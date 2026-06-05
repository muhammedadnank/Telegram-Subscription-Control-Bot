"""
Database connection, indexing, and global settings management.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

client: AsyncIOMotorClient = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URI, tz_aware=True)
    db = client[DB_NAME]

async def close_db():
    global client
    if client:
        client.close()

async def create_indexes():
    # users
    await db.users.create_index("username")
    await db.users.create_index("is_banned")

    # courses
    await db.courses.create_index("is_active")
    await db.courses.create_index("channel_id", unique=True)

    # subscriptions
    await db.subscriptions.create_index("user_id")
    await db.subscriptions.create_index("course_id")
    await db.subscriptions.create_index("status")
    await db.subscriptions.create_index("expires_at")
    await db.subscriptions.create_index("created_at")
    await db.subscriptions.create_index(
        [("user_id", 1), ("course_id", 1)]
    )
    await db.subscriptions.create_index(
        [("status", 1), ("expires_at", 1)]
    )

async def init_settings():
    from config import ADMIN_ID
    existing = await db.settings.find_one({"_id": "global_settings"})
    if not existing:
        await db.settings.insert_one({
            "_id": "global_settings",
            "admin_id": ADMIN_ID,
            "warning_hours": [48, 12],
            "invite_link_expiry_hours": 2
        })

async def get_settings() -> dict:
    return await db.settings.find_one({"_id": "global_settings"})

async def update_settings(data: dict):
    await db.settings.update_one(
        {"_id": "global_settings"},
        {"$set": data}
    )
