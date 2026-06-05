from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from database import users as users_db

class BannedUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user and await users_db.is_banned(user.id):
            if isinstance(event, Message):
                await event.answer(
                    "🚫 <b>Access Restricted</b>\n\n"
                    "You are not allowed to use this bot.\n"
                    "Contact admin if you believe this is a mistake."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Access Restricted", show_alert=True)
            return
        return await handler(event, data)
