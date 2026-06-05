"""
Course CRUD database operations.
"""

from datetime import datetime, timezone
from bson import ObjectId
from database.db import db

async def get_all_courses(active_only: bool = False) -> list[dict]:
    query = {"is_active": True} if active_only else {}
    cursor = db.courses.find(query)
    return await cursor.to_list(None)

async def get_course(course_id: str) -> dict | None:
    return await db.courses.find_one({"_id": ObjectId(course_id)})

async def get_course_by_channel(channel_id: int) -> dict | None:
    return await db.courses.find_one({"channel_id": channel_id})

async def create_course(
    name: str,
    channel_id: int,
    price: int,
    duration_days: int = 30,
    photo_file_id: str | None = None
) -> str:
    result = await db.courses.insert_one({
        "name": name,
        "channel_id": channel_id,
        "price": price,
        "duration_days": duration_days,
        "is_active": True,
        "photo_file_id": photo_file_id,
        "created_at": datetime.now(timezone.utc)
    })
    return str(result.inserted_id)

async def update_course(course_id: str, data: dict):
    await db.courses.update_one(
        {"_id": ObjectId(course_id)},
        {"$set": data}
    )

async def toggle_course(course_id: str, is_active: bool):
    await db.courses.update_one(
        {"_id": ObjectId(course_id)},
        {"$set": {"is_active": is_active}}
    )

async def get_active_subscriber_count(course_id: str) -> int:
    return await db.subscriptions.count_documents({
        "course_id": ObjectId(course_id),
        "status": "active"
    })
