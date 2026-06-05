# Technical Requirements Document (TRD)
# Telegram Subscription Control Bot

**Version:** 1.0  
**Status:** Draft  
**Stack:** Aiogram 3 + Motor (MongoDB) + APScheduler  
**Last Updated:** 2025

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Tech Stack & Dependencies](#2-tech-stack--dependencies)
3. [File Structure](#3-file-structure)
4. [Environment Variables](#4-environment-variables)
5. [Database Design](#5-database-design)
6. [API & Telegram Event Contracts](#6-api--telegram-event-contracts)
7. [FSM States](#7-fsm-states)
8. [Scheduler Design](#8-scheduler-design)
9. [Invite Link Lifecycle](#9-invite-link-lifecycle)
10. [Error Handling Strategy](#10-error-handling-strategy)
11. [Indexing Strategy](#11-indexing-strategy)
12. [Bot Startup & Shutdown](#12-bot-startup--shutdown)
13. [Logging](#13-logging)

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Telegram                             │
│   Users / Admin ──► Bot API ──► Webhook / Long Polling      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   bot.py    │  ← Entry point
                    │  (Aiogram)  │
                    └──────┬──────┘
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
   │  handlers/  │  │  scheduler/ │  │   utils/   │
   │  user.py    │  │  tasks.py   │  │  invite.py │
   │  admin.py   │  │ (APScheduler│  └─────┬──────┘
   └──────┬──────┘  └──────┬──────┘        │
          │                │               │
          └────────────────▼───────────────┘
                    ┌──────▼──────┐
                    │  database/  │
                    │  db.py      │
                    │  users.py   │
                    │  courses.py │
                    │  subscript. │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  MongoDB    │
                    │  (Motor)    │
                    └─────────────┘
```

### 1.1 Communication Flow

```
User Action (Telegram)
  → Aiogram dispatcher receives update
  → Router matches handler (command / callback / chat_member)
  → Handler calls database layer
  → Handler calls utils if needed (invite link)
  → Handler sends response back to Telegram

Scheduler (background)
  → APScheduler triggers job on interval
  → Job queries MongoDB directly
  → Job calls Telegram API via bot instance
  → Job updates DB after action
```

---

## 2. Tech Stack & Dependencies

### 2.1 Core Dependencies

| Package | Version | Purpose |
|---|---|---|
| `aiogram` | `^3.7.0` | Telegram Bot framework |
| `motor` | `^3.4.0` | Async MongoDB driver |
| `apscheduler` | `^3.10.4` | Cron / interval job scheduler |
| `python-dotenv` | `^1.0.0` | `.env` file loading |
| `pymongo` | `^4.6.0` | Sync MongoDB (APScheduler job store) |

### 2.2 Python Version

```
Python 3.11+
```

### 2.3 requirements.txt

```txt
aiogram==3.7.0
motor==3.4.0
apscheduler==3.10.4
python-dotenv==1.0.0
pymongo==4.6.0
```

---

## 3. File Structure

```
subscription_bot/
├── bot.py                        # Entry point — bot startup, dispatcher, scheduler init
├── config.py                     # Env vars, constants
├── database/
│   ├── db.py                     # Motor client, db reference
│   ├── users.py                  # User CRUD
│   ├── subscriptions.py          # Subscription CRUD
│   └── courses.py                # Course CRUD
├── handlers/
│   ├── user.py                   # /start, /status
│   └── admin.py                  # /admin, all admin callbacks
├── keyboards/
│   ├── user_kb.py                # User inline keyboards
│   └── admin_kb.py               # Admin inline keyboards
├── scheduler/
│   └── tasks.py                  # APScheduler job definitions
├── states/
│   └── fsm.py                    # All FSM state groups
├── utils/
│   └── invite.py                 # Invite link create / revoke helpers
├── .env
└── requirements.txt
```

---

## 4. Environment Variables

```env
# Telegram
BOT_TOKEN=your_bot_token_here
ADMIN_ID=123456789

# MongoDB
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=subscription_bot
```

### 4.1 config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
ADMIN_ID: int = int(os.getenv("ADMIN_ID"))
MONGO_URI: str = os.getenv("MONGO_URI")
DB_NAME: str = os.getenv("DB_NAME", "subscription_bot")
```

---

## 5. Database Design

### 5.1 Collection: `users`

```json
{
  "_id": 123456789,
  "name": "Rahul Kumar",
  "username": "@rahul123",
  "photo_file_id": "AgACAgIxxxxx",
  "registered_at": "2025-01-01T00:00:00Z",
  "is_banned": false
}
```

| Field | Type | Notes |
|---|---|---|
| `_id` | `int` | Telegram user ID — used as primary key |
| `name` | `str` | `first_name + last_name` from Telegram |
| `username` | `str` | `@username` — nullable if user has no username |
| `photo_file_id` | `str` | From `getProfilePhotos` — nullable |
| `registered_at` | `datetime` | UTC |
| `is_banned` | `bool` | Default: `false` |

---

### 5.2 Collection: `courses`

```json
{
  "_id": "ObjectId",
  "name": "Python Basics",
  "channel_id": -1001234567890,
  "price": 499,
  "duration_days": 30,
  "is_active": true,
  "photo_file_id": "AgACAgIxxxxx",
  "created_at": "2025-01-01T00:00:00Z"
}
```

| Field | Type | Notes |
|---|---|---|
| `_id` | `ObjectId` | Auto-generated |
| `name` | `str` | Display name |
| `channel_id` | `int` | Negative integer for channels |
| `price` | `int` | In INR (paise not needed) |
| `duration_days` | `int` | Default: 30 |
| `is_active` | `bool` | False = disabled, no new subscriptions |
| `photo_file_id` | `str` | Nullable — optional course thumbnail |
| `created_at` | `datetime` | UTC |

---

### 5.3 Collection: `subscriptions`

```json
{
  "_id": "ObjectId",
  "user_id": 123456789,
  "course_id": "ObjectId",
  "invite_link": "https://t.me/+xxxxxxxxxx",
  "status": "active",
  "is_renewal": false,
  "joined_at": "2025-01-01T00:00:00Z",
  "expires_at": "2025-01-31T00:00:00Z",
  "left_at": null,
  "days_used": null,
  "reminder_48h_sent": false,
  "reminder_12h_sent": false,
  "amount_paid": 499,
  "kicked_at": null,
  "kick_reason": null,
  "created_at": "2025-01-01T00:00:00Z"
}
```

| Field | Type | Notes |
|---|---|---|
| `_id` | `ObjectId` | Auto-generated |
| `user_id` | `int` | Ref → `users._id` |
| `course_id` | `ObjectId` | Ref → `courses._id` |
| `invite_link` | `str` | Full t.me URL — used for revocation too |
| `status` | `str` | Enum — see below |
| `is_renewal` | `bool` | True if user had prior subscription for same course |
| `joined_at` | `datetime` | Set on chat_member join event |
| `expires_at` | `datetime` | `joined_at + duration_days` |
| `left_at` | `datetime` | Nullable — set if user manually leaves |
| `days_used` | `int` | Nullable — `(left_at - joined_at).days` |
| `reminder_48h_sent` | `bool` | Prevents duplicate reminders |
| `reminder_12h_sent` | `bool` | Prevents duplicate reminders |
| `amount_paid` | `int` | Snapshot of price at time of creation |
| `kicked_at` | `datetime` | Nullable — set on expiry kick |
| `kick_reason` | `str` | Nullable — e.g., `"subscription_expired"` |
| `created_at` | `datetime` | UTC — when admin granted access |

**Status Enum:**

| Value | Meaning |
|---|---|
| `pending_join` | Link sent, user not yet joined |
| `active` | User joined, subscription running |
| `expired` | Subscription ended (auto or manual leave + expiry) |
| `kicked` | Manually kicked by admin before expiry |
| `extended` | Reserved for future renewal extension logic |

> **Note:** `invite_link_id` field removed from original design. Telegram's `revoke_chat_invite_link()` accepts the invite link URL directly — no separate ID needed.

---

### 5.4 Collection: `settings`

```json
{
  "_id": "global_settings",
  "admin_id": 123456789,
  "warning_hours": [48, 12],
  "invite_link_expiry_hours": 2
}
```

| Field | Type | Notes |
|---|---|---|
| `_id` | `str` | Fixed key: `"global_settings"` |
| `admin_id` | `int` | Telegram admin user ID |
| `warning_hours` | `list[int]` | Hours before expiry to send reminders |
| `invite_link_expiry_hours` | `int` | Hours before invite link auto-expires |

> **Note:** Settings document is created once on bot startup if not present (`upsert`).

---

## 6. API & Telegram Event Contracts

### 6.1 Commands

| Command | Handler | Access |
|---|---|---|
| `/start` | `user.py` | All users |
| `/status` | `user.py` | Registered users |
| `/admin` | `admin.py` | Admin only |

### 6.2 Callback Query Prefixes

All callback data follows `prefix:value` convention.

| Prefix | Example | Description |
|---|---|---|
| `admin_` | `admin_users` | Admin panel navigation |
| `user_` | `user_123456` | Select specific user |
| `course_` | `course_abc123` | Select specific course |
| `give_` | `give_123456:abc123` | Give access: user_id:course_id |
| `confirm_give_` | `confirm_give_123456:abc123` | Confirm give access |
| `kick_` | `kick_123456:abc123` | Kick user from course |
| `ban_` | `ban_123456` | Ban user |
| `unban_` | `unban_123456` | Unban user |
| `history_` | `history_123456` | View user history |
| `profile_` | `profile_123456` | View user profile |
| `report_` | `report_2025:01` | Revenue report: year:month |
| `broadcast_` | `broadcast_all` | Broadcast target selection |
| `settings_` | `settings_expiry` | Settings edit action |
| `course_toggle_` | `course_toggle_abc123` | Enable/disable course |

### 6.3 Telegram Updates Required

```python
# bot.py — start_polling must include:
await dp.start_polling(
    bot,
    allowed_updates=[
        "message",
        "callback_query",
        "chat_member",        # ← Required for join/leave detection
        "my_chat_member"
    ]
)
```

### 6.4 Bot Permissions Required in Channel

| Permission | Required For |
|---|---|
| `can_invite_users` | Creating invite links |
| `can_restrict_members` | Kicking users (ban + unban) |
| `can_manage_chat` | Revoking invite links |

---

## 7. FSM States

```python
# states/fsm.py

from aiogram.fsm.state import State, StatesGroup

class RegisterState(StatesGroup):
    waiting_photo = State()           # Unused — auto-collected

class AddCourseState(StatesGroup):
    waiting_name = State()
    waiting_photo = State()           # Optional step with Skip button
    waiting_channel_id = State()
    waiting_price = State()

class EditCourseState(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_photo = State()

class BroadcastState(StatesGroup):
    waiting_message = State()

class SearchState(StatesGroup):
    waiting_query = State()

class SettingsState(StatesGroup):
    waiting_invite_expiry = State()
    waiting_warning_hours = State()
```

### 7.1 FSM Storage

```python
from aiogram.fsm.storage.mongo import MongoStorage

storage = MongoStorage.from_url(MONGO_URI)
dp = Dispatcher(storage=storage)
```

> **Note:** Use `MongoStorage` so FSM state survives bot restarts.

---

## 8. Scheduler Design

### 8.1 APScheduler Setup

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
```

### 8.2 Jobs

| Job | Trigger | Interval | Description |
|---|---|---|---|
| `check_reminders` | interval | Every 60 min | Send 48h/12h reminders |
| `check_expiry_kicks` | interval | Every 15 min | Kick expired subscriptions |
| `cleanup_pending_joins` | interval | Every 60 min | Mark stale pending_join as expired |

### 8.3 check_reminders Logic

```python
async def check_reminders(bot: Bot):
    settings = await db.settings.find_one({"_id": "global_settings"})
    warning_hours = settings["warning_hours"]  # e.g., [48, 12]
    now = datetime.utcnow()

    for hours in warning_hours:
        field = f"reminder_{hours}h_sent"
        window_start = now + timedelta(hours=hours)
        window_end = window_start + timedelta(hours=1)

        subs = await db.subscriptions.find({
            "status": "active",
            field: False,
            "expires_at": {"$gte": window_start, "$lt": window_end}
        }).to_list(None)

        for sub in subs:
            # Send to user
            # Notify admin
            # Mark flag as True
            await db.subscriptions.update_one(
                {"_id": sub["_id"]},
                {"$set": {field: True}}
            )
```

### 8.4 check_expiry_kicks Logic

```python
async def check_expiry_kicks(bot: Bot):
    now = datetime.utcnow()

    subs = await db.subscriptions.find({
        "status": "active",
        "expires_at": {"$lte": now}
    }).to_list(None)

    for sub in subs:
        course = await db.courses.find_one({"_id": sub["course_id"]})

        # Step 1: Attempt kick
        try:
            await bot.ban_chat_member(course["channel_id"], sub["user_id"])
            await bot.unban_chat_member(course["channel_id"], sub["user_id"])
        except Exception:
            pass  # User already left — safe to continue

        # Step 2: Revoke invite link
        try:
            await bot.revoke_chat_invite_link(
                course["channel_id"],
                sub["invite_link"]
            )
        except Exception:
            pass  # Link may already be expired

        # Step 3: Update DB
        await db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {
                "status": "expired",
                "kicked_at": now,
                "kick_reason": "subscription_expired"
            }}
        )

        # Step 4: Notify user + admin
```

### 8.5 cleanup_pending_joins Logic

```python
async def cleanup_pending_joins(bot: Bot):
    settings = await db.settings.find_one({"_id": "global_settings"})
    expiry_hours = settings["invite_link_expiry_hours"]
    threshold = datetime.utcnow() - timedelta(hours=expiry_hours + 1)

    await db.subscriptions.update_many(
        {
            "status": "pending_join",
            "created_at": {"$lte": threshold}
        },
        {"$set": {
            "status": "expired",
            "kick_reason": "invite_link_expired_unused"
        }}
    )
```

---

## 9. Invite Link Lifecycle

```
Admin gives access
    │
    ▼
bot.create_chat_invite_link(
    chat_id=channel_id,
    member_limit=1,
    expire_date=now + invite_link_expiry_hours
)
    │
    ▼
Subscription created (status: pending_join)
invite_link stored in DB
    │
    ├─── User joins within expiry window
    │       ▼
    │    chat_member update received
    │    status → active
    │    joined_at, expires_at set
    │    Link auto-invalidated by Telegram (member_limit=1 reached)
    │
    ├─── User does NOT join within expiry window
    │       ▼
    │    cleanup_pending_joins job fires
    │    status → expired (kick_reason: invite_link_expired_unused)
    │
    └─── Subscription expires (Day 30)
            ▼
         bot.revoke_chat_invite_link(channel_id, invite_link)
         status → expired
```

---

## 10. Error Handling Strategy

### 10.1 Telegram API Errors

| Error | Cause | Handling |
|---|---|---|
| `TelegramForbiddenError` (403) | User blocked bot | Catch silently, log, continue |
| `TelegramBadRequest` (400) | Invalid chat/user | Catch, log, mark subscription for review |
| `TelegramRetryAfter` (429) | Rate limit hit | Catch, `await asyncio.sleep(e.retry_after)`, retry once |
| `ChatNotFound` | Bot removed from channel | Catch, notify admin |
| `UserNotParticipant` | User already left on kick | Catch silently, continue expiry processing |

### 10.2 Global Error Handler

```python
@dp.errors()
async def global_error_handler(update: Update, exception: Exception):
    logging.error(f"Update {update.update_id} caused error: {exception}")
    # Notify admin for critical errors
```

### 10.3 Broadcast Error Handling

```python
success = 0
failed = 0

for user_id in recipients:
    try:
        await bot.send_message(user_id, text)
        success += 1
    except TelegramForbiddenError:
        failed += 1
    await asyncio.sleep(0.05)

await bot.send_message(ADMIN_ID, f"✅ {success} sent, ❌ {failed} failed")
```

---

## 11. Indexing Strategy

```python
# database/db.py — run on startup

async def create_indexes():
    # users
    await db.users.create_index("username")
    await db.users.create_index("is_banned")

    # subscriptions
    await db.subscriptions.create_index("user_id")
    await db.subscriptions.create_index("course_id")
    await db.subscriptions.create_index("status")
    await db.subscriptions.create_index("expires_at")
    await db.subscriptions.create_index("created_at")
    await db.subscriptions.create_index([("user_id", 1), ("course_id", 1)])
    await db.subscriptions.create_index([("status", 1), ("expires_at", 1)])

    # courses
    await db.courses.create_index("is_active")
    await db.courses.create_index("channel_id")
```

> **Compound index** on `(status, expires_at)` is critical for scheduler query performance.

---

## 12. Bot Startup & Shutdown

```python
# bot.py

async def on_startup(bot: Bot):
    await create_indexes()
    await init_settings()       # Create default settings doc if not exists
    scheduler.add_job(check_reminders, "interval", hours=1, args=[bot])
    scheduler.add_job(check_expiry_kicks, "interval", minutes=15, args=[bot])
    scheduler.add_job(cleanup_pending_joins, "interval", hours=1, args=[bot])
    scheduler.start()
    logging.info("Bot started")

async def on_shutdown(bot: Bot):
    scheduler.shutdown()
    logging.info("Bot stopped")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"]
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### 12.1 init_settings

```python
async def init_settings():
    existing = await db.settings.find_one({"_id": "global_settings"})
    if not existing:
        await db.settings.insert_one({
            "_id": "global_settings",
            "admin_id": ADMIN_ID,
            "warning_hours": [48, 12],
            "invite_link_expiry_hours": 2
        })
```

---

## 13. Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),               # Console
        logging.FileHandler("bot.log")         # File
    ]
)
```

### 13.1 Key Log Points

| Event | Level |
|---|---|
| Bot started / stopped | INFO |
| New user registered | INFO |
| Invite link created | INFO |
| User joined channel | INFO |
| Reminder sent | INFO |
| User kicked (expiry) | INFO |
| Telegram API error (403, 429) | WARNING |
| Scheduler job failure | ERROR |
| Unhandled exception | ERROR |
