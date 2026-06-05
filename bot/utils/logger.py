"""
Utility helper to log bot activities to a dedicated channel/group.
"""

import logging
from aiogram import Bot
from config import LOG_CHANNEL_ID

async def log_to_channel(bot: Bot, text: str):
    """
    Send an HTML-formatted log message to the configured log channel/group.
    Fails silently with a logger warning if the send fails.
    """
    if not LOG_CHANNEL_ID:
        return
    try:
        await bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=text,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"Failed to send log to channel {LOG_CHANNEL_ID}: {e}")
