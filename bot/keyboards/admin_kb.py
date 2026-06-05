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


def profile_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 Give Access", callback_data=f"give_{user_id}"),
            InlineKeyboardButton(text="📋 History",     callback_data=f"history_{user_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Kick All",    callback_data=f"kickall_{user_id}"),
            InlineKeyboardButton(text="🚫 Ban User",    callback_data=f"ban_{user_id}")
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
