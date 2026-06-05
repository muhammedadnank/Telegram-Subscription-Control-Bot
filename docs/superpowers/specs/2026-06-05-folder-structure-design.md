# Design Specification: Project Folder Structure & Reorganization

**Date:** 2026-06-05  
**Topic:** Reorganizing the Telegram Subscription Control Bot files to standard project layout and scaffolding development files.

---

## 1. Objectives

- Reorganize all existing markdown documents into a dedicated `docs/` folder to clean up the root directory.
- Update the documentation links inside `README.md` to point to their new locations.
- Scaffold the Python project directory structure according to the technical plan.

---

## 2. Document Reorganization Plan

Move and rename the following files from the root directory into the `docs/` directory:

| Original Path | New Path | Description |
|---|---|---|
| `PRD_Subscription_Bot.md` | `docs/PRD.md` | Product Requirements Document |
| `TRD_Subscription_Bot.md` | `docs/TRD.md` | Technical Requirements Document |
| `UIUX_Subscription_Bot.md` | `docs/UIUX.md` | UI/UX Design Document |
| `BACKEND_Subscription_Bot.md` | `docs/BACKEND.md` | Schema & Implementation Plan |
| `AI_WORKFLOW.md` | `docs/AI_WORKFLOW.md` | AI-Assisted Development Workflow Guidelines |

---

## 3. Project Scaffolding Structure

Create the following folder and file structure under `subscription_bot/` relative to the project root:

```
subscription_bot/
├── __init__.py
├── bot.py                  # Entry point
├── config.py               # Env vars & constants
├── database/
│   ├── __init__.py
│   ├── db.py               # Connection, indexes, settings init
│   ├── users.py            # User CRUD
│   ├── courses.py          # Course CRUD
│   └── subscriptions.py    # Subscription CRUD
├── handlers/
│   ├── __init__.py
│   ├── user.py             # /start, /status
│   └── admin.py            # /admin, all admin callbacks
├── keyboards/
│   ├── __init__.py
│   ├── user_kb.py          # User inline keyboards
│   └── admin_kb.py         # Admin inline keyboards
├── scheduler/
│   ├── __init__.py
│   └── tasks.py            # Reminder, kick & cleanup jobs
├── states/
│   ├── __init__.py
│   └── fsm.py              # FSM state groups
├── utils/
│   ├── __init__.py
│   └── invite.py           # Invite link helpers
```

- Every directory will contain an empty `__init__.py` to ensure it is treated as a Python package.
- All `.py` files will be created as empty files or containing a basic top-level docstring.

---

## 4. README Link Verification

Verify and update the documentation links in `README.md` to:
- `[PRD](docs/PRD.md)`
- `[TRD](docs/TRD.md)`
- `[UI/UX](docs/UIUX.md)`
- `[Backend Plan](docs/BACKEND.md)`
