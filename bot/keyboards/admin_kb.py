"""
Admin-facing keyboard definitions.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_entry_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Open Admin Panel", callback_data="admin_panel")]
    ])


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Users",     callback_data="admin_users"),
            InlineKeyboardButton(text="📋 Courses",   callback_data="admin_courses")
        ],
        [
            InlineKeyboardButton(text="📊 Reports",   callback_data="admin_reports"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="🔍 Search",    callback_data="admin_search"),
            InlineKeyboardButton(text="⚙️ Settings",  callback_data="admin_settings")
        ]
    ])


def users_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Active Users",      callback_data="admin_active_users")],
        [InlineKeyboardButton(text="❌ Expired / Kicked",  callback_data="admin_expired_users")],
        [InlineKeyboardButton(text="🚫 Banned Users",      callback_data="admin_banned_users")],
        [InlineKeyboardButton(text="🔙 Back",              callback_data="admin_panel")]
    ])


def user_quick_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 Give Access", callback_data=f"give_{user_id}"),
            InlineKeyboardButton(text="👁 Profile",     callback_data=f"profile_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🚫 Ban",         callback_data=f"ban_{user_id}"),
            InlineKeyboardButton(text="🔙 Back",        callback_data="admin_active_users")
        ]
    ])


def profile_kb(user_id: int, is_banned: bool = False) -> InlineKeyboardMarkup:
    ban_text = "🟢 Unban User" if is_banned else "🚫 Ban User"
    ban_callback = f"unban_{user_id}" if is_banned else f"ban_{user_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 Give Access", callback_data=f"give_{user_id}"),
            InlineKeyboardButton(text="📋 History",     callback_data=f"history_{user_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Kick All",    callback_data=f"kickall_{user_id}"),
            InlineKeyboardButton(text=ban_text,        callback_data=ban_callback)
        ],
        [InlineKeyboardButton(text="🔙 Back",           callback_data="admin_users")]
    ])


def pagination_kb(
    page: int,
    total_pages: int,
    prefix: str,
    back_data: str
) -> InlineKeyboardMarkup:
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀ Prev", callback_data=f"{prefix}_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Next ▶", callback_data=f"{prefix}_page_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[
        nav_row,
        [InlineKeyboardButton(text="🔙 Back", callback_data=back_data)]
    ])


def course_select_kb(courses: list[dict], user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for c in courses:
        rows.append([InlineKeyboardButton(
            text=f"📚 {c['name']} — ₹{c['price']}",
            callback_data=f"give_{user_id}:{str(c['_id'])}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"profile_{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_give_kb(user_id: int, course_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_give_{user_id}:{course_id}"),
            InlineKeyboardButton(text="❌ Cancel",  callback_data=f"give_{user_id}")
        ]
    ])


def courses_menu_kb(courses: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for c in courses:
        status_icon = "🟢" if c.get("is_active", True) else "🔴"
        rows.append([
            InlineKeyboardButton(text=f"{status_icon} {c['name']} (₹{c['price']})", callback_data=f"course_detail_{str(c['_id'])}"),
            InlineKeyboardButton(
                text="🔴 Disable" if c.get("is_active", True) else "🟢 Enable",
                callback_data=f"course_toggle_{str(c['_id'])}"
            )
        ])
    rows.append([InlineKeyboardButton(text="➕ Add Course", callback_data="admin_add_course")])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def course_detail_kb(course_id: str, is_active: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Edit Name", callback_data=f"course_edit_name_{course_id}"),
            InlineKeyboardButton(text="✏️ Edit Price", callback_data=f"course_edit_price_{course_id}")
        ],
        [
            InlineKeyboardButton(text="📸 Edit Photo", callback_data=f"course_edit_photo_{course_id}"),
            InlineKeyboardButton(
                text="🔴 Disable" if is_active else "🟢 Enable",
                callback_data=f"course_toggle_{course_id}"
            )
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_courses")]
    ])


def confirm_kb(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    """Generic confirm/cancel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=confirm_data),
            InlineKeyboardButton(text="❌ Cancel",  callback_data=cancel_data)
        ]
    ])


def skip_kb(callback_data: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Skip", callback_data=callback_data)]
    ])


def settings_kb(settings: dict) -> InlineKeyboardMarkup:
    expiry_hours = settings.get("invite_link_expiry_hours", 2)
    warning_hours = ", ".join(map(str, settings.get("warning_hours", [48, 12])))
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⏳ Invite Link Expiry ({expiry_hours}h)", callback_data="settings_expiry")],
        [InlineKeyboardButton(text=f"🔔 Warning Hours ({warning_hours}h)", callback_data="settings_warnings")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
    ])


def broadcast_target_kb(courses: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📢 All Users", callback_data="broadcast_target_all")]
    ]
    for c in courses:
        rows.append([InlineKeyboardButton(text=f"📚 Course: {c['name']}", callback_data=f"broadcast_target_course_{str(c['_id'])}")])
    rows.append([InlineKeyboardButton(text="👤 Direct User ID", callback_data="broadcast_target_user")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def report_kb(year: int, month: int) -> InlineKeyboardMarkup:
    # Previous month
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    
    # Next month
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️ Prev", callback_data=f"report_{prev_year}_{prev_month}"),
            InlineKeyboardButton(text=f"📅 {months[month-1]} {year}", callback_data="noop"),
            InlineKeyboardButton(text="Next ▶️", callback_data=f"report_{next_year}_{next_month}")
        ],
        [
            InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")
        ]
    ])


