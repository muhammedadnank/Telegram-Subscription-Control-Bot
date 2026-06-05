"""
Admin commands and callbacks handlers.
"""

from datetime import datetime, timezone, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ChatMemberUpdated
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION

from aiogram.fsm.context import FSMContext
from states.fsm import AddCourseState, EditCourseState, BroadcastState, SearchState, SettingsState

import database.db as db_module
from database import users as users_db
from database import subscriptions as subs_db
from database import courses as courses_db
from utils.logger import log_to_channel
from config import ADMIN_ID

router = Router()


def admin_only(func):
    """Decorator to restrict handlers to ADMIN_ID."""
    import inspect
    import functools

    sig = inspect.signature(func)
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

    @functools.wraps(func)
    async def wrapper(event, *args, **kwargs):
        user_id = event.from_user.id if (event and event.from_user) else None
        if user_id != ADMIN_ID:
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Unauthorized. This command is for admins only.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⛔ Unauthorized. This command is for admins only.")
            return
        
        if has_var_keyword:
            return await func(event, *args, **kwargs)
        
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
        return await func(event, *args, **filtered_kwargs)
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
async def cb_admin_panel(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
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
        reply_markup=profile_kb(user_id, is_banned=user.get("is_banned", False))
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

    # Notify log channel
    await log_to_channel(
        event.bot,
        f"✅ <b>Subscription Activated</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>User:</b> {user_name} (@{username or 'None'})\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"📚 <b>Course:</b> {course['name']}\n"
        f"💰 <b>Amount Paid:</b> ₹{sub.get('amount_paid', course['price'])}\n"
        f"⏳ <b>Duration:</b> {duration} days\n"
        f"📅 <b>Expires At:</b> {expires_at}\n"
        f"🔄 <b>Type:</b> New Subscription"
    )


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_user_leave(event: ChatMemberUpdated):
    user_id = event.new_chat_member.user.id
    channel_id = event.chat.id
    
    sub = await subs_db.get_active_subscription_by_channel(user_id, channel_id)
    if not sub:
        return
        
    await subs_db.record_manual_leave(str(sub["_id"]))

    user = await users_db.get_user(user_id)
    user_name = user["name"] if user else event.new_chat_member.user.full_name
    username = user["username"] if user else event.new_chat_member.user.username
    course = await courses_db.get_course(str(sub["course_id"]))
    course_name = course["name"] if course else "Unknown Course"

    await log_to_channel(
        event.bot,
        f"🔴 <b>User Left Channel</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>User:</b> {user_name} (@{username or 'None'})\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"📚 <b>Course:</b> {course_name}\n"
        f"🚫 <b>Action:</b> Manually left chat/channel"
    )


# ── Course Management ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_courses")
@admin_only
async def cb_courses_menu(callback: CallbackQuery):
    courses = await courses_db.get_all_courses()
    from keyboards.admin_kb import courses_menu_kb
    text = "📋 <b>Course Management</b>\n\nManage courses, pricing, and statuses:"
    try:
        await callback.message.edit_text(text, reply_markup=courses_menu_kb(courses))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=courses_menu_kb(courses))
    await callback.answer()


@router.callback_query(F.data == "admin_add_course")
@admin_only
async def cb_add_course_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCourseState.waiting_name)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_courses")]
    ])
    try:
        await callback.message.edit_text(
            "➕ <b>Add Course</b>\n\nPlease enter the name of the new course:",
            reply_markup=cancel_kb
        )
    except Exception:
        await callback.message.answer(
            "➕ <b>Add Course</b>\n\nPlease enter the name of the new course:",
            reply_markup=cancel_kb
        )
    await callback.answer()


@router.message(AddCourseState.waiting_name)
@admin_only
async def add_course_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.reply("❌ Name cannot be empty. Please enter a valid course name:")
        return
        
    await state.update_data(name=name)
    await state.set_state(AddCourseState.waiting_photo)
    
    from keyboards.admin_kb import skip_kb
    await message.reply(
        "📸 <b>Course Photo (Optional)</b>\n\nPlease upload a photo for this course, or click Skip:",
        reply_markup=skip_kb("add_course_photo_skip")
    )


@router.message(AddCourseState.waiting_photo, F.photo)
@admin_only
async def add_course_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_id)
    await state.set_state(AddCourseState.waiting_channel_id)
    await message.reply(
        "🆔 <b>Channel ID</b>\n\nPlease send the Telegram Channel ID (e.g., <code>-1001234567890</code>).\n\n"
        "⚠️ <i>Make sure the bot has been added as an Administrator to that channel.</i>"
    )


