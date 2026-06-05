"""
Admin commands and callbacks handlers.
"""

from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION

import database.db as db_module
from database import users as users_db
from database import subscriptions as subs_db
from database import courses as courses_db
from config import ADMIN_ID

router = Router()


def admin_only(func):
    """Decorator to restrict handlers to ADMIN_ID."""
    async def wrapper(event, *args, **kwargs):
        user_id = event.from_user.id if (event and event.from_user) else None
        if user_id != ADMIN_ID:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Unauthorized. This command is for admins only.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⛔ Unauthorized. This command is for admins only.")
            return
        return await func(event, *args, **kwargs)
    return wrapper


# ── /admin entry ────────────────────────────────────────────────────────────
@router.message(Command("admin"))
@admin_only
async def cmd_admin(message: Message):
    # Fetch stats
    total_users = await db_module.db.users.count_documents({})
    expiring_today = await subs_db.count_expiring_today()
    
    # Active subscriptions by course
    courses = await courses_db.get_all_courses(active_only=True)
    lines = []
    for c in courses:
        count = await subs_db.count_active_subscriptions_by_course(str(c["_id"]))
        lines.append(f"• <b>{c['name']}</b>: {count} active")
        
    active_subs_by_course_text = "\n".join(lines) if lines else "• No active courses."
    
    from keyboards.admin_kb import admin_entry_kb
    await message.answer(
        f"🛠 <b>Admin Dashboard</b>\n\n"
        f"👥 Total Registered Users: {total_users}\n"
        f"⏳ Subscriptions Expiring Today: {expiring_today}\n\n"
        f"📚 <b>Active Subscriptions:</b>\n{active_subs_by_course_text}",
        reply_markup=admin_entry_kb()
    )


# ── Admin Panel Main Menu ───────────────────────────────────────────────────
@router.callback_query(F.data == "admin_panel")
@admin_only
async def cb_admin_panel(callback: CallbackQuery):
    from keyboards.admin_kb import admin_panel_kb
    await callback.message.edit_text(
        "🛠 <b>Admin Control Panel</b>\n\n"
        "Choose a management category below:",
        reply_markup=admin_panel_kb()
    )
    await callback.answer()


# ── Users submenu ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_users")
@admin_only
async def cb_users_menu(callback: CallbackQuery):
    from keyboards.admin_kb import users_menu_kb
    await callback.message.edit_text(
        "👥 <b>User Management</b>\n\n"
        "Select users status list to browse:",
        reply_markup=users_menu_kb()
    )
    await callback.answer()


