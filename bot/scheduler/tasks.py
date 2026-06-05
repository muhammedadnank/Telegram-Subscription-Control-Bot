"""
Scheduler jobs for reminders and kicks.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from database.db import get_settings
from database import subscriptions as subs_db
from database import courses as courses_db
from database import users as users_db
from utils.logger import log_to_channel
from config import ADMIN_ID

scheduler = AsyncIOScheduler()


async def check_reminders(bot: Bot):
    """
    Checks active subscriptions that are expiring in warning_hours and notifies users and admin.
    """
    settings = await get_settings()
    warning_hours = settings.get("warning_hours", [48, 12])

    for hours in warning_hours:
        subs = await subs_db.get_expiring_soon(hours)
        for sub in subs:
            course = await courses_db.get_course(str(sub["course_id"]))
            if not course:
                continue

            expires_str = sub["expires_at"].strftime("%b %d, %Y")

            # Notify user
            try:
                if hours >= 24:
                    days = hours // 24
                    user_msg = (
                        f"⚠️ <b>Subscription Expiring Soon</b>\n\n"
                        f"📚 <b>{course['name']}</b> expires in {days} days.\n"
                        f"📅 Expiry: {expires_str}\n\n"
                        f"Contact admin to renew."
                    )
                else:
                    user_msg = (
                        f"🚨 <b>Final Warning!</b>\n\n"
                        f"📚 <b>{course['name']}</b> expires in {hours} hours.\n"
                        f"📅 Expiry: {expires_str}\n\n"
                        f"Contact admin immediately to renew."
                    )
                await bot.send_message(sub["user_id"], user_msg)
            except Exception as e:
                logging.warning(f"Reminder to user {sub['user_id']} failed: {e}")

            # Notify admin
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🔔 <b>Expiry Reminder Sent</b>\n\n"
                    f"👤 User ID: {sub['user_id']}\n"
                    f"📚 {course['name']}\n"
                    f"⏳ Expires in {hours}h\n"
                    f"📅 {expires_str}"
                )
            except Exception as e:
                logging.warning(f"Admin reminder notify failed: {e}")

            # Notify log channel
            user = await users_db.get_user(sub["user_id"])
            user_name = user["name"] if user else f"User {sub['user_id']}"
            username = user["username"] if user else None
            await log_to_channel(
                bot,
                f"🔔 <b>Expiry Warning Sent</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>User:</b> {user_name}" + (f" ({username})" if username else "") + f"\n"
                f"🆔 <b>Telegram ID:</b> <code>{sub['user_id']}</code>\n"
                f"📚 <b>Course:</b> {course['name']}\n"
                f"⏳ <b>Time Remaining:</b> {hours} Hours\n"
                f"📅 <b>Expiry Date:</b> {expires_str}"
            )

            await subs_db.mark_reminder_sent(str(sub["_id"]), hours)


async def check_expiry_kicks(bot: Bot):
    """
    Checks active subscriptions that have passed expires_at. Kicks them from Telegram and revokes their invite link.
    """
    subs = await subs_db.get_due_for_kick()
    for sub in subs:
        course = await courses_db.get_course(str(sub["course_id"]))
        if not course:
            continue

        # Kick user from channel
        try:
            await bot.ban_chat_member(course["channel_id"], sub["user_id"])
            await bot.unban_chat_member(course["channel_id"], sub["user_id"])
        except Exception as e:
            logging.info(f"Kick skipped for {sub['user_id']} (already left?): {e}")

        # Revoke invite link
        try:
            await bot.revoke_chat_invite_link(
                course["channel_id"],
                sub["invite_link"]
            )
        except Exception as e:
            logging.info(f"Link revoke skipped for sub {sub['_id']}: {e}")

        # Update DB
        await subs_db.expire_subscription(str(sub["_id"]))

        # Notify user
        try:
            await bot.send_message(
                sub["user_id"],
                f"❌ <b>Subscription Expired</b>\n\n"
                f"📚 <b>{course['name']}</b> access has ended.\n\n"
                f"Contact admin to renew and regain access."
            )
        except Exception as e:
            logging.warning(f"Expiry notify to user {sub['user_id']} failed: {e}")

        # Notify admin
        try:
            await bot.send_message(
                ADMIN_ID,
                f"📋 <b>Subscription Expired</b>\n\n"
                f"👤 User ID: {sub['user_id']}\n"
                f"📚 {course['name']}\n"
                f"📅 Expired: {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
            )
        except Exception as e:
            logging.warning(f"Admin expiry notify failed: {e}")

        # Notify log channel
        user = await users_db.get_user(sub["user_id"])
        user_name = user["name"] if user else f"User {sub['user_id']}"
        username = user["username"] if user else None
        await log_to_channel(
            bot,
            f"🔴 <b>Subscription Expired (Kicked)</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {user_name}" + (f" ({username})" if username else "") + f"\n"
            f"🆔 <b>Telegram ID:</b> <code>{sub['user_id']}</code>\n"
            f"📚 <b>Course:</b> {course['name']}\n"
            f"🚫 <b>Action:</b> Removed from channel (expired)"
        )


async def cleanup_pending_joins(bot: Bot):
    """
    Checks for pending_join subscriptions that have exceeded the invite link expiry window and expires them.
    """
    settings = await get_settings()
    expiry_hours = settings.get("invite_link_expiry_hours", 2)
    threshold = datetime.now(timezone.utc) - timedelta(hours=expiry_hours + 1)

    stale = await subs_db.get_stale_pending_joins(threshold)
    for sub in stale:
        await subs_db.expire_subscription(
            str(sub["_id"]),
            reason="invite_link_expired_unused"
        )
        logging.info(f"Cleaned up stale pending_join: sub {sub['_id']}")


def setup_scheduler(bot: Bot):
    """
    Initializes and starts the background tasks.
    """
    scheduler.add_job(
        check_reminders, "interval",
        hours=1,
        args=[bot],
        id="check_reminders",
        replace_existing=True
    )
    scheduler.add_job(
        check_expiry_kicks, "interval",
        minutes=15,
        args=[bot],
        id="check_expiry_kicks",
        replace_existing=True
    )
    scheduler.add_job(
        cleanup_pending_joins, "interval",
        hours=1,
        args=[bot],
        id="cleanup_pending_joins",
        replace_existing=True
    )
    scheduler.start()
    logging.info("Scheduler started with 3 jobs")
