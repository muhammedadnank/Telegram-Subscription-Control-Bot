# Design Specification: Phase 2 — User Registration and Banned User Guard

## 1. Background & Goals
Phase 2 implements the initial user onboarding flow:
- Block banned users from interacting with the bot.
- Guide new users to register with a single click (storing their user ID, name, username, and profile photo).
- Show returning users their active courses or prompt them to contact the admin if they have none.

## 2. Component Design

### 2.1 Banned User Middleware (`bot/middlewares/banned.py`)
To prevent banned users from interacting with the bot, we'll implement an aiogram outer middleware that checks `is_banned(user_id)` on all incoming messages/callbacks.
- If the user is banned:
  - If it's a message: Respond with a restriction alert.
  - If it's a callback query: Answer with an alert popup.
  - Cancel event propagation.

### 2.2 Keyboards (`bot/keyboards/user_kb.py`)
- `register_kb()`: Inline button "📝 Register" -> callback `user_register`.
- `home_kb(has_history=False)`:
  - Row 1: "📊 My Status" (`user_status`), "🔄 Refresh" (`user_refresh`).
  - Row 2 (if `has_history`): "📋 My History" (`user_history`).
- `status_back_kb()`: Inline button "🔙 Back" -> callback `user_home`.

### 2.3 Database Layers
- **`bot/database/users.py`**: Implements basic CRUD operations:
  - `get_user(user_id)`
  - `create_user(user_id, name, username, photo_file_id)`
  - `is_banned(user_id)`
  - `ban_user(user_id)`
  - `unban_user(user_id)`
  - `get_all_users(skip, limit)`
  - `get_banned_users()`
  - `search_users(query)`
- **`bot/database/subscriptions.py`**: Implements:
  - `get_active_subscriptions_for_user(user_id)` -> fetches active subscriptions.

### 2.4 User Handlers (`bot/handlers/user.py`)
- `/start` Command:
  - Check if the user is registered.
  - If not registered, prompt with "👋 Welcome! Register below to get started." and `register_kb()`.
  - If registered, query active subscriptions. Show active courses with remaining days or show "No active courses" and `home_kb()`.
- `user_register` Callback:
  - Fetch user's profile photo via `bot.get_user_profile_photos(limit=1)`.
  - Create the user in MongoDB.
  - Send "Registration Complete!" message.
  - Notify the main admin (`ADMIN_ID`).

## 3. Verification Plan
- Create a test script that sets up dummy data in a test MongoDB, runs imports, and uses mock objects to simulate:
  - `/start` command for a banned user (should be blocked by middleware).
  - `/start` command for a new user (should show register keyboard).
  - `user_register` callback query (should create user in DB and notify admin).
  - `/start` command for a registered user (should display active courses).
