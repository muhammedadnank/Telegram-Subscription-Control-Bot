"""
Configuration settings for the Telegram Subscription Control Bot.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
MONGO_URI: str = os.getenv("MONGO_URI")
DB_NAME: str = os.getenv("DB_NAME", "subscription_bot")

# Validation
assert BOT_TOKEN, "BOT_TOKEN missing in .env"
assert ADMIN_ID_RAW, "ADMIN_ID missing in .env"
assert MONGO_URI, "MONGO_URI missing in .env"

try:
    ADMIN_ID: int = int(ADMIN_ID_RAW)
except ValueError:
    raise ValueError("ADMIN_ID must be a valid integer in .env")

LOG_CHANNEL_ID_RAW = os.getenv("LOG_CHANNEL_ID")
LOG_CHANNEL_ID: int = None
if LOG_CHANNEL_ID_RAW:
    try:
        LOG_CHANNEL_ID = int(LOG_CHANNEL_ID_RAW)
    except ValueError:
        raise ValueError("LOG_CHANNEL_ID must be a valid integer in .env")
