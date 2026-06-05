"""
User commands and callbacks handlers.
"""

from datetime import datetime, timezone
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from database import users as users_db, subscriptions as subs_db, courses as courses_db
from keyboards.user_kb import register_kb, home_kb, status_back_kb, available_courses_kb, course_subscribe_kb

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
            "👋 <b>Welcome to Subscription Control Bot!</b>\n\n"
            "Access exclusive course content through this bot. "
            "Register below to get started.\n\n"
            "━━━━━━━━━━━━━━━━━━━━",
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


@router.callback_query(F.data == "user_status")
async def cb_user_status(callback: CallbackQuery):
    user_id = callback.from_user.id
    active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
    history = await subs_db.get_subscription_history(user_id)
    
    if not active_subs:
        await callback.answer("No active subscriptions found.", show_alert=True)
        return
        
    lines = ["📊 <b>My Subscriptions</b>\n"]
    for sub in active_subs:
        course = await courses_db.get_course(str(sub["course_id"]))
        if course:
            joined_str = sub["joined_at"].strftime("%b %d, %Y") if sub.get("joined_at") else "N/A"
            expires_str = sub["expires_at"].strftime("%b %d, %Y") if sub.get("expires_at") else "N/A"
            days_left = 0
            if sub.get("expires_at"):
                days_left = max(0, (sub["expires_at"] - datetime.now(timezone.utc)).days)
            lines.append(
                f"📚 <b>{course['name']}</b>\n"
                f"   Status: 🟢 Active\n"
                f"   Joined: {joined_str}\n"
                f"   Expires: {expires_str}\n"
                f"   ⏳ {days_left} days remaining\n"
                f"   💰 ₹{sub.get('amount_paid', 0)}\n"
            )
            
    total_paid = sum(sub.get("amount_paid", 0) for sub in history)
    lines.append("──────────────────")
    lines.append(f"💰 <b>Total Paid:</b> ₹{total_paid:,}")
    
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=status_back_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "user_refresh")
async def cb_user_refresh(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await users_db.get_user(user_id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return
        
    active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
    history = await subs_db.get_subscription_history(user_id)
    has_history = len(history) > 0
    
    if not active_subs:
        text = (
            f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
            "📚 No active courses.\n\n"
            "Contact admin to get course access."
        )
    else:
        lines = []
        for sub in active_subs:
            course = await courses_db.get_course(str(sub["course_id"]))
            if course:
                days_left = max(0, (sub["expires_at"] - datetime.now(timezone.utc)).days) if sub.get("expires_at") else 0
                lines.append(f"• <b>{course['name']}</b> — {days_left} days left")
        course_text = "\n".join(lines)
        text = (
            f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
            f"📚 <b>Active Courses:</b>\n{course_text}\n\n"
            f"📋 Total Subscriptions: {len(active_subs)}"
        )
        
    try:
        await callback.message.edit_text(text, reply_markup=home_kb(has_history=has_history))
        await callback.answer("Refreshed!")
    except Exception:
        await callback.answer("Already up-to-date.")


@router.callback_query(F.data == "user_history")
async def cb_user_history(callback: CallbackQuery):
    user_id = callback.from_user.id
    history = await subs_db.get_subscription_history(user_id)
    
    if not history:
        await callback.answer("No subscription history found.", show_alert=True)
        return
        
    lines = ["📋 <b>My History</b>\n"]
    for idx, sub in enumerate(history, 1):
        course = await courses_db.get_course(str(sub["course_id"]))
        if course:
            course_name = course["name"]
            amount = sub.get("amount_paid", 0)
            status = sub.get("status", "unknown").capitalize()
            
            # Formatting status emoji
            status_emoji = "⏳"
            if sub.get("status") == "active":
                status_emoji = "🟢"
            elif sub.get("status") == "expired":
                status_emoji = "❌"
            elif sub.get("status") == "kicked":
                status_emoji = "🚫"
            elif sub.get("status") == "pending_join":
                status_emoji = "⏳"
                
            date_range = "N/A"
            if sub.get("joined_at") and sub.get("expires_at"):
                start_str = sub["joined_at"].strftime("%b %d")
                end_str = sub["expires_at"].strftime("%b %d, %Y")
                date_range = f"{start_str} – {end_str}"
            elif sub.get("created_at"):
                date_range = sub["created_at"].strftime("%b %d, %Y")
                
            renewal_tag = " · 🔄 Renewal" if sub.get("is_renewal") else ""
            
            lines.append(
                f"{idx}. <b>{course_name}</b>\n"
                f"   {date_range}\n"
                f"   💰 ₹{amount} · {status_emoji} {status}{renewal_tag}\n"
            )
            
    total_paid = sum(sub.get("amount_paid", 0) for sub in history)
    lines.append("──────────────────")
    lines.append(f"💰 <b>Total Paid:</b> ₹{total_paid:,}")
    
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=status_back_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "user_home")
async def cb_user_home(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await users_db.get_user(user_id)
    if not user:
        await callback.answer("User not found.", show_alert=True)
        return
        
    active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
    history = await subs_db.get_subscription_history(user_id)
    has_history = len(history) > 0
    
    if not active_subs:
        text = (
            f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
            "📚 No active courses.\n\n"
            "Contact admin to get course access."
        )
    else:
        lines = []
        for sub in active_subs:
            course = await courses_db.get_course(str(sub["course_id"]))
            if course:
                days_left = max(0, (sub["expires_at"] - datetime.now(timezone.utc)).days) if sub.get("expires_at") else 0
                lines.append(f"• <b>{course['name']}</b> — {days_left} days left")
        course_text = "\n".join(lines)
        text = (
            f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
            f"📚 <b>Active Courses:</b>\n{course_text}\n\n"
            f"📋 Total Subscriptions: {len(active_subs)}"
        )
        
    try:
        await callback.message.edit_text(text, reply_markup=home_kb(has_history=has_history))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=home_kb(has_history=has_history))
    await callback.answer()


@router.callback_query(F.data == "user_available_courses")
async def cb_user_available_courses(callback: CallbackQuery):
    courses = await courses_db.get_all_courses(active_only=True)
    if not courses:
        text = "🛍 <b>Available Courses</b>\n\nNo courses are currently available. Please check back later!"
        try:
            await callback.message.edit_text(text, reply_markup=status_back_kb())
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=status_back_kb())
        await callback.answer()
        return

    text = (
        "🛍 <b>Available Courses</b>\n\n"
        "Select a course below to view its price, duration, and subscribe:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=available_courses_kb(courses))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=available_courses_kb(courses))
    await callback.answer()


@router.callback_query(F.data.startswith("user_course_"))
async def cb_user_view_course(callback: CallbackQuery):
    course_id = callback.data.split("_")[-1]
    course = await courses_db.get_course(course_id)
    if not course:
        await callback.answer("Course not found.", show_alert=True)
        return

    try:
        admin_chat = await callback.bot.get_chat(ADMIN_ID)
        admin_username = admin_chat.username
        if admin_username:
            admin_url = f"https://t.me/{admin_username}"
        else:
            admin_url = f"tg://user?id={ADMIN_ID}"
    except Exception as e:
        logging.warning(f"Could not fetch admin username: {e}")
        admin_url = f"tg://user?id={ADMIN_ID}"

    text = (
        f"📚 <b>Course Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Name:</b> {course['name']}\n"
        f"<b>Price:</b> ₹{course['price']}\n"
        f"<b>Duration:</b> {course.get('duration_days', 30)} days\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"To subscribe to this course, please contact the admin by clicking the button below:"
    )
    
    kb = course_subscribe_kb(admin_url)
    photo_id = course.get("photo_file_id")
    if photo_id:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(
            photo=photo_id,
            caption=text,
            reply_markup=kb
        )
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "cancel")
async def cmd_cancel(message: Message, state: FSMContext):
    """Global handler to cancel any active FSM state."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ No active state or operation to cancel.")
        return
    await state.clear()
    await message.answer("❌ Current operation cancelled. FSM state cleared.", reply_markup=None)