@router.callback_query(F.data == "add_course_photo_skip", AddCourseState.waiting_photo)
@admin_only
async def add_course_photo_skip(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photo_file_id=None)
    await state.set_state(AddCourseState.waiting_channel_id)
    try:
        await callback.message.edit_text(
            "🆔 <b>Channel ID</b>\n\nPlease send the Telegram Channel ID (e.g., <code>-1001234567890</code>).\n\n"
            "⚠️ <i>Make sure the bot has been added as an Administrator to that channel.</i>"
        )
    except Exception:
        await callback.message.answer(
            "🆔 <b>Channel ID</b>\n\nPlease send the Telegram Channel ID (e.g., <code>-1001234567890</code>).\n\n"
            "⚠️ <i>Make sure the bot has been added as an Administrator to that channel.</i>"
        )
    await callback.answer()


@router.message(AddCourseState.waiting_channel_id)
@admin_only
async def add_course_channel(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        channel_id = int(text)
    except ValueError:
        await message.reply("❌ Invalid Channel ID format. Please send a numeric ID (e.g. <code>-1001234567890</code>):")
        return
        
    # Verify bot access to the channel
    try:
        chat = await message.bot.get_chat(channel_id)
        if chat.type not in ["channel", "supergroup", "group"]:
            await message.reply(f"❌ The provided ID corresponds to a {chat.type}, not a channel/group. Please enter a channel ID:")
            return
        channel_title = chat.title
    except Exception as e:
        # For testing purposes or manual input, if we are in a testing context, the bot get_chat might be mocked or fail
        # But we still want to be helpful.
        await message.reply(
            f"❌ <b>Bot cannot access this channel.</b>\n\n"
            f"Error: <code>{str(e)}</code>\n\n"
            f"Please check if the bot is added as an Administrator to the channel and try again:"
        )
        return
        
    await state.update_data(channel_id=channel_id, channel_title=channel_title)
    await state.set_state(AddCourseState.waiting_price)
    await message.reply("💰 <b>Subscription Price</b>\n\nPlease enter the price in INR (e.g. <code>499</code>):")


@router.message(AddCourseState.waiting_price)
@admin_only
async def add_course_price(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        price = int(text)
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.reply("❌ Invalid price. Please enter a positive whole number (e.g., <code>499</code>):")
        return
        
    await state.update_data(price=price)
    data = await state.get_data()
    await state.set_state(AddCourseState.waiting_confirm)
    
    from keyboards.admin_kb import confirm_kb
    confirm_text = (
        f"📋 <b>Confirm Course Details</b>\n\n"
        f"📚 <b>Name:</b> {data['name']}\n"
        f"🆔 <b>Channel:</b> {data['channel_title']} (<code>{data['channel_id']}</code>)\n"
        f"💰 <b>Price:</b> ₹{data['price']}\n"
        f"⏳ <b>Duration:</b> 30 Days (Default)\n"
        f"📸 <b>Photo:</b> {'Yes' if data.get('photo_file_id') else 'No'}\n\n"
        f"Do you want to create this course?"
    )
    await message.reply(confirm_text, reply_markup=confirm_kb("confirm_add_course", "cancel_add_course"))


@router.callback_query(F.data == "confirm_add_course", AddCourseState.waiting_confirm)
@admin_only
async def cb_confirm_add_course(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    
    await courses_db.create_course(
        name=data["name"],
        channel_id=data["channel_id"],
        price=data["price"],
        photo_file_id=data.get("photo_file_id")
    )
    
    try:
        await callback.message.edit_text("✅ <b>Course created successfully!</b>")
    except Exception:
        await callback.message.answer("✅ <b>Course created successfully!</b>")
    
    courses = await courses_db.get_all_courses()
    from keyboards.admin_kb import courses_menu_kb
    text = "📋 <b>Course Management</b>\n\nManage courses, pricing, and statuses:"
    await callback.message.answer(text, reply_markup=courses_menu_kb(courses))
    await callback.answer()


@router.callback_query(F.data == "cancel_add_course", AddCourseState.waiting_confirm)
@admin_only
async def cb_cancel_add_course(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Course creation cancelled.")
    except Exception:
        await callback.message.answer("❌ Course creation cancelled.")
    
    courses = await courses_db.get_all_courses()
    from keyboards.admin_kb import courses_menu_kb
    text = "📋 <b>Course Management</b>\n\nManage courses, pricing, and statuses:"
    await callback.message.answer(text, reply_markup=courses_menu_kb(courses))
    await callback.answer()


@router.callback_query(F.data.startswith("course_detail_"))
@admin_only
async def cb_course_detail(callback: CallbackQuery):
    course_id = callback.data.replace("course_detail_", "")
    course = await courses_db.get_course(course_id)
    if not course:
        await callback.answer("❌ Course not found.")
        return
        
    text = (
        f"📚 <b>Course Details</b>\n\n"
        f"📖 <b>Name:</b> {course['name']}\n"
        f"💰 <b>Price:</b> ₹{course['price']}\n"
        f"⏳ <b>Duration:</b> {course.get('duration_days', 30)} days\n"
        f"🆔 <b>Channel ID:</b> <code>{course['channel_id']}</code>\n"
        f"⚙️ <b>Status:</b> {'🟢 Active' if course.get('is_active', True) else '🔴 Disabled'}\n"
    )
    
    from keyboards.admin_kb import course_detail_kb
    kb = course_detail_kb(course_id, course.get("is_active", True))
    
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


@router.callback_query(F.data.startswith("course_toggle_"))
@admin_only
async def cb_course_toggle(callback: CallbackQuery):
    course_id = callback.data.replace("course_toggle_", "")
    course = await courses_db.get_course(course_id)
    if not course:
        await callback.answer("❌ Course not found.")
        return
        
    new_status = not course.get("is_active", True)
    await courses_db.toggle_course(course_id, new_status)
    await callback.answer(f"✅ Course {'enabled' if new_status else 'disabled'}.")
    
    courses = await courses_db.get_all_courses()
    from keyboards.admin_kb import courses_menu_kb
    text = "📋 <b>Course Management</b>\n\nManage courses, pricing, and statuses:"
    
    try:
        await callback.message.edit_text(text, reply_markup=courses_menu_kb(courses))
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=courses_menu_kb(courses))


@router.callback_query(F.data.startswith("course_edit_name_"))
@admin_only
async def cb_edit_course_name_start(callback: CallbackQuery, state: FSMContext):
    course_id = callback.data.replace("course_edit_name_", "")
    await state.set_state(EditCourseState.waiting_name)
    await state.update_data(course_id=course_id)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"course_detail_{course_id}")]
    ])
    await callback.message.reply(
        "✏️ <b>Edit Course Name</b>\n\nPlease enter the new name for the course:",
        reply_markup=cancel_kb
    )
    await callback.answer()


