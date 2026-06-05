# Design Specification: Phase 1 — Scaffold, DB Connection, Index Creation, Settings Init

## 1. Background & Goals
The objective of Phase 1 is to establish the core runtime environment, database connection layer, configuration handling, and boot/shutdown sequence for the Telegram Subscription Control Bot. This forms the foundation upon which subsequent interactive features (user registration, subscription control, scheduler kicks) will be built.

## 2. Technical Stack & Dependencies
- **Python**: 3.12+
- **Aiogram**: 3.7.0 (Telegram Bot framework)
- **Motor**: 3.4.0 (Async MongoDB driver)
- **APScheduler**: 3.10.4 (Job scheduler)
- **Python-dotenv**: 1.0.0 (Environment config)
- **Pymongo**: 4.6.0 (Underlying driver for Motor and BSON utilities)

## 3. Directory and File Layout
```
├── .env                  # Environment secrets (Local use, not committed)
├── .env.example          # Sample environment template (Committed)
├── .gitignore            # Git exclusions (.env, .venv, pycache)
├── requirements.txt      # Python dependencies
└── bot/
    ├── config.py         # Reads and validates environment variables
    ├── bot.py            # Main runner/poller
    ├── database/
    │   ├── db.py         # MongoDB connection & collection indices
    │   ├── users.py      # Stub user DB CRUD
    │   ├── courses.py    # Stub course DB CRUD
    │   └── subscriptions.py # Stub subscription DB CRUD
    ├── handlers/
    │   ├── user.py       # Stub user command handler
    │   └── admin.py      # Stub admin command handler
    └── scheduler/
        └── tasks.py      # Stub background tasks setup
```

## 4. Key Design Details

### 4.1 Configuration Management (`bot/config.py`)
Reads variables from `.env` using `python-dotenv`:
- `BOT_TOKEN` (required): Telegram bot token.
- `ADMIN_ID` (required): Integer ID of the main bot administrator.
- `MONGO_URI` (required): MongoDB connection URI.
- `DB_NAME` (optional): DB name, default is `"subscription_bot"`.

*Validation:* An assertion or `ValueError` is raised immediately on startup if any required field is missing.

### 4.2 Database Initialization (`bot/database/db.py`)
- Manages a global `AsyncIOMotorClient` instance.
- **Index Creation:**
  - `users`: index on `username`, index on `is_banned`.
  - `courses`: index on `is_active`, unique index on `channel_id`.
  - `subscriptions`: index on `user_id`, index on `course_id`, index on `status`, index on `expires_at`, index on `created_at`, compound index on `(user_id, course_id)`, compound index on `(status, expires_at)`.
- **Global Settings Init:**
  - Database collection: `settings`
  - Document ID: `global_settings`
  - Fields: `admin_id`, `warning_hours` (default `[48, 12]`), `invite_link_expiry_hours` (default `2`).

### 4.3 Bot Entry Point (`bot/bot.py`)
- Initializes `aiogram.Bot` with HTML parse mode.
- Initializes `aiogram.fsm.storage.mongo.MongoStorage` using the same `MONGO_URI` and `DB_NAME` to persist user finite state machine states.
- Registers startup and shutdown handlers:
  - Startup: Connects DB, creates indexes, initializes default global settings, starts scheduler.
  - Shutdown: Closes MongoDB client.
- Starts polling for updates.

## 5. Verification Plan
1. **Dependency Installation:** Verify package downloads inside virtual environment.
2. **Import Integrity:** Validate that running `python -m bot.config` or importing packages doesn't throw errors.
3. **Database connection and Index Creation Test:** Write a temporary verification script to verify that we can successfully connect to a test MongoDB database, create indexes, and write settings.