# ── Active Users List ───────────────────────────────────────────────────────
async def show_active_users(callback: CallbackQuery, page: int):
    active_ids = await subs_db.get_all_active_user_ids()
    limit = 5
    total_users = len(active_ids)
    if total_users == 0:
        from keyboards.admin_kb import pagination_kb
        await callback.message.edit_text(
            "🟢 <b>Active Users</b>\n\n"
            "No active users found.",
            reply_markup=pagination_kb(1, 1, "admin_active_users", "admin_users")
        )
        return
        
    total_pages = max((total_users + limit - 1) // limit, 1)
    if page > total_pages:
        page = total_pages
    if page < 1:
        page = 1
        
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_user_ids = active_ids[start_idx:end_idx]
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from keyboards.admin_kb import pagination_kb
    
    builder = InlineKeyboardBuilder()
    for uid in page_user_ids:
        user = await users_db.get_user(uid)
        if user:
            username_str = f" (@{user['username']})" if user.get("username") else ""
            builder.button(
                text=f"{user['name']}{username_str}",
                callback_data=f"profile_{uid}"
            )
            
    builder.adjust(1)
    
    pag_kb = pagination_kb(page, total_pages, "admin_active_users", "admin_users")
    builder.attach(InlineKeyboardBuilder.from_markup(pag_kb))
    
    await callback.message.edit_text(
        "🟢 <b>Active Users</b>\n\n"
        "Select a user to view profile or manage access:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin_active_users")
@admin_only
async def cb_active_users(callback: CallbackQuery):
    await show_active_users(callback, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_active_users_page_"))
@admin_only
async def cb_active_users_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_active_users(callback, page)
    await callback.answer()


# ── Expired Users List ──────────────────────────────────────────────────────
async def show_expired_users(callback: CallbackQuery, page: int):
    limit = 5
    pipeline = [
        {"$match": {"status": {"$in": ["expired", "kicked"]}}},
        {"$group": {"_id": "$user_id"}}
    ]
    cursor = db_module.db.subscriptions.aggregate(pipeline)
    expired_uids = [doc["_id"] for doc in await cursor.to_list(None)]
    
    total_users = len(expired_uids)
    if total_users == 0:
        from keyboards.admin_kb import pagination_kb
        await callback.message.edit_text(
            "❌ <b>Expired / Kicked Users</b>\n\n"
            "No expired or kicked users found.",
            reply_markup=pagination_kb(1, 1, "admin_expired_users", "admin_users")
        )
        return
        
    total_pages = max((total_users + limit - 1) // limit, 1)
    if page > total_pages:
        page = total_pages
    if page < 1:
        page = 1
        
    page_uids = expired_uids[(page - 1) * limit : page * limit]
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from keyboards.admin_kb import pagination_kb
    
    builder = InlineKeyboardBuilder()
    for uid in page_uids:
        user = await users_db.get_user(uid)
        if user:
            username_str = f" (@{user['username']})" if user.get("username") else ""
            builder.button(
                text=f"{user['name']}{username_str}",
                callback_data=f"profile_{uid}"
            )
            
    builder.adjust(1)
    
    pag_kb = pagination_kb(page, total_pages, "admin_expired_users", "admin_users")
    builder.attach(InlineKeyboardBuilder.from_markup(pag_kb))
    
    await callback.message.edit_text(
        "❌ <b>Expired / Kicked Users</b>\n\n"
        "Select a user to view profile or manage access:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin_expired_users")
@admin_only
async def cb_expired_users(callback: CallbackQuery):
    await show_expired_users(callback, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_expired_users_page_"))
@admin_only
async def cb_expired_users_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_expired_users(callback, page)
    await callback.answer()


# ── Banned Users List ───────────────────────────────────────────────────────
async def show_banned_users(callback: CallbackQuery, page: int):
    banned_users = await users_db.get_banned_users()
    limit = 5
    total_users = len(banned_users)
    if total_users == 0:
        from keyboards.admin_kb import pagination_kb
        await callback.message.edit_text(
            "🚫 <b>Banned Users</b>\n\n"
            "No banned users found.",
            reply_markup=pagination_kb(1, 1, "admin_banned_users", "admin_users")
        )
        return
        
    total_pages = max((total_users + limit - 1) // limit, 1)
    if page > total_pages:
        page = total_pages
    if page < 1:
        page = 1
        
    page_users = banned_users[(page - 1) * limit : page * limit]
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from keyboards.admin_kb import pagination_kb
    
    builder = InlineKeyboardBuilder()
    for user in page_users:
        uid = user["_id"]
        username_str = f" (@{user['username']})" if user.get("username") else ""
        builder.button(
            text=f"{user['name']}{username_str}",
            callback_data=f"profile_{uid}"
        )
            
    builder.adjust(1)
    
    pag_kb = pagination_kb(page, total_pages, "admin_banned_users", "admin_users")
    builder.attach(InlineKeyboardBuilder.from_markup(pag_kb))
    
    await callback.message.edit_text(
        "🚫 <b>Banned Users</b>\n\n"
        "Select a user to view profile or manage access:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin_banned_users")
@admin_only
async def cb_banned_users(callback: CallbackQuery):
    await show_banned_users(callback, 1)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_banned_users_page_"))
@admin_only
async def cb_banned_users_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])
    await show_banned_users(callback, page)
    await callback.answer()


# ── Profile & History View ──────────────────────────────────────────────────
@router.callback_query(F.data.startswith("profile_"))
@admin_only
async def cb_profile(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    user = await users_db.get_user(user_id)
    if not user:
        await callback.answer("User not found!", show_alert=True)
        return
        
    stats = await users_db.get_user_stats(user_id)
    active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
    
    # Build active courses summary
    active_lines = []
    for sub in active_subs:
        course = await courses_db.get_course(str(sub["course_id"]))
        if course:
            days_left = (sub["expires_at"] - datetime.now(timezone.utc)).days
            active_lines.append(f"• <b>{course['name']}</b> ({max(days_left, 0)} days left)")
            
    active_subs_text = "\n".join(active_lines) if active_lines else "• None"
    
    registered_str = user["registered_at"].strftime("%b %d, %Y")
    status_str = "🚫 BANNED" if user.get("is_banned") else "🟢 Normal"
    
    from keyboards.admin_kb import profile_kb
    
    await callback.message.edit_text(
        f"👤 <b>User Profile: {user['name']}</b>\n\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"🔗 Username: {user['username'] or 'None'}\n"
        f"📅 Registered: {registered_str}\n"
        f"🚫 Status: {status_str}\n\n"
        f"📊 <b>Subscription Stats:</b>\n"
        f"• Total Subscriptions: {stats['total_subs']}\n"
        f"• Total Paid: ₹{stats['total_paid']}\n\n"
        f"📚 <b>Active Subscriptions:</b>\n{active_subs_text}",
        reply_markup=profile_kb(user_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("history_"))
@admin_only
async def cb_history(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    user = await users_db.get_user(user_id)
    if not user:
        await callback.answer("User not found!", show_alert=True)
        return
        
    history = await subs_db.get_subscription_history(user_id)
    
    lines = []
    for sub in history:
        course = await courses_db.get_course(str(sub["course_id"]))
        course_name = course["name"] if course else "Unknown Course"
        joined_str = sub["joined_at"].strftime("%b %d, %Y") if sub.get("joined_at") else "Pending"
        expires_str = sub["expires_at"].strftime("%b %d, %Y") if sub.get("expires_at") else "Pending"
        
        status_emoji = {
            "pending_join": "⏳",
            "active": "🟢",
            "expired": "❌",
            "kicked": "🚫",
            "extended": "🔵"
        }.get(sub["status"], "❓")
        
        lines.append(
            f"{status_emoji} <b>{course_name}</b>\n"
            f"  Status: {sub['status'].upper()}\n"
            f"  Price: ₹{sub['amount_paid']}\n"
            f"  Joined: {joined_str}\n"
            f"  Expires: {expires_str}\n"
        )
        
    history_text = "\n".join(lines) if lines else "No subscription history."
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data=f"profile_{user_id}")]
    ])
    
    await callback.message.edit_text(
        f"📋 <b>Subscription History: {user['name']}</b>\n\n"
        f"{history_text}",
        reply_markup=back_kb
    )
    await callback.answer()


# ── Give access ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("give_"))
@admin_only
async def cb_give_select_course(callback: CallbackQuery):
    # Format: give_{user_id} or give_{user_id}:{course_id}
    data_parts = callback.data.split("_")[1].split(":")
    user_id = int(data_parts[0])
    
    if len(data_parts) == 1:
        # Step 1: List active courses
        user = await users_db.get_user(user_id)
        if not user:
            await callback.answer("User not found!", show_alert=True)
            return
            
        courses = await courses_db.get_all_courses(active_only=True)
        if not courses:
            await callback.answer("No active courses found.", show_alert=True)
            return
            
        from keyboards.admin_kb import course_select_kb
        await callback.message.edit_text(
            f"🎓 <b>Give Access — Select Course</b>\n\n"
            f"Select a course to grant access to <b>{user['name']}</b>:",
            reply_markup=course_select_kb(courses, user_id)
        )
        await callback.answer()
    else:
        # Step 2: Course selected, show confirmation screen
        course_id = data_parts[1]
        user = await users_db.get_user(user_id)
        course = await courses_db.get_course(course_id)
        if not user or not course:
            await callback.answer("User or Course not found!", show_alert=True)
            return
            
        # Check if already has active subscription for this course
        existing_active = await subs_db.get_active_subscription(user_id, course_id)
        warning_text = ""
        if existing_active:
            warning_text = "⚠️ <b>Warning:</b> This user already has an active subscription for this course!\n\n"
            
        is_renewal = await subs_db.check_is_renewal(user_id, course_id)
        type_str = "Renewal" if is_renewal else "New Subscription"
        
        projected_expiry = (datetime.now(timezone.utc) + timedelta(days=course.get("duration_days", 30))).strftime("%b %d, %Y")
        
        from keyboards.admin_kb import confirm_give_kb
        await callback.message.edit_text(
            f"🎓 <b>Confirm Grant Access</b>\n\n"
            f"{warning_text}"
            f"👤 <b>User:</b> {user['name']} (@{user['username'] or 'None'})\n"
            f"📚 <b>Course:</b> {course['name']}\n"
            f"💰 <b>Price:</b> ₹{course['price']}\n"
            f"⏱ <b>Duration:</b> {course.get('duration_days', 30)} days\n"
            f"📅 <b>Projected Expiry:</b> {projected_expiry} (if joined today)\n"
            f"🔄 <b>Type:</b> {type_str}\n\n"
            f"Are you sure you want to generate an invite link and grant access to this course?",
            reply_markup=confirm_give_kb(user_id, course_id)
        )
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_give_"))
@admin_only
async def cb_confirm_give(callback: CallbackQuery):
    # Format: confirm_give_{user_id}:{course_id}
    data_parts = callback.data.replace("confirm_give_", "").split(":")
    user_id = int(data_parts[0])
    course_id = data_parts[1]
    
    user = await users_db.get_user(user_id)
    course = await courses_db.get_course(course_id)
    if not user or not course:
        await callback.answer("User or Course not found!", show_alert=True)
        return
        
    settings = await db_module.get_settings()
    expiry_hours = settings.get("invite_link_expiry_hours", 2)
    
    # Generate invite link
    from utils.invite import create_one_time_link
    try:
        invite_link = await create_one_time_link(
            bot=callback.bot,
            channel_id=course["channel_id"],
            expiry_hours=expiry_hours
        )
    except Exception as e:
        await callback.answer(f"Failed to create invite link: {str(e)}", show_alert=True)
        return
        
    # Check is_renewal
    is_renewal = await subs_db.check_is_renewal(user_id, course_id)
    
    # Create subscription in pending_join status
    sub_id = await subs_db.create_subscription(
        user_id=user_id,
        course_id=course_id,
        invite_link=invite_link,
        amount_paid=course["price"],
        is_renewal=is_renewal
    )
    
    # Send link to user
    user_notified = False
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=f"🎓 <b>Access Granted!</b>\n\n"
                 f"You have been granted access to the course: <b>{course['name']}</b>.\n"
                 f"Please use the link below to join the channel. Note that this link is valid for **one use only** and will expire in {expiry_hours} hours:\n\n"
                 f"🔗 {invite_link}"
        )
        user_notified = True
    except Exception:
        pass
        
    from keyboards.admin_kb import profile_kb
    status_text = "and the user has been notified via DM" if user_notified else "⚠️ but the user could NOT be notified via DM (bot blocked?)"
    await callback.message.edit_text(
        f"✅ <b>Access Granted Successfully!</b>\n\n"
        f"👤 <b>User:</b> {user['name']}\n"
        f"📚 <b>Course:</b> {course['name']}\n"
        f"🔗 <b>Invite Link:</b> {invite_link}\n\n"
        f"The invite link was generated successfully {status_text}.",
        reply_markup=profile_kb(user_id)
    )
    await callback.answer()


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_user_join(event: ChatMemberUpdated):
    user_id = event.new_chat_member.user.id
    channel_id = event.chat.id
    
    sub = await subs_db.get_pending_subscription(user_id, channel_id)
    if not sub:
        return
        
    course = await courses_db.get_course(str(sub["course_id"]))
    if not course:
        return
        
    duration = course.get("duration_days", 30)
    await subs_db.activate_subscription(str(sub["_id"]), duration)
    
    user = await users_db.get_user(user_id)
    user_name = user["name"] if user else event.new_chat_member.user.full_name
    username = user["username"] if user else event.new_chat_member.user.username
    
    expires_at = (datetime.now(timezone.utc) + timedelta(days=duration)).strftime("%b %d, %Y")
    
    # Notify user
    try:
        await event.bot.send_message(
            chat_id=user_id,
            text=f"🎉 <b>Welcome to {course['name']}!</b>\n\n"
                 f"Your subscription is now active until <b>{expires_at}</b>."
        )
    except Exception:
        pass
        
    # Notify admin
    settings = await db_module.get_settings()
    admin_id = settings.get("admin_id", ADMIN_ID)
    try:
        await event.bot.send_message(
            chat_id=admin_id,
            text=f"🔔 <b>User Joined Channel</b>\n\n"
                 f"👤 <b>User:</b> {user_name} (@{username or 'None'})\n"
                 f"📚 <b>Course:</b> {course['name']}\n"
                 f"📅 <b>Expiry:</b> {expires_at}"
        )
    except Exception:
        pass


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_user_leave(event: ChatMemberUpdated):
    user_id = event.new_chat_member.user.id
    channel_id = event.chat.id
    
    sub = await subs_db.get_active_subscription_by_channel(user_id, channel_id)
    if not sub:
        return
        
    await subs_db.record_manual_leave(str(sub["_id"]))