@router.message(EditCourseState.waiting_name)
@admin_only
async def edit_course_name_input(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.reply("❌ Name cannot be empty. Please enter a valid course name:")
        return
        
    data = await state.get_data()
    course_id = data["course_id"]
    await state.clear()
    
    await courses_db.update_course(course_id, {"name": name})
    await message.reply("✅ <b>Course name updated successfully!</b>")
    
    course = await courses_db.get_course(course_id)
    text = (
        f"📚 <b>Course Details</b>\n\n"
        f"📖 <b>Name:</b> {course['name']}\n"
        f"💰 <b>Price:</b> ₹{course['price']}\n"
        f"⏳ <b>Duration:</b> {course.get('duration_days', 30)} days\n"
        f"🆔 <b>Channel ID:</b> <code>{course['channel_id']}</code>\n"
        f"⚙️ <b>Status:</b> {'🟢 Active' if course.get('is_active', True) else '🔴 Disabled'}\n"
    )
    from keyboards.admin_kb import course_detail_kb
    await message.reply(text, reply_markup=course_detail_kb(course_id, course.get("is_active", True)))


@router.callback_query(F.data.startswith("course_edit_price_"))
@admin_only
async def cb_edit_course_price_start(callback: CallbackQuery, state: FSMContext):
    course_id = callback.data.replace("course_edit_price_", "")
    await state.set_state(EditCourseState.waiting_price)
    await state.update_data(course_id=course_id)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"course_detail_{course_id}")]
    ])
    await callback.message.reply(
        "✏️ <b>Edit Course Price</b>\n\nPlease enter the new subscription price for the course in INR:",
        reply_markup=cancel_kb
    )
    await callback.answer()


@router.message(EditCourseState.waiting_price)
@admin_only
async def edit_course_price_input(message: Message, state: FSMContext):
    text = message.text.strip()
    try:
        price = int(text)
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.reply("❌ Invalid price. Please enter a positive whole number:")
        return
        
    data = await state.get_data()
    course_id = data["course_id"]
    await state.clear()
    
    await courses_db.update_course(course_id, {"price": price})
    await message.reply("✅ <b>Course price updated successfully!</b>")
    
    course = await courses_db.get_course(course_id)
    text = (
        f"📚 <b>Course Details</b>\n\n"
        f"📖 <b>Name:</b> {course['name']}\n"
        f"💰 <b>Price:</b> ₹{course['price']}\n"
        f"⏳ <b>Duration:</b> {course.get('duration_days', 30)} days\n"
        f"🆔 <b>Channel ID:</b> <code>{course['channel_id']}</code>\n"
        f"⚙️ <b>Status:</b> {'🟢 Active' if course.get('is_active', True) else '🔴 Disabled'}\n"
    )
    from keyboards.admin_kb import course_detail_kb
    await message.reply(text, reply_markup=course_detail_kb(course_id, course.get("is_active", True)))


