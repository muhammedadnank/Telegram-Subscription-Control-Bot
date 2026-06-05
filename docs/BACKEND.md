# Backend Schema & Implementation Plan
# Telegram Subscription Control Bot

**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2025

---

## Table of Contents

1. [Implementation Phases](#1-implementation-phases)
2. [Database Layer](#2-database-layer)
   - [db.py — Connection & Init](#21-dbpy--connection--init)
   - [users.py — CRUD](#22-userspy--crud)
   - [courses.py — CRUD](#23-coursespy--crud)
   - [subscriptions.py — CRUD](#24-subscriptionspy--crud)
3. [Config & Entry Point](#3-config--entry-point)
4. [FSM States](#4-fsm-states)
5. [Keyboards](#5-keyboards)
   - [user_kb.py](#51-user_kbpy)
   - [admin_kb.py](#52-admin_kbpy)
6. [Handlers](#6-handlers)
   - [user.py](#61-userpy)
   - [admin.py](#62-adminpy)
7. [Scheduler Tasks](#7-scheduler-tasks)
8. [Invite Utils](#8-invite-utils)
9. [Implementation Order](#9-implementation-order)
10. [Testing Checklist](#10-testing-checklist)
11. [Deployment Checklist](#11-deployment-checklist)

---

## 1. Implementation Phases

| Phase | Scope | Priority |
|---|---|---|
| **Phase 1** | Project scaffold, DB connection, index creation, settings init | P0 |
| **Phase 2** | User registration (/start), banned user guard | P0 |
| **Phase 3** | Admin panel entry, Users submenu, User profile view | P0 |
| **Phase 4** | Give Access flow — invite link creation, subscription creation | P0 |
| **Phase 5** | Join detection (chat_member), subscription activation | P0 |
| **Phase 6** | Scheduler — reminders + expiry kicks + pending cleanup | P0 |
| **Phase 7** | Active users list, kicked/expired list, pagination | P1 |
| **Phase 8** | Subscription history, re-subscribe flow | P1 |
| **Phase 9** | Course management — add/edit/disable | P1 |
| **Phase 10** | Monthly revenue report | P1 |
| **Phase 11** | Broadcast message | P1 |
| **Phase 12** | Search users | P1 |
| **Phase 13** | Settings panel — edit invite expiry, warning hours | P1 |
| **Phase 14** | Ban/unban management | P1 |
| **Phase 15** | Edge case hardening, error handling audit, logging audit | P2 |

---

## 2. Database Layer

### 2.1 db.py — Connection & Init

```python
# database/db.py

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URI, DB_NAME

client: AsyncIOMotorClient = None
db = None

async def connect_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URI)
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
```

---

### 2.2 users.py — CRUD

```python
# database/users.py

from datetime import datetime, timezone
from database.db import db


async def get_user(user_id: int) -> dict | None:
    return await db.users.find_one({"_id": user_id})


async def create_user(user_id: int, name: str, username: str | None, photo_file_id: str | None):
    await db.users.insert_one({
        "_id": user_id,
        "name": name,
        "username": username,
        "photo_file_id": photo_file_id,
        "registered_at": datetime.now(timezone.utc),
        "is_banned": False
    })


async def is_banned(user_id: int) -> bool:
    user = await db.users.find_one({"_id": user_id}, {"is_banned": 1})
    if not user:
        return False
    return user.get("is_banned", False)


async def ban_user(user_id: int):
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_banned": True}}
    )


async def unban_user(user_id: int):
    await db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_banned": False}}
    )


async def get_all_users(skip: int = 0, limit: int = 50) -> list[dict]:
    cursor = db.users.find({}).skip(skip).limit(limit)
    return await cursor.to_list(None)


async def get_banned_users() -> list[dict]:
    cursor = db.users.find({"is_banned": True})
    return await cursor.to_list(None)


async def search_users(query: str) -> list[dict]:
    """Case-insensitive partial match on name or username."""
    import re
    pattern = re.compile(query, re.IGNORECASE)
    cursor = db.users.find({
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
    result = await db.subscriptions.aggregate(pipeline).to_list(None)
    if result:
        return {"total_subs": result[0]["total_subs"], "total_paid": result[0]["total_paid"]}
    return {"total_subs": 0, "total_paid": 0}
```

---

### 2.3 courses.py — CRUD

```python
# database/courses.py

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
```

---

### 2.4 subscriptions.py — CRUD

```python
# database/subscriptions.py

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from database.db import db


async def get_active_subscription(user_id: int, course_id: str) -> dict | None:
    return await db.subscriptions.find_one({
        "user_id": user_id,
        "course_id": ObjectId(course_id),
        "status": "active"
    })


async def get_pending_subscription(user_id: int, channel_id: int) -> dict | None:
    """Used in chat_member join handler — match by channel via course lookup."""
    course = await db.courses.find_one({"channel_id": channel_id})
    if not course:
        return None
    return await db.subscriptions.find_one({
        "user_id": user_id,
        "course_id": course["_id"],
        "status": "pending_join"
    })


async def check_is_renewal(user_id: int, course_id: str) -> bool:
    existing = await db.subscriptions.find_one({
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
    result = await db.subscriptions.insert_one({
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
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "status": "active",
            "joined_at": now,
            "expires_at": now + timedelta(days=duration_days)
        }}
    )


async def record_manual_leave(sub_id: str):
    now = datetime.now(timezone.utc)
    sub = await db.subscriptions.find_one({"_id": ObjectId(sub_id)})
    days_used = (now - sub["joined_at"]).days if sub.get("joined_at") else 0
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "left_at": now,
            "days_used": days_used
        }}
    )


async def expire_subscription(sub_id: str, reason: str = "subscription_expired"):
    now = datetime.now(timezone.utc)
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "status": "expired",
            "kicked_at": now,
            "kick_reason": reason
        }}
    )


async def kick_subscription(sub_id: str, reason: str = "manual_kick"):
    now = datetime.now(timezone.utc)
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {
            "status": "kicked",
            "kicked_at": now,
            "kick_reason": reason
        }}
    )


async def get_active_subscriptions_for_user(user_id: int) -> list[dict]:
    cursor = db.subscriptions.find({
        "user_id": user_id,
        "status": "active"
    })
    return await cursor.to_list(None)


async def get_subscription_history(user_id: int) -> list[dict]:
    cursor = db.subscriptions.find(
        {"user_id": user_id}
    ).sort("created_at", -1)
    return await cursor.to_list(None)


async def get_active_subscriptions_by_course(
    course_id: str,
    skip: int = 0,
    limit: int = 5
) -> list[dict]:
    cursor = db.subscriptions.find({
        "course_id": ObjectId(course_id),
        "status": "active"
    }).sort("expires_at", 1).skip(skip).limit(limit)
    return await cursor.to_list(None)


async def get_expired_subscriptions(skip: int = 0, limit: int = 5) -> list[dict]:
    cursor = db.subscriptions.find({
        "status": {"$in": ["expired", "kicked"]}
    }).sort("kicked_at", -1).skip(skip).limit(limit)
    return await cursor.to_list(None)


async def get_expiring_soon(hours: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=hours)
    window_end = window_start + timedelta(hours=1)
    field = f"reminder_{hours}h_sent"
    cursor = db.subscriptions.find({
        "status": "active",
        field: False,
        "expires_at": {"$gte": window_start, "$lt": window_end}
    })
    return await cursor.to_list(None)


async def mark_reminder_sent(sub_id: str, hours: int):
    field = f"reminder_{hours}h_sent"
    await db.subscriptions.update_one(
        {"_id": ObjectId(sub_id)},
        {"$set": {field: True}}
    )


async def get_due_for_kick() -> list[dict]:
    now = datetime.now(timezone.utc)
    cursor = db.subscriptions.find({
        "status": "active",
        "expires_at": {"$lte": now}
    })
    return await cursor.to_list(None)


async def get_stale_pending_joins(threshold: datetime) -> list[dict]:
    cursor = db.subscriptions.find({
        "status": "pending_join",
        "created_at": {"$lte": threshold}
    })
    return await cursor.to_list(None)


async def get_revenue_report(year: int, month: int) -> list[dict]:
    from calendar import monthrange
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    _, last_day = monthrange(year, month)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    pipeline = [
        {"$match": {
            "joined_at": {"$gte": start, "$lte": end},
            "status": {"$in": ["active", "expired", "kicked", "extended"]}
        }},
        {"$group": {
            "_id": {
                "course_id": "$course_id",
                "is_renewal": "$is_renewal"
            },
            "count": {"$sum": 1},
            "revenue": {"$sum": "$amount_paid"}
        }}
    ]
    return await db.subscriptions.aggregate(pipeline).to_list(None)


async def get_active_user_ids_for_course(course_id: str) -> list[int]:
    cursor = db.subscriptions.find(
        {"course_id": ObjectId(course_id), "status": "active"},
        {"user_id": 1}
    )
    subs = await cursor.to_list(None)
    return [s["user_id"] for s in subs]


async def get_all_active_user_ids() -> list[int]:
    cursor = db.subscriptions.find(
        {"status": "active"},
        {"user_id": 1}
    )
    subs = await cursor.to_list(None)
    return list({s["user_id"] for s in subs})  # deduplicated


async def count_active_subscriptions_by_course(course_id: str) -> int:
    return await db.subscriptions.count_documents({
        "course_id": ObjectId(course_id),
        "status": "active"
    })


async def count_expiring_today() -> int:
    now = datetime.now(timezone.utc)
    end_of_day = now.replace(hour=23, minute=59, second=59)
    return await db.subscriptions.count_documents({
        "status": "active",
        "expires_at": {"$gte": now, "$lte": end_of_day}
    })
```

---

## 3. Config & Entry Point

### 3.1 config.py

```python
# config.py

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
ADMIN_ID: int = int(os.getenv("ADMIN_ID"))
MONGO_URI: str = os.getenv("MONGO_URI")
DB_NAME: str = os.getenv("DB_NAME", "subscription_bot")

# Validation
assert BOT_TOKEN, "BOT_TOKEN missing in .env"
assert ADMIN_ID, "ADMIN_ID missing in .env"
assert MONGO_URI, "MONGO_URI missing in .env"
```

### 3.2 bot.py

```python
# bot.py

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
```

---

## 4. FSM States

```python
# states/fsm.py

from aiogram.fsm.state import State, StatesGroup


class AddCourseState(StatesGroup):
    waiting_name = State()
    waiting_photo = State()          # Optional — [⏭ Skip] available
    waiting_channel_id = State()
    waiting_price = State()
    waiting_confirm = State()


class EditCourseState(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_photo = State()


class BroadcastState(StatesGroup):
    selecting_target = State()
    waiting_message = State()
    waiting_confirm = State()


class SearchState(StatesGroup):
    waiting_query = State()


class SettingsState(StatesGroup):
    waiting_invite_expiry = State()
    waiting_warning_hours = State()
```

---

## 5. Keyboards

### 5.1 user_kb.py

```python
# keyboards/user_kb.py

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
```

---

### 5.2 admin_kb.py

```python
# keyboards/admin_kb.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_entry_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Open Admin Panel", callback_data="admin_panel")]
    ])


def admin_panel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Users",     callback_data="admin_users"),
            InlineKeyboardButton(text="📋 Courses",   callback_data="admin_courses")
        ],
        [
            InlineKeyboardButton(text="📊 Reports",   callback_data="admin_reports"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="🔍 Search",    callback_data="admin_search"),
            InlineKeyboardButton(text="⚙️ Settings",  callback_data="admin_settings")
        ]
    ])


def users_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟢 Active Users",      callback_data="admin_active_users")],
        [InlineKeyboardButton(text="❌ Expired / Kicked",  callback_data="admin_expired_users")],
        [InlineKeyboardButton(text="🚫 Banned Users",      callback_data="admin_banned_users")],
        [InlineKeyboardButton(text="🔙 Back",              callback_data="admin_panel")]
    ])


def user_quick_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 Give Access", callback_data=f"give_{user_id}"),
            InlineKeyboardButton(text="👁 Profile",     callback_data=f"profile_{user_id}")
        ],
        [
            InlineKeyboardButton(text="🚫 Ban",         callback_data=f"ban_{user_id}"),
            InlineKeyboardButton(text="🔙 Back",        callback_data="admin_active_users")
        ]
    ])


def profile_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 Give Access", callback_data=f"give_{user_id}"),
            InlineKeyboardButton(text="📋 History",     callback_data=f"history_{user_id}")
        ],
        [
            InlineKeyboardButton(text="❌ Kick All",    callback_data=f"kickall_{user_id}"),
            InlineKeyboardButton(text="🚫 Ban User",    callback_data=f"ban_{user_id}")
        ],
        [InlineKeyboardButton(text="🔙 Back",           callback_data="admin_users")]
    ])


def course_select_kb(courses: list[dict], user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for c in courses:
        rows.append([InlineKeyboardButton(
            text=f"📚 {c['name']} — ₹{c['price']}",
            callback_data=f"give_{user_id}:{str(c['_id'])}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"profile_{user_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_give_kb(user_id: int, course_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=f"confirm_give_{user_id}:{course_id}"),
            InlineKeyboardButton(text="❌ Cancel",  callback_data=f"give_{user_id}")
        ]
    ])


def confirm_kb(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    """Generic confirm/cancel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Confirm", callback_data=confirm_data),
            InlineKeyboardButton(text="❌ Cancel",  callback_data=cancel_data)
        ]
    ])


def pagination_kb(
    page: int,
    total_pages: int,
    prefix: str,
    back_data: str
) -> InlineKeyboardMarkup:
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="◀ Prev", callback_data=f"{prefix}_page_{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Next ▶", callback_data=f"{prefix}_page_{page + 1}"))

    return InlineKeyboardMarkup(inline_keyboard=[
        nav_row,
        [InlineKeyboardButton(text="🔙 Back", callback_data=back_data)]
    ])


def report_nav_kb(year: int, month: int) -> InlineKeyboardMarkup:
    import datetime
    current = datetime.date(year, month, 1)
    prev = (current.replace(day=1) - datetime.timedelta(days=1))
    nxt = (current.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"◀ {prev.strftime('%b %Y')}",
                callback_data=f"report_{prev.year}:{prev.month:02d}"
            ),
            InlineKeyboardButton(
                text=f"{nxt.strftime('%b %Y')} ▶",
                callback_data=f"report_{nxt.year}:{nxt.month:02d}"
            )
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_reports")]
    ])


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Edit Invite Expiry",  callback_data="settings_expiry")],
        [InlineKeyboardButton(text="✏️ Edit Warning Hours",  callback_data="settings_warnings")],
        [InlineKeyboardButton(text="🔙 Back",                callback_data="admin_panel")]
    ])


def broadcast_target_kb(courses: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📢 All Active Users", callback_data="broadcast_all")]
    ]
    for c in courses:
        rows.append([InlineKeyboardButton(
            text=f"📚 {c['name']} only",
            callback_data=f"broadcast_{str(c['_id'])}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_kb(callback_data: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Skip", callback_data=callback_data)]
    ])
```

---

## 6. Handlers

### 6.1 user.py

```python
# handlers/user.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from config import ADMIN_ID
from database import users as users_db, subscriptions as subs_db
from keyboards.user_kb import register_kb, home_kb, status_back_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    # Banned check
    if await users_db.is_banned(user_id):
        await message.answer(
            "🚫 <b>Access Restricted</b>\n\n"
            "You are not allowed to use this bot.\n"
            "Contact admin if you believe this is a mistake."
        )
        return

    user = await users_db.get_user(user_id)

    if not user:
        # New user
        await message.answer(
            "👋 <b>Welcome!</b>\n\n"
            "Register below to get started.",
            reply_markup=register_kb()
        )
        return

    # Returning user
    active_subs = await subs_db.get_active_subscriptions_for_user(user_id)

    if not active_subs:
        await message.answer(
            f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
            "📚 No active courses.\n\n"
            "Contact admin to get course access.",
            reply_markup=home_kb(has_history=True)
        )
        return

    # Build course summary — requires course name lookup
    from database import courses as courses_db
    lines = []
    for sub in active_subs:
        course = await courses_db.get_course(str(sub["course_id"]))
        if course:
            from datetime import datetime, timezone
            days_left = (sub["expires_at"] - datetime.now(timezone.utc)).days
            lines.append(f"• <b>{course['name']}</b> — {days_left} days left")

    course_text = "\n".join(lines)
    await message.answer(
        f"👋 <b>Welcome back, {user['name']}!</b>\n\n"
        f"📚 <b>Active Courses:</b>\n{course_text}\n\n"
        f"📋 Total Subscriptions: {len(active_subs)}",
        reply_markup=home_kb()
    )


@router.callback_query(F.data == "user_register")
async def cb_register(callback: CallbackQuery):
    user = callback.from_user
    user_id = user.id

    if await users_db.get_user(user_id):
        await callback.answer("Already registered!", show_alert=False)
        return

    # Get profile photo
    photos = await callback.bot.get_user_profile_photos(user_id, limit=1)
    photo_file_id = None
    if photos.total_count > 0:
        photo_file_id = photos.photos[0][0].file_id

    name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else None

    await users_db.create_user(user_id, name, username, photo_file_id)

    await callback.message.edit_text(
        f"✅ <b>Registration Complete!</b>\n\n"
        f"👤 {name}\n"
        f"🆔 {user_id}\n\n"
        f"Admin will contact you once your course access is approved."
    )

    # Notify admin
    await callback.bot.send_message(
        ADMIN_ID,
        f"🔔 <b>New Registration</b>\n\n"
        f"👤 {name}\n"
        f"🔗 {username or 'No username'}\n"
        f"🆔 {user_id}"
    )
    await callback.answer()
```

---

### 6.2 admin.py

```python
# handlers/admin.py — Skeleton with key handler signatures

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from states.fsm import AddCourseState, BroadcastState, SearchState, SettingsState

router = Router()

# ── Admin guard filter ──────────────────────────────────────────────────────

def admin_only(func):
    """Decorator to restrict handlers to ADMIN_ID."""
    async def wrapper(event, *args, **kwargs):
        user_id = event.from_user.id if hasattr(event, "from_user") else None
        if user_id != ADMIN_ID:
            if hasattr(event, "answer"):
                await event.answer("⛔ Unauthorized. This command is for admins only.")
            return
        return await func(event, *args, **kwargs)
    return wrapper

# ── /admin entry ────────────────────────────────────────────────────────────

@router.message(Command("admin"))
@admin_only
async def cmd_admin(message: Message):
    from database.subscriptions import count_expiring_today
    from database.subscriptions import count_active_subscriptions_by_course
    from keyboards.admin_kb import admin_entry_kb
    # Build summary stats and show entry button
    ...

# ── Admin panel main menu ───────────────────────────────────────────────────

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery): ...

# ── Users submenu ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_users")
async def cb_users_menu(callback: CallbackQuery): ...

@router.callback_query(F.data == "admin_active_users")
async def cb_active_users(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("admin_active_users_page_"))
async def cb_active_users_page(callback: CallbackQuery): ...

@router.callback_query(F.data == "admin_expired_users")
async def cb_expired_users(callback: CallbackQuery): ...

@router.callback_query(F.data == "admin_banned_users")
async def cb_banned_users(callback: CallbackQuery): ...

# ── Profile ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("profile_"))
async def cb_profile(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("history_"))
async def cb_history(callback: CallbackQuery): ...

# ── Give access ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("give_"))
async def cb_give_select_course(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("confirm_give_"))
async def cb_confirm_give(callback: CallbackQuery):
    """
    1. Check is_renewal
    2. Create invite link
    3. Create subscription (pending_join)
    4. Send link to user
    5. Confirm to admin
    """
    ...

# ── Join detection ──────────────────────────────────────────────────────────

from aiogram.types import ChatMemberUpdated
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, JOIN_TRANSITION, LEAVE_TRANSITION

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=JOIN_TRANSITION))
async def on_user_join(event: ChatMemberUpdated):
    """
    1. Find pending_join subscription for user+channel
    2. Activate subscription
    3. Send confirmation to user
    4. Notify admin
    """
    ...

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION))
async def on_user_leave(event: ChatMemberUpdated):
    """
    1. Find active subscription for user+channel
    2. Record left_at + days_used
    """
    ...

# ── Kick ────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("kick_"))
async def cb_kick_confirm(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("kickall_"))
async def cb_kickall_confirm(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("confirm_kickall_"))
async def cb_kickall_execute(callback: CallbackQuery): ...

# ── Ban / Unban ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("ban_"))
async def cb_ban_confirm(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("confirm_ban_"))
async def cb_ban_execute(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("unban_"))
async def cb_unban_execute(callback: CallbackQuery): ...

# ── Courses ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_courses")
async def cb_courses_menu(callback: CallbackQuery): ...

@router.callback_query(F.data == "admin_add_course")
async def cb_add_course_start(callback: CallbackQuery, state: FSMContext): ...

@router.message(AddCourseState.waiting_name)
async def add_course_name(message: Message, state: FSMContext): ...

@router.message(AddCourseState.waiting_photo)
async def add_course_photo(message: Message, state: FSMContext): ...

@router.callback_query(F.data == "skip", AddCourseState.waiting_photo)
async def add_course_photo_skip(callback: CallbackQuery, state: FSMContext): ...

@router.message(AddCourseState.waiting_channel_id)
async def add_course_channel(message: Message, state: FSMContext): ...

@router.message(AddCourseState.waiting_price)
async def add_course_price(message: Message, state: FSMContext): ...

@router.callback_query(F.data.startswith("course_toggle_"))
async def cb_course_toggle(callback: CallbackQuery): ...

# ── Reports ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_reports")
async def cb_reports_menu(callback: CallbackQuery): ...

@router.callback_query(F.data.startswith("report_"))
async def cb_report_view(callback: CallbackQuery): ...

# ── Broadcast ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext): ...

@router.callback_query(F.data.startswith("broadcast_"), BroadcastState.selecting_target)
async def cb_broadcast_target(callback: CallbackQuery, state: FSMContext): ...

@router.message(BroadcastState.waiting_message)
async def broadcast_message_input(message: Message, state: FSMContext): ...

@router.callback_query(F.data == "confirm_broadcast", BroadcastState.waiting_confirm)
async def broadcast_send(callback: CallbackQuery, state: FSMContext): ...

# ── Search ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_search")
async def cb_search_start(callback: CallbackQuery, state: FSMContext): ...

@router.message(SearchState.waiting_query)
async def search_execute(message: Message, state: FSMContext): ...

# ── Settings ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_settings")
async def cb_settings(callback: CallbackQuery): ...

@router.callback_query(F.data == "settings_expiry")
async def cb_settings_expiry(callback: CallbackQuery, state: FSMContext): ...

@router.message(SettingsState.waiting_invite_expiry)
async def settings_expiry_input(message: Message, state: FSMContext): ...

@router.callback_query(F.data == "settings_warnings")
async def cb_settings_warnings(callback: CallbackQuery, state: FSMContext): ...

@router.message(SettingsState.waiting_warning_hours)
async def settings_warnings_input(message: Message, state: FSMContext): ...
```

---

## 7. Scheduler Tasks

```python
# scheduler/tasks.py

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot

from database.db import db, get_settings
from database import subscriptions as subs_db, courses as courses_db
from config import ADMIN_ID

scheduler = AsyncIOScheduler()


async def check_reminders(bot: Bot):
    settings = await get_settings()
    warning_hours: list[int] = settings["warning_hours"]

    for hours in warning_hours:
        subs = await subs_db.get_expiring_soon(hours)
        for sub in subs:
            course = await courses_db.get_course(str(sub["course_id"]))
            if not course:
                continue

            expires_str = sub["expires_at"].strftime("%b %d, %Y")

            # Notify user
            try:
                if hours >= 24:
                    days = hours // 24
                    user_msg = (
                        f"⚠️ <b>Subscription Expiring Soon</b>\n\n"
                        f"📚 <b>{course['name']}</b> expires in {days} days.\n"
                        f"📅 Expiry: {expires_str}\n\n"
                        f"Contact admin to renew."
                    )
                else:
                    user_msg = (
                        f"🚨 <b>Final Warning!</b>\n\n"
                        f"📚 <b>{course['name']}</b> expires in {hours} hours.\n"
                        f"📅 Expiry: {expires_str}\n\n"
                        f"Contact admin immediately to renew."
                    )
                await bot.send_message(sub["user_id"], user_msg)
            except Exception as e:
                logging.warning(f"Reminder to user {sub['user_id']} failed: {e}")

            # Notify admin
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🔔 <b>Expiry Reminder Sent</b>\n\n"
                    f"👤 User ID: {sub['user_id']}\n"
                    f"📚 {course['name']}\n"
                    f"⏳ Expires in {hours}h\n"
                    f"📅 {expires_str}"
                )
            except Exception as e:
                logging.warning(f"Admin reminder notify failed: {e}")

            await subs_db.mark_reminder_sent(str(sub["_id"]), hours)


async def check_expiry_kicks(bot: Bot):
    subs = await subs_db.get_due_for_kick()
    for sub in subs:
        course = await courses_db.get_course(str(sub["course_id"]))
        if not course:
            continue

        # Kick user from channel
        try:
            await bot.ban_chat_member(course["channel_id"], sub["user_id"])
            await bot.unban_chat_member(course["channel_id"], sub["user_id"])
        except Exception as e:
            logging.info(f"Kick skipped for {sub['user_id']} (already left?): {e}")

        # Revoke invite link
        try:
            await bot.revoke_chat_invite_link(
                course["channel_id"],
                sub["invite_link"]
            )
        except Exception as e:
            logging.info(f"Link revoke skipped for sub {sub['_id']}: {e}")

        # Update DB
        await subs_db.expire_subscription(str(sub["_id"]))

        # Notify user
        try:
            await bot.send_message(
                sub["user_id"],
                f"❌ <b>Subscription Expired</b>\n\n"
                f"📚 <b>{course['name']}</b> access has ended.\n\n"
                f"Contact admin to renew and regain access."
            )
        except Exception as e:
            logging.warning(f"Expiry notify to user {sub['user_id']} failed: {e}")

        # Notify admin
        try:
            await bot.send_message(
                ADMIN_ID,
                f"📋 <b>Subscription Expired</b>\n\n"
                f"👤 User ID: {sub['user_id']}\n"
                f"📚 {course['name']}\n"
                f"📅 Expired: {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
            )
        except Exception as e:
            logging.warning(f"Admin expiry notify failed: {e}")


async def cleanup_pending_joins(bot: Bot):
    settings = await get_settings()
    expiry_hours = settings["invite_link_expiry_hours"]
    threshold = datetime.now(timezone.utc) - timedelta(hours=expiry_hours + 1)

    stale = await subs_db.get_stale_pending_joins(threshold)
    for sub in stale:
        await subs_db.expire_subscription(
            str(sub["_id"]),
            reason="invite_link_expired_unused"
        )
        logging.info(f"Cleaned up stale pending_join: sub {sub['_id']}")


def setup_scheduler(bot: Bot):
    scheduler.add_job(
        check_reminders, "interval",
        hours=1,
        args=[bot],
        id="check_reminders",
        replace_existing=True
    )
    scheduler.add_job(
        check_expiry_kicks, "interval",
        minutes=15,
        args=[bot],
        id="check_expiry_kicks",
        replace_existing=True
    )
    scheduler.add_job(
        cleanup_pending_joins, "interval",
        hours=1,
        args=[bot],
        id="cleanup_pending_joins",
        replace_existing=True
    )
    scheduler.start()
    logging.info("Scheduler started with 3 jobs")
```

---

## 8. Invite Utils

```python
# utils/invite.py

from datetime import datetime, timezone, timedelta
from aiogram import Bot


async def create_one_time_link(
    bot: Bot,
    channel_id: int,
    expiry_hours: int
) -> str:
    """Create member_limit=1 invite link. Returns the t.me URL."""
    link = await bot.create_chat_invite_link(
        chat_id=channel_id,
        member_limit=1,
        expire_date=datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    )
    return link.invite_link


async def revoke_link(bot: Bot, channel_id: int, invite_link: str):
    """Revoke an invite link. Silently ignores if already expired."""
    try:
        await bot.revoke_chat_invite_link(channel_id, invite_link)
    except Exception:
        pass
```

---

## 9. Implementation Order

```
Phase 1 — Scaffold
  ✅ Create folder structure
  ✅ requirements.txt
  ✅ .env + config.py
  ✅ database/db.py — connect, indexes, init_settings
  ✅ bot.py — startup/shutdown skeleton

Phase 2 — User Registration
  ✅ database/users.py
  ✅ handlers/user.py — /start, register callback
  ✅ keyboards/user_kb.py

Phase 3 — Admin Entry
  ✅ handlers/admin.py — /admin, admin_panel, users_menu
  ✅ keyboards/admin_kb.py — admin_entry_kb, admin_panel_kb, users_menu_kb

Phase 4 — Give Access
  ✅ database/courses.py
  ✅ database/subscriptions.py — create, check_is_renewal
  ✅ utils/invite.py
  ✅ admin.py — give flow, confirm_give handler

Phase 5 — Join Detection
  ✅ admin.py — on_user_join, on_user_leave chat_member handlers
  ✅ subscriptions.py — activate_subscription, record_manual_leave

Phase 6 — Scheduler
  ✅ scheduler/tasks.py — all 3 jobs
  ✅ bot.py — setup_scheduler in on_startup

Phase 7 — User Lists
  ✅ admin.py — active users, expired users, pagination
  ✅ admin_kb.py — pagination_kb

Phase 8 — Profile & History
  ✅ admin.py — profile view, history view, kick, kick-all

Phase 9 — Course Management
  ✅ states/fsm.py — AddCourseState, EditCourseState
  ✅ admin.py — add/edit/toggle course FSM handlers

Phase 10 — Revenue Report
  ✅ subscriptions.py — get_revenue_report aggregation
  ✅ admin.py — report view, month navigation

Phase 11 — Broadcast
  ✅ states/fsm.py — BroadcastState
  ✅ admin.py — broadcast flow

Phase 12 — Search
  ✅ states/fsm.py — SearchState
  ✅ admin.py — search handler

Phase 13 — Settings
  ✅ states/fsm.py — SettingsState
  ✅ admin.py — settings view + edit handlers

Phase 14 — Ban/Unban
  ✅ admin.py — ban confirm, execute, unban, banned list

Phase 15 — Hardening
  ✅ Global error handler
  ✅ All callback_query answer() calls verified
  ✅ FSM /cancel command added
  ✅ Stale callback guard (MessageNotModified)
  ✅ Logging audit
```

---

## 10. Testing Checklist

### Registration
- [ ] New user sees register button
- [ ] Registration saves all fields to DB
- [ ] Admin receives new user notification
- [ ] Returning user sees active courses
- [ ] Banned user is blocked immediately

### Give Access
- [ ] Course list shows only active courses
- [ ] Duplicate subscription warning shown
- [ ] Confirmation shows correct expiry date
- [ ] Invite link delivered to user
- [ ] Subscription created with `pending_join` status
- [ ] `is_renewal` correctly set (true/false)

### Join Detection
- [ ] `chat_member` update triggers handler
- [ ] Subscription activated with correct `expires_at`
- [ ] User receives welcome message
- [ ] Admin receives join alert
- [ ] Manual leave records `left_at` + `days_used`

### Scheduler
- [ ] 48h reminder sent once (flag prevents duplicate)
- [ ] 12h reminder sent once (flag prevents duplicate)
- [ ] Auto-kick fires within 15 min of expiry
- [ ] User removed from channel after kick
- [ ] Invite link revoked after kick
- [ ] Pending_join cleanup fires for expired links
- [ ] All scheduler jobs survive bot restart

### Edge Cases
- [ ] User already left channel — kick exception caught, expiry processed
- [ ] User blocked bot — reminder failure caught silently
- [ ] Bot removed from channel — error caught, admin notified
- [ ] Admin clicks old callback button — MessageNotModified handled
- [ ] Non-admin uses /admin — blocked

---

## 11. Deployment Checklist

### Pre-Deployment
- [ ] `.env` values set (BOT_TOKEN, ADMIN_ID, MONGO_URI, DB_NAME)
- [ ] Bot added as **admin** to all course channels
- [ ] Channel permissions: invite users, restrict members, manage chat ✅
- [ ] MongoDB Atlas cluster created, IP whitelist configured
- [ ] `requirements.txt` complete and pinned

### Deployment (Koyeb / Render)
- [ ] Environment variables set in platform dashboard
- [ ] `python bot.py` as start command
- [ ] Health check / keep-alive configured (if needed)
- [ ] Log streaming enabled

### Post-Deployment
- [ ] Send `/start` as user → registration works
- [ ] Send `/admin` → admin panel loads
- [ ] Give access to test user → link delivered
- [ ] Join channel → subscription activates
- [ ] Check MongoDB collections — documents created correctly
- [ ] Verify scheduler jobs appear in logs on startup
