"""
User-facing keyboard definitions.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def register_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Register", callback_data="user_register")]
    ])

def home_kb(has_history: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📊 My Status", callback_data="user_status"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="user_refresh")
        ],
        [
            InlineKeyboardButton(text="🛍 Available Courses", callback_data="user_available_courses")
        ]
    ]
    if has_history:
        rows.append([
            InlineKeyboardButton(text="📋 My History", callback_data="user_history")
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def status_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="user_home")]
    ])

def available_courses_kb(courses: list) -> InlineKeyboardMarkup:
    keyboard = []
    for course in courses:
        keyboard.append([
            InlineKeyboardButton(text=course["name"], callback_data=f"user_course_{course['_id']}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 Back", callback_data="user_home")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def course_subscribe_kb(admin_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Contact Admin to Subscribe", url=admin_url)],
        [InlineKeyboardButton(text="🔙 Back", callback_data="user_available_courses")]
    ])