@router.callback_query(F.data.startswith("course_edit_photo_"))
@admin_only
async def cb_edit_course_photo_start(callback: CallbackQuery, state: FSMContext):
    course_id = callback.data.replace("course_edit_photo_", "")
    await state.set_state(EditCourseState.waiting_photo)
    await state.update_data(course_id=course_id)
    
    from keyboards.admin_kb import skip_kb
    await callback.message.reply(
        "📸 <b>Edit Course Photo</b>\n\nPlease upload a new photo, or click Skip to remove the photo:",
        reply_markup=skip_kb(f"course_edit_photo_skip_{course_id}")
    )
    await callback.answer()


@router.message(EditCourseState.waiting_photo, F.photo)
@admin_only
async def edit_course_photo_input(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    course_id = data["course_id"]
    await state.clear()
    
    await courses_db.update_course(course_id, {"photo_file_id": photo_id})
    await message.reply("✅ <b>Course photo updated successfully!</b>")
    
    course = await courses_db.get_course(course_id)
    text = (
        f"📚 <b>Course Details</b>\n\n"
        f"📖 <b>Name:</b> {course['name']}\n"
        f"💰 <b>Price:</b> ₹{course['price']}\n"
        f"⏳ <b>Duration:</b> {course.get('duration_days', 30)} days\n"
        f"🆔 <b>Channel ID:</b> <code>{course['channel_id']}</code>\n"
        f"⚙️ <b>Status:</b> {'🟢 Active' if course.get('is_active', True) else '🔴 Disabled'}\n"
    )
    from keyboards.admin_kb import course_detail_kb
    await message.reply_photo(photo=photo_id, caption=text, reply_markup=course_detail_kb(course_id, course.get("is_active", True)))


@router.callback_query(F.data.startswith("course_edit_photo_skip_"), EditCourseState.waiting_photo)
@admin_only
async def cb_edit_course_photo_skip(callback: CallbackQuery, state: FSMContext):
    course_id = callback.data.replace("course_edit_photo_skip_", "")
    await state.clear()
    
    await courses_db.update_course(course_id, {"photo_file_id": None})
    try:
        await callback.message.edit_text("✅ <b>Course photo removed.</b>")
    except Exception:
        await callback.message.answer("✅ <b>Course photo removed.</b>")
    
    course = await courses_db.get_course(course_id)
    text = (
        f"📚 <b>Course Details</b>\n\n"
        f"📖 <b>Name:</b> {course['name']}\n"
        f"💰 <b>Price:</b> ₹{course['price']}\n"
        f"⏳ <b>Duration:</b> {course.get('duration_days', 30)} days\n"
        f"🆔 <b>Channel ID:</b> <code>{course['channel_id']}</code>\n"
        f"⚙️ <b>Status:</b> {'🟢 Active' if course.get('is_active', True) else '🔴 Disabled'}\n"
    )
    from keyboards.admin_kb import course_detail_kb
    await callback.message.answer(text, reply_markup=course_detail_kb(course_id, course.get("is_active", True)))
    await callback.answer()


# ── Reports ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_reports")
@router.callback_query(F.data.startswith("report_"))
@admin_only
async def cb_reports_menu(callback: CallbackQuery):
    now = datetime.now(timezone.utc)
    year, month = now.year, now.month
    
    if callback.data.startswith("report_"):
        parts = callback.data.split("_")
        if len(parts) == 3:
            year, month = int(parts[1]), int(parts[2])

    report_data = await subs_db.get_revenue_report(year, month)
    
    # Fetch all courses to map names
    courses = await courses_db.get_all_courses()
    course_map = {c["_id"]: c for c in courses}
    
    # Aggregate: course_id -> {new_count: int, new_rev: float, renewal_count: int, renewal_rev: float}
    aggregated = {}
    total_new_count = 0
    total_new_rev = 0
    total_ren_count = 0
    total_ren_rev = 0
    
    for item in report_data:
        course_id = item["_id"]["course_id"]
        is_renewal = item["_id"]["is_renewal"]
        count = item["count"]
        revenue = item["revenue"]
        
        if course_id not in aggregated:
            aggregated[course_id] = {
                "new_count": 0,
                "new_rev": 0,
                "ren_count": 0,
                "ren_rev": 0
            }
            
        if is_renewal:
            aggregated[course_id]["ren_count"] += count
            aggregated[course_id]["ren_rev"] += revenue
            total_ren_count += count
            total_ren_rev += revenue
        else:
            aggregated[course_id]["new_count"] += count
            aggregated[course_id]["new_rev"] += revenue
            total_new_count += count
            total_new_rev += revenue
            
    months_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    
    text_lines = [
        f"📊 <b>Revenue Report — {months_names[month-1]} {year}</b>\n",
    ]
    
    if not aggregated:
        text_lines.append("<i>No revenue recorded for this month.</i>\n")
    else:
        for c_id, stats in aggregated.items():
            course = course_map.get(c_id)
            c_name = course["name"] if course else f"Unknown Course ({c_id})"
            
            c_total_rev = stats["new_rev"] + stats["ren_rev"]
            text_lines.append(
                f"📚 <b>{c_name}</b>\n"
                f"  • New: {stats['new_count']} (₹{stats['new_rev']})\n"
                f"  • Renewal: {stats['ren_count']} (₹{stats['ren_rev']})\n"
                f"  • Total: ₹{c_total_rev}\n"
            )
            
        total_rev = total_new_rev + total_ren_rev
        text_lines.append(
            f"<b>Grand Totals:</b>\n"
            f"  • Total New: {total_new_count} (₹{total_new_rev})\n"
            f"  • Total Renewals: {total_ren_count} (₹{total_ren_rev})\n"
            f"  • <b>Total Revenue: ₹{total_rev}</b>"
        )
        
    from keyboards.admin_kb import report_kb
    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=report_kb(year, month)
    )
    await callback.answer()


