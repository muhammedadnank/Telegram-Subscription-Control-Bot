"""
Main entry point for the Telegram Subscription Control Bot.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.mongo import MongoStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN, MONGO_URI, DB_NAME
from database.db import connect_db, close_db, create_indexes, init_settings
from handlers import user, admin
from scheduler.tasks import setup_scheduler

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

dp.include_router(user.router)
dp.include_router(admin.router)


async def on_startup():
    await connect_db()
    await create_indexes()
    await init_settings()
    setup_scheduler(bot)
    logging.info("Bot started successfully")


async def on_shutdown():
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
