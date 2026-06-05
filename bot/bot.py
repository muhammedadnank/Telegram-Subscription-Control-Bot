"""
Main entry point for the Telegram Subscription Control Bot.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.mongo import MongoStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, MONGO_URI, DB_NAME, ADMIN_ID
from database.db import connect_db, close_db, create_indexes, init_settings
from handlers import user, admin
from middlewares.banned import BannedUserMiddleware
from scheduler.tasks import setup_scheduler
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

storage = MongoStorage.from_url(MONGO_URI, db_name=DB_NAME)
dp = Dispatcher(storage=storage)

# Register middlewares
dp.message.outer_middleware(BannedUserMiddleware())
dp.callback_query.outer_middleware(BannedUserMiddleware())

# Global Error Handler
@dp.errors()
async def error_handler(event: ErrorEvent):
    exception = event.exception
    if isinstance(exception, TelegramBadRequest):
        exc_str = str(exception).lower()
        if "message is not modified" in exc_str:
            logging.warning("Stale callback click: message not modified")
            return True
        if "query is too old" in exc_str or "query id is invalid" in exc_str:
            logging.warning("Stale callback click: query is too old or invalid")
            return True
    
    logging.exception(f"Unhandled exception: {exception}")
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🚨 <b>Unhandled Exception occurred!</b>\n\n<code>{exception}</code>"
        )
    except Exception as e:
        logging.error(f"Failed to send error alert to admin: {e}")
    return True

dp.include_router(user.router)
dp.include_router(admin.router)



async def on_startup():
    await connect_db()
    await create_indexes()
    await init_settings()
    setup_scheduler(bot)
    logging.info("Bot started successfully")
    from utils.logger import log_to_channel
    await log_to_channel(
        bot,
        f"🤖 <b>Bot Started Successfully</b>\n"
        f"🟢 Bot is now online and active."
    )


async def on_shutdown():
    from utils.logger import log_to_channel
    await log_to_channel(
        bot,
        f"🤖 <b>Bot Shutting Down</b>\n"
        f"🔴 Bot is going offline."
    )
    await close_db()
    logging.info("Bot shut down")


async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(
        bot,
        allowed_updates=[
            "message",
            "callback_query",
            "chat_member",
            "my_chat_member"
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())
