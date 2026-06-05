# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- Multi-admin support
- Automated renewal flow
- Google Drive subscription export
- Web dashboard (admin UI)

## [0.1.0] — 2026-06-05

### Added
- Reorganized bot folder structure, moving all documentation to the dedicated `docs/` folder.
- Scaffolded Python project layout under the `bot/` directory with package subdirectories.
- Configured python virtual environment (`.venv`, `requirements.txt`, `.gitignore`, `.env.example`).
- Implemented **Phase 1**:
  - Configuration settings loader and variable validator in `bot/config.py`.
  - MongoDB connection, auto-indexing logic, and default settings initializer in `bot/database/db.py`.
  - Main bot application runner with FSM persistence (`MongoStorage`) and polling setup in `bot/bot.py`.
  - Basic handler and scheduler stubs for user, admin, and background tasks.
  - Verification test script (`verify_phase_1.py`) to validate configuration parsing and import paths.

---

## [0.2.0] — 2026-06-05

### Added
- Implemented **Phase 2 (Database CRUD & User Keyboards)**:
  - Database helper CRUD functions for `users.py`, `subscriptions.py`, and `courses.py`.
  - Registration FSM, Registration keyboards, and registration handlers in `user_kb.py` and `user.py`.
  - Global middleware `BannedUserMiddleware` to intercept and restrict blocked users.
  - Implemented detailed test verify script `verify_phase_2.py` with mock MongoDB collection layers.

---

## [0.3.0] — 2026-06-05

### Added
- Implemented **Phase 3 (Admin Panel Entry & Users Menu)**:
  - Added new database helper functions to calculate revenue reports, expiring subscriptions, active user IDs, and expiring soon notifications in `subscriptions.py`.
  - Added admin keyboard layouts (`admin_entry_kb`, `admin_panel_kb`, `users_menu_kb`, `user_quick_kb`, `profile_kb`, `pagination_kb`) in `admin_kb.py`.
  - Added admin callback handlers in `admin.py` to route `/admin` command, admin menus, active/expired/banned user lists, user profile inspector, and subscription history overview.
  - Developed and verified all updates using `verify_phase_3.py` script.

---

## [0.4.0] — 2026-06-05

### Added
- Implemented **Phase 4 (Give Access Flow)**:
  - Added invite link creation helper (`create_one_time_link`) and link revocation (`revoke_link`) in `bot/utils/invite.py`.
  - Expanded admin keyboards (`course_select_kb`, `confirm_give_kb`) in `bot/keyboards/admin_kb.py` to support target course selection and grant confirmations.
  - Implemented Give Access FSM callback routing (`cb_give_select_course`, `cb_confirm_give`) in `bot/handlers/admin.py` to prompt admins, display price and duration summaries, check for existing subscriptions, generate one-time invite links, create pending subscriptions in MongoDB, and notify the user via DM.
  - Fixed missing `timedelta` import in `bot/handlers/admin.py`.
  - Created a mock unit test suite `verify_phase_4.py` to validate all FSM steps and warning triggers.

---

## [0.5.0] — 2026-06-05

### Added
- Implemented **Phase 5 (Join Detection & Activation)**:
  - Added `get_active_subscription_by_channel` to `bot/database/subscriptions.py` to look up subscriptions for channel leaving events.
  - Registered `on_user_join` and `on_user_leave` handlers using `JOIN_TRANSITION` and `LEAVE_TRANSITION` on `chat_member` updates in `bot/handlers/admin.py`.
  - Implemented auto-activation on join (`pending_join` → `active`), expiration timestamp calculation, user welcome messages, admin join notifications, and automated logging of manual leave details (`left_at` and `days_used` metrics).
  - Created mock verification test script `verify_phase_5.py` to check all join/leave transition paths and database updates.

---

## [1.0.0] — Unreleased (In Development)

### Added
- User registration via `/start` — auto-collects name, username, profile photo
- Admin panel with inline keyboard navigation (`/admin`)
- Give Access flow — one-time invite link generation per user per course
- Auto join detection via `chat_member` Telegram events
- Subscription activation on channel join (`pending_join` → `active`)
- Manual leave detection — records `left_at` and `days_used`
- Configurable reminder system — 48h & 12h warnings before expiry
- Auto-kick on Day 30 via APScheduler (ban + immediate unban pattern)
- Invite link revocation on subscription expiry
- Pending join cleanup — marks unused invite links as `expired` after threshold
- Per-user subscription history with renewal tagging (`is_renewal` flag)
- Active users list with course filter and pagination (5 per page)
- Kicked / Expired users list with re-subscribe shortcut
- User profile view — stats, active courses, total paid
- Kick All — remove user from all active courses in one action
- Monthly revenue report — course-wise breakdown, new vs renewal count
- Broadcast message — target all active users or specific course subscribers
- Broadcast result summary — sent count + failed count
- Course management — add, edit, enable/disable courses
- Optional course photo support (`photo_file_id`)
- Custom price per course — price snapshot stored at subscription creation
- Search users — partial case-insensitive match on name or @username
- Settings panel — configure invite link expiry hours and warning hours from bot
- Ban / Unban management — blocks user from bot interaction
- FSM state persistence via `MongoStorage` (survives bot restarts)
- MongoDB indexes — compound index on `(status, expires_at)` for scheduler performance
- Global error handler — catches unhandled exceptions, notifies admin
- Broadcast flood protection — `asyncio.sleep(0.05)` between messages
- Admin-only guard on all admin handlers
- HTML parse mode set globally via `DefaultBotProperties`
- Structured logging to console and `bot.log` file

### Database
- `users` collection with `is_banned` flag
- `courses` collection with `is_active` toggle
- `subscriptions` collection with full lifecycle fields
- `settings` collection — auto-initialized on first startup with defaults
- `is_renewal` field on subscriptions for revenue report accuracy

### Scheduler Jobs
- `check_reminders` — runs every 60 minutes
- `check_expiry_kicks` — runs every 15 minutes
- `cleanup_pending_joins` — runs every 60 minutes

---

## Version Guide

```
MAJOR.MINOR.PATCH

MAJOR — Breaking changes (DB schema changes, handler rewrites)
MINOR — New features added (backward compatible)
PATCH — Bug fixes, minor improvements
```

---

*Maintained by the project owner.*
