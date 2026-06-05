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