# ── Broadcast ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
@admin_only
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.selecting_target)
    courses = await courses_db.get_all_courses()
    from keyboards.admin_kb import broadcast_target_kb
    await callback.message.edit_text(
        "📢 <b>Broadcast Setup</b>\n\n"
        "Please select the target group for this broadcast:",
        reply_markup=broadcast_target_kb(courses)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_target_"), BroadcastState.selecting_target)
@admin_only
async def cb_broadcast_target(callback: CallbackQuery, state: FSMContext):
    target_data = callback.data.replace("broadcast_target_", "")
    
    if target_data == "all":
        await state.update_data(target_type="all")
        await callback.message.edit_text(
            "📢 <b>Broadcast Message</b>\n\n"
            "Target: <b>All Users</b>\n\n"
            "Please send or forward the message you want to broadcast (supports formatting, photos, videos, documents):"
        )
        await state.set_state(BroadcastState.waiting_message)
    elif target_data == "user":
        await state.update_data(target_type="user")
        await callback.message.edit_text(
            "👤 <b>Broadcast Target: Direct User</b>\n\n"
            "Please enter the Target User ID:"
        )
    elif target_data.startswith("course_"):
        course_id = target_data.replace("course_", "")
        course = await courses_db.get_course(course_id)
        if not course:
            await callback.answer("Course not found!", show_alert=True)
            return
        await state.update_data(target_type="course", course_id=course_id)
        await callback.message.edit_text(
            f"📢 <b>Broadcast Message</b>\n\n"
            f"Target: Course <b>{course['name']}</b>\n\n"
            "Please send or forward the message you want to broadcast (supports formatting, photos, videos, documents):"
        )
        await state.set_state(BroadcastState.waiting_message)
        
    await callback.answer()


@router.message(BroadcastState.selecting_target)
@admin_only
async def broadcast_target_user_input(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get("target_type") == "user":
        try:
            user_id = int(message.text.strip())
            user = await users_db.get_user(user_id)
            if not user:
                await message.reply("❌ User not found in database. Please enter a valid User ID:")
                return
            await state.update_data(target_user_id=user_id)
            await state.set_state(BroadcastState.waiting_message)
            await message.reply(
                f"✅ Target set to user: <b>{user['name']}</b>\n\n"
                "Please send or forward the message you want to broadcast:"
            )
        except ValueError:
            await message.reply("❌ Invalid User ID! Please enter a numeric User ID:")
    else:
        pass


@router.message(BroadcastState.waiting_message)
@admin_only
async def broadcast_message_input(message: Message, state: FSMContext):
    msg_data = {}
    if message.text:
        msg_data["type"] = "text"
        msg_data["text"] = message.html_text
    elif message.photo:
        msg_data["type"] = "photo"
        msg_data["photo"] = message.photo[-1].file_id
        msg_data["caption"] = message.html_text
    elif message.video:
        msg_data["type"] = "video"
        msg_data["video"] = message.video.file_id
        msg_data["caption"] = message.html_text
    elif message.document:
        msg_data["type"] = "document"
        msg_data["document"] = message.document.file_id
        msg_data["caption"] = message.html_text
    else:
        await message.reply("❌ Unsupported message type. Please send text, photo, video, or document.")
        return

    await state.update_data(broadcast_msg=msg_data)
    await state.set_state(BroadcastState.waiting_confirm)
    
    from keyboards.admin_kb import confirm_kb
    await message.reply(
        "⚠️ <b>Confirm Broadcast Sending</b>\n\n"
        "Please review the broadcast. Once confirmed, it will be sent to the target(s).",
        reply_markup=confirm_kb("confirm_broadcast", "cancel_broadcast")
    )


@router.callback_query(F.data == "confirm_broadcast", BroadcastState.waiting_confirm)
@admin_only
async def cb_broadcast_send(callback: CallbackQuery, state: FSMContext):
    import logging
    import asyncio
    data = await state.get_data()
    msg_data = data.get("broadcast_msg")
    target_type = data.get("target_type")
    
    user_ids = []
    if target_type == "all":
        users = await users_db.get_all_users(limit=999999)
        user_ids = [u["_id"] for u in users]
    elif target_type == "course":
        course_id = data.get("course_id")
        user_ids = await subs_db.get_active_user_ids_for_course(course_id)
    elif target_type == "user":
        user_ids = [data.get("target_user_id")]

    await callback.message.edit_text(f"⏳ Sending broadcast to {len(user_ids)} targets...")
    
    success_count = 0
    fail_count = 0
    
    for uid in user_ids:
        try:
            if msg_data["type"] == "text":
                await callback.bot.send_message(uid, msg_data["text"])
            elif msg_data["type"] == "photo":
                await callback.bot.send_photo(uid, msg_data["photo"], caption=msg_data.get("caption"))
            elif msg_data["type"] == "video":
                await callback.bot.send_video(uid, msg_data["video"], caption=msg_data.get("caption"))
            elif msg_data["type"] == "document":
                await callback.bot.send_document(uid, msg_data["document"], caption=msg_data.get("caption"))
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.warning(f"Broadcast failed for user {uid}: {e}")
            fail_count += 1
            
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ <b>Broadcast Finished</b>\n\n"
        f"📈 <b>Stats:</b>\n"
        f"• Total Targets: {len(user_ids)}\n"
        f"• Sent: {success_count}\n"
        f"• Failed: {fail_count}"
    )
    
    from keyboards.admin_kb import admin_panel_kb
    await callback.message.answer("🛠 <b>Admin Control Panel</b>", reply_markup=admin_panel_kb())
    await callback.answer()


@router.callback_query(F.data == "cancel_broadcast")
@admin_only
async def cb_cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text("❌ Broadcast cancelled.")
    except Exception:
        await callback.message.answer("❌ Broadcast cancelled.")
        
    from keyboards.admin_kb import admin_panel_kb
    await callback.message.answer("🛠 <b>Admin Control Panel</b>", reply_markup=admin_panel_kb())
    await callback.answer()


# ── Search ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_search")
@admin_only
async def cb_search_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_query)
    await callback.message.edit_text("🔍 <b>User Search</b>\n\n"
                                     "Please enter a partial name or username to search:")
    await callback.answer()


