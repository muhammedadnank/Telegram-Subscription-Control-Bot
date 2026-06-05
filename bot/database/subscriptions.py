"""
Subscription CRUD database operations.
"""

from datetime import datetime, timezone, timedelta
from bson import ObjectId
import database.db as db_module

async def get_active_subscription(user_id: int, course_id: str) -> dict | None:
    return await db_module.db.subscriptions.find_one({
        "user_id": user_id,
        "course_id": ObjectId(course_id),
        "status": "active"
    })

async def get_pending_subscription(user_id: int, channel_id: int) -> dict | None:
    """Used in chat_member join handler — match by channel via course lookup."""
    course = await db_module.db.courses.find_one({"channel_id": channel_id})
    if not course:
        return None
    return await db_module.db.subscriptions.find_one({
        "user_id": user_id,
        "course_id": course["_id"],
        "status": "pending_join"
    })

async def check_is_renewal(user_id: int, course_id: str) -> bool:
    existing = await db_module.db.subscriptions.find_one({
        "user_id": user_id,
        "course_id": ObjectId(course_id),
        "status": {"$in": ["active", "expired", "kicked", "extended"]}
    })
    return existing is not None

async def create_subscription(
    user_id: int,
    course_id: str,
    invite_link: str,
    amount_paid: int,
    is_renewal: bool
) -> str:
    result = await db_module.db.subscriptions.insert_one({
        "user_id": user_id,
        "course_id": ObjectId(course_id),
        "invite_link": invite_link,
        "status": "pending_join",
        "is_renewal": is_renewal,
        "joined_at": None,
        "expires_at": None,
        "left_at": None,
        "days_used": None,
        "reminder_48h_sent": False,
        "reminder_12h_sent": False,
        "amount_paid": amount_paid,
        "kicked_at": None,
        "kick_reason": None,
        "created_at": datetime.now(timezone.utc)
    })
    return str(result.inserted_id)

async def activate_subscription(sub_id: str, duration_days: int):
    now = datetime.now(timezone.utc)
    await db_module.db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "status": "active",
            "joined_at": now,
            "expires_at": now + timedelta(days=duration_days)
        }}
    )

async def record_manual_leave(sub_id: str):
    now = datetime.now(timezone.utc)
    sub = await db_module.db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    days_used = (now - sub["joined_at"]).days if sub.get("joined_at") else 0
    await db_module.db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "left_at": now,
            "days_used": days_used
        }}
    )

async def expire_subscription(sub_id: str, reason: str = "subscription_expired"):
    now = datetime.now(timezone.utc)
    await db_module.db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "status": "expired",
            "kicked_at": now,
            "kick_reason": reason
        }}
    )

async def kick_subscription(sub_id: str, reason: str = "manual_kick"):
    now = datetime.now(timezone.utc)
    await db_module.db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "status": "kicked",
            "kicked_at": now,
            "kick_reason": reason
        }}
    )

async def get_active_subscriptions_for_user(user_id: int) -> list[dict]:
    cursor = db_module.db.subscriptions.find({
        "user_id": user_id,
        "status": "active"
    })
    return await cursor.to_list(None)

async def get_subscription_history(user_id: int) -> list[dict]:
    cursor = db_module.db.subscriptions.find(
        {"user_id": user_id}
    ).sort("created_at", -1)
    return await cursor.to_list(None)

async def get_active_subscriptions_by_course(
    course_id: str,
    skip: int = 0,
    limit: int = 5
) -> list[dict]:
    cursor = db_module.db.subscriptions.find({
        "course_id": ObjectId(course_id),
        "status": "active"
    }).sort("expires_at", 1).skip(skip).limit(limit)
    return await cursor.to_list(None)

async def get_expired_subscriptions(skip: int = 0, limit: int = 5) -> list[dict]:
    cursor = db_module.db.subscriptions.find({
        "status": {"$in": ["expired", "kicked"]}
    }).sort("kicked_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(None)

async def get_expiring_soon(hours: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=hours)
    window_end = window_start + timedelta(hours=1)
    field = f"reminder_{hours}h_sent"
    cursor = db_module.db.subscriptions.find({
        "status": "active",
        "expires_at": {"$gte": window_start, "$lt": window_end},
        field: False
    })
    return await cursor.to_list(None)

async def mark_reminder_sent(sub_id: str, hours: int):
    field = f"reminder_{hours}h_sent"
    await db_module.db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {field: True}}
    )
