"""
User CRUD database operations.
"""

from datetime import datetime, timezone
import re
import database.db as db_module

async def get_user(user_id: int) -> dict | None:
    return await db_module.db.users.find_one({"_id": user_id})

async def create_user(user_id: int, name: str, username: str | None, photo_file_id: str | None):
    await db_module.db.users.insert_one({
        "_id": user_id,
        "name": name,
        "username": username,
        "photo_file_id": photo_file_id,
        "registered_at": datetime.now(timezone.utc),
        "is_banned": False
    })

async def is_banned(user_id: int) -> bool:
    user = await db_module.db.users.find_one({"_id": user_id}, {"is_banned": 1})
    if not user:
        return False
    return user.get("is_banned", False)

async def ban_user(user_id: int):
    await db_module.db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_banned": True}}
    )

async def unban_user(user_id: int):
    await db_module.db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_banned": False}}
    )

async def get_all_users(skip: int = 0, limit: int = 50) -> list[dict]:
    cursor = db_module.db.users.find({}).skip(skip).limit(limit)
    return await cursor.to_list(None)

async def get_banned_users() -> list[dict]:
    cursor = db_module.db.users.find({"is_banned": True})
    return await cursor.to_list(None)

async def search_users(query: str) -> list[dict]:
    """Case-insensitive partial match on name or username."""
    pattern = re.compile(query, re.IGNORECASE)
    cursor = db_module.db.users.find({
        "$or": [
            {"name": {"$regex": pattern}},
            {"username": {"$regex": pattern}}
        ]
    })
    return await cursor.to_list(None)

async def get_user_stats(user_id: int) -> dict:
    """Returns total subscriptions count and total amount paid."""
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$user_id",
            "total_subs": {"$sum": 1},
            "total_paid": {"$sum": "$amount_paid"}
        }}
    ]
    cursor = db_module.db.subscriptions.aggregate(pipeline)
    result = await cursor.to_list(1)
    if not result:
        return {"total_subs": 0, "total_paid": 0}
    return {
        "total_subs": result[0].get("total_subs", 0),
        "total_paid": result[0].get("total_paid", 0)
    }