@router.message(SearchState.waiting_query)
@admin_only
async def search_execute(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.reply("❌ Search query cannot be empty. Please enter a search query:")
        return
        
    await state.clear()
    results = await users_db.search_users(query)
    
    if not results:
        await message.reply(f"❌ No users found matching '<code>{query}</code>'.")
        from keyboards.admin_kb import admin_panel_kb
        await message.reply("🛠 <b>Admin Control Panel</b>", reply_markup=admin_panel_kb())
        return
        
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for user in results[:10]:
        username_str = f" (@{user['username']})" if user.get('username') else ""
        rows.append([
            InlineKeyboardButton(
                text=f"👤 {user['name']}{username_str}",
                callback_data=f"profile_{user['_id']}"
            )
        ])
    rows.append([InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_panel")])
    
    await message.reply(
        f"🔍 <b>Search Results for '{query}':</b>\n"
        f"Found {len(results)} matches (showing top {min(len(results), 10)}):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


# ── Settings ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_settings")
@admin_only
async def cb_settings(callback: CallbackQuery):
    settings = await db_module.get_settings()
    from keyboards.admin_kb import settings_kb
    await callback.message.edit_text(
        "⚙️ <b>Global Settings</b>\n\n"
        f"⏳ <b>Invite Link Expiry:</b> {settings.get('invite_link_expiry_hours', 2)} hours\n"
        f"🔔 <b>Warning Notifications:</b> {', '.join(map(str, settings.get('warning_hours', [48, 12])))} hours before expiry",
        reply_markup=settings_kb(settings)
    )
    await callback.answer()


@router.callback_query(F.data == "settings_expiry")
@admin_only
async def cb_settings_expiry(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_invite_expiry)
    await callback.message.edit_text("⏳ <b>Invite Link Expiry</b>\n\n"
                                     "Enter new invite link expiry duration in hours (positive integer):")
    await callback.answer()


@router.message(SettingsState.waiting_invite_expiry)
@admin_only
async def settings_expiry_input(message: Message, state: FSMContext):
    try:
        hours = int(message.text.strip())
        if hours <= 0:
            raise ValueError()
    except ValueError:
        await message.reply("❌ Invalid input! Please enter a positive integer for hours:")
        return
        
    await state.clear()
    await db_module.update_settings({"invite_link_expiry_hours": hours})
    
    settings = await db_module.get_settings()
    from keyboards.admin_kb import settings_kb
    await message.reply(
        "✅ <b>Settings updated successfully!</b>\n\n"
        "⚙️ <b>Global Settings</b>\n\n"
        f"⏳ <b>Invite Link Expiry:</b> {settings.get('invite_link_expiry_hours', 2)} hours\n"
        f"🔔 <b>Warning Notifications:</b> {', '.join(map(str, settings.get('warning_hours', [48, 12])))} hours before expiry",
        reply_markup=settings_kb(settings)
    )


@router.callback_query(F.data == "settings_warnings")
@admin_only
async def cb_settings_warnings(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_warning_hours)
    await callback.message.edit_text("🔔 <b>Warning Notifications</b>\n\n"
                                     "Enter warning intervals in hours (comma-separated, e.g., 48,12):")
    await callback.answer()


@router.message(SettingsState.waiting_warning_hours)
@admin_only
async def settings_warnings_input(message: Message, state: FSMContext):
    try:
        hours_list = [int(x.strip()) for x in message.text.split(",") if x.strip()]
        if not hours_list or any(h <= 0 for h in hours_list):
            raise ValueError()
    except ValueError:
        await message.reply("❌ Invalid input! Please enter comma-separated positive integers (e.g. 48,12):")
        return
        
    await state.clear()
    await db_module.update_settings({"warning_hours": hours_list})
    
    settings = await db_module.get_settings()
    from keyboards.admin_kb import settings_kb
    await message.reply(
        "✅ <b>Settings updated successfully!</b>\n\n"
        "⚙️ <b>Global Settings</b>\n\n"
        f"⏳ <b>Invite Link Expiry:</b> {settings.get('invite_link_expiry_hours', 2)} hours\n"
        f"🔔 <b>Warning Notifications:</b> {', '.join(map(str, settings.get('warning_hours', [48, 12])))} hours before expiry",
        reply_markup=settings_kb(settings)
    )


# ── Ban & Unban ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ban_"), ~F.data.startswith("ban_confirm_"))
@admin_only
async def cb_ban_user_start(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    from keyboards.admin_kb import confirm_kb
    await callback.message.edit_text(
        f"⚠️ <b>Confirm Ban User</b>\n\n"
        f"Are you sure you want to ban user <code>{user_id}</code>?\n"
        f"This user will be blocked from using the bot.",
        reply_markup=confirm_kb(f"ban_confirm_{user_id}", f"profile_{user_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ban_confirm_"))
@admin_only
async def cb_ban_user_confirm(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    await users_db.ban_user(user_id)
    await callback.message.edit_text(
        f"✅ <b>User Banned</b>\n\n"
        f"User <code>{user_id}</code> has been banned."
    )
    
    # Return to profile
    from keyboards.admin_kb import profile_kb
    user = await users_db.get_user(user_id)
    if user:
        # Notify log channel
        admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
        await log_to_channel(
            callback.bot,
            f"🚫 <b>User Banned</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {user['name']}" + (f" ({user['username']})" if user.get('username') else "") + f"\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
            f"✍️ <b>Action by Admin:</b> {admin_username}"
        )

        stats = await users_db.get_user_stats(user_id)
        active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
        active_lines = []
        for sub in active_subs:
            course = await courses_db.get_course(str(sub["course_id"]))
            if course:
                days_left = (sub["expires_at"] - datetime.now(timezone.utc)).days
                active_lines.append(f"• <b>{course['name']}</b> ({max(days_left, 0)} days left)")
        active_subs_text = "\n".join(active_lines) if active_lines else "• None"
        registered_str = user["registered_at"].strftime("%b %d, %Y")
        await callback.message.answer(
            f"👤 <b>User Profile: {user['name']}</b>\n\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"🔗 Username: {user['username'] or 'None'}\n"
            f"📅 Registered: {registered_str}\n"
            f"🚫 Status: 🚫 BANNED\n\n"
            f"📊 <b>Subscription Stats:</b>\n"
            f"• Total Subscriptions: {stats['total_subs']}\n"
            f"• Total Paid: ₹{stats['total_paid']}\n\n"
            f"📚 <b>Active Subscriptions:</b>\n{active_subs_text}",
            reply_markup=profile_kb(user_id, is_banned=True)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("unban_"))
@admin_only
async def cb_unban_user(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await users_db.unban_user(user_id)
    await callback.message.edit_text(
        f"✅ <b>User Unbanned</b>\n\n"
        f"User <code>{user_id}</code> has been unbanned."
    )
    
    # Return to profile
    from keyboards.admin_kb import profile_kb
    user = await users_db.get_user(user_id)
    if user:
        # Notify log channel
        admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
        await log_to_channel(
            callback.bot,
            f"🟢 <b>User Unbanned</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User:</b> {user['name']}" + (f" ({user['username']})" if user.get('username') else "") + f"\n"
            f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
            f"✍️ <b>Action by Admin:</b> {admin_username}"
        )

        stats = await users_db.get_user_stats(user_id)
        active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
        active_lines = []
        for sub in active_subs:
            course = await courses_db.get_course(str(sub["course_id"]))
            if course:
                days_left = (sub["expires_at"] - datetime.now(timezone.utc)).days
                active_lines.append(f"• <b>{course['name']}</b> ({max(days_left, 0)} days left)")
        active_subs_text = "\n".join(active_lines) if active_lines else "• None"
        registered_str = user["registered_at"].strftime("%b %d, %Y")
        await callback.message.answer(
            f"👤 <b>User Profile: {user['name']}</b>\n\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"🔗 Username: {user['username'] or 'None'}\n"
            f"📅 Registered: {registered_str}\n"
            f"🚫 Status: 🟢 Normal\n\n"
            f"📊 <b>Subscription Stats:</b>\n"
            f"• Total Subscriptions: {stats['total_subs']}\n"
            f"• Total Paid: ₹{stats['total_paid']}\n\n"
            f"📚 <b>Active Subscriptions:</b>\n{active_subs_text}",
            reply_markup=profile_kb(user_id, is_banned=False)
        )
    await callback.answer()


# ── Kick All ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("kickall_"), ~F.data.startswith("kickall_confirm_"))
@admin_only
async def cb_kickall_start(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    from keyboards.admin_kb import confirm_kb
    await callback.message.edit_text(
        f"⚠️ <b>Confirm Kick All</b>\n\n"
        f"Are you sure you want to kick user <code>{user_id}</code> from all active channels?\n"
        f"This will terminate all their active subscriptions.",
        reply_markup=confirm_kb(f"kickall_confirm_{user_id}", f"profile_{user_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("kickall_confirm_"))
@admin_only
async def cb_kickall_confirm(callback: CallbackQuery):
    import logging
    user_id = int(callback.data.split("_")[-1])
    active_subs = await subs_db.get_active_subscriptions_for_user(user_id)
    
    kicked_courses = []
    for sub in active_subs:
        course = await courses_db.get_course(str(sub["course_id"]))
        if course:
            try:
                await callback.bot.ban_chat_member(course["channel_id"], user_id)
                await callback.bot.unban_chat_member(course["channel_id"], user_id)
            except Exception as e:
                logging.info(f"Failed to kick user {user_id} from channel {course['channel_id']}: {e}")
            
            await subs_db.kick_subscription(str(sub["_id"]), reason="admin_kick_all")
            kicked_courses.append(course["name"])
            
    if kicked_courses:
        courses_str = ", ".join(kicked_courses)
        try:
            await callback.bot.send_message(
                user_id,
                f"❌ <b>Access Revoked</b>\n\n"
                f"Your subscription access to the following courses has been terminated by the administrator:\n"
                f"📚 <b>{courses_str}</b>\n\n"
                f"Please contact the admin if you have any questions."
            )
        except Exception as e:
            logging.warning(f"Failed to notify kicked user {user_id}: {e}")
            
        await callback.message.edit_text(
            f"✅ <b>Success:</b> User <code>{user_id}</code> kicked from {len(kicked_courses)} courses: {courses_str}."
        )
    else:
        await callback.message.edit_text("ℹ️ User has no active subscriptions to kick.")
        
    await callback.answer()



