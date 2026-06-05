"""
User commands and callbacks handlers.
"""

from datetime import datetime, timezone
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from config import ADMIN_ID
from database import users as users_db, subscriptions as subs_db, courses as courses_db
from keyboards.user_kb import register_kb, home_kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # Banned check
    if await users_db.is_banned(user_id):
        await message.answer(
            "🚫 <b>Access Restricted</b>\n\n"
            "You are not allowed to use this bot.\n"
            "Contact admin if you believe this is a mistake."
        )
        return

    user = await users_db.get_user(user_id)

    if not user:
        # New user
        await message.answer(
            "👋 <b>Welcome!</b>\n\n"
            "Register below to get started.",
            reply_markup=register_kb()
        )
        return

    # Returning user
    active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
    history = await subs_db.get_subscription_history(user_id)
    has_history = len(history) > 0

    if not active_subs:
        await message.answer(
            f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
            "📚 No active courses.\n\n"
            "Contact admin to get course access.",
            reply_markup=home_kb(has_history=has_history)
        )
        return

    # Build course summary — requires course name lookup
    lines = []
    for sub in active_subs:
        course = await courses_db.get_course(str(sub["course_id"]))
        if course:
            days_left = (sub["expires_at"] - datetime.now(timezone.utc)).days
            lines.append(f"• <b>{course['name']}</b> — {max(0, days_left)} days left")

    course_text = "\n".join(lines)
    await message.answer(
        f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
        f"📚 <b>Active Courses:</b>\n{course_text}\n\n"
        f"📋 Total Subscriptions: {len(active_subs)}",
        reply_markup=home_kb(has_history=has_history)
    )

@router.callback_query(F.data == "user_register")
async def cb_register(callback: CallbackQuery):
    user = callback.from_user
    user_id = user.id

    if await users_db.get_user(user_id):
        await callback.answer("Already registered!", show_alert=False)
        return

    # Get profile photo
    photo_file_id = None
    try:
        photos = await callback.bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][0].file_id
    except Exception as e:
        logging.warning(f"Could not retrieve profile photo for user {user_id}: {e}")

    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else None

    await users_db.create_user(user_id, name, username, photo_file_id)

    await callback.message.edit_text(
        f"✅ <b>Registration Complete!</b>\n\n"
        f"👤 {name}\n"
        f"🆔 {user_id}\n\n"
        f"Admin will contact you once your course access is approved."
    )

    # Notify admin
    try:
        await callback.bot.send_message(
            ADMIN_ID,
            f"🔔 <b>New Registration</b>\n\n"
            f"👤 {name}\n"
            f"🔗 {username or 'No username'}\n"
            f"🆔 {user_id}"
        )
    except Exception as e:
        logging.error(f"Failed to notify admin {ADMIN_ID} of new registration: {e}")

    await callback.answer()
