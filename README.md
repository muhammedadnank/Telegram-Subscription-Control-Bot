# 🤖 Telegram Subscription Control Bot

A single-admin Telegram bot for managing paid course subscriptions. Handles invite link generation, auto-reminders, and expiry kicks — all from an inline keyboard panel.

---

## ✨ Features

- 📝 **Auto Registration** — Collects user info from Telegram automatically
- 🎓 **Give Access** — One-time invite links per user per course
- 🔔 **Smart Reminders** — Configurable 48h & 12h expiry warnings
- ⏱ **Auto Kick** — Removes users from channel on Day 30
- 📊 **Revenue Reports** — Monthly course-wise income breakdown
- 📢 **Broadcast** — Message all users or specific course subscribers
- 🔍 **Search** — Find users by name or @username
- 🚫 **Ban Management** — Block users from bot access
- ⚙️ **Settings Panel** — Configure invite expiry & warning hours from bot

---

## 🛠 Tech Stack

| Package | Version | Purpose |
|---|---|---|
| `aiogram` | 3.7.0 | Telegram Bot framework |
| `motor` | 3.4.0 | Async MongoDB driver |
| `apscheduler` | 3.10.4 | Scheduled jobs (reminders, kicks) |
| `python-dotenv` | 1.0.0 | Environment variables |
| `pymongo` | 4.6.0 | MongoDB (FSM storage) |

**Python:** 3.11+  
**Database:** MongoDB Atlas

---

## 📁 Project Structure

```
subscription_bot/
├── bot.py                  # Entry point
├── config.py               # Env vars & constants
├── database/
│   ├── db.py               # Connection, indexes, settings init
│   ├── users.py            # User CRUD
│   ├── courses.py          # Course CRUD
│   └── subscriptions.py    # Subscription CRUD
├── handlers/
│   ├── user.py             # /start, /status
│   └── admin.py            # /admin, all admin callbacks
├── keyboards/
│   ├── user_kb.py          # User inline keyboards
│   └── admin_kb.py         # Admin inline keyboards
├── scheduler/
│   └── tasks.py            # Reminder, kick & cleanup jobs
├── states/
│   └── fsm.py              # FSM state groups
├── utils/
│   └── invite.py           # Invite link helpers
├── .env
├── requirements.txt
├── README.md
└── CHANGELOG.md
```

---

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone https://github.com/yourname/subscription-bot.git
cd subscription-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the root directory:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_ID=123456789
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=subscription_bot
```

| Variable | Description |
|---|---|
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Your Telegram user ID |
| `MONGO_URI` | MongoDB Atlas connection string |
| `DB_NAME` | Database name (default: `subscription_bot`) |

### 4. Add bot to course channels

Add the bot as **admin** to every course channel with these permissions:

- ✅ Invite users via link
- ✅ Restrict members
- ✅ Manage chat

### 5. Run the bot

```bash
python bot.py
```

---

## 🗄 Database Collections

| Collection | Purpose |
|---|---|
| `users` | Registered users |
| `courses` | Course definitions |
| `subscriptions` | Subscription records |
| `settings` | Bot configuration |

---

## 🔄 Subscription Lifecycle

```
Admin gives access
    ↓
One-time invite link generated (expires in N hours)
    ↓
Link sent to user
    ↓
User joins channel → subscription activated
    ↓
48h before expiry → reminder sent
12h before expiry → final warning sent
    ↓
Day 30 → auto kick → subscription expired
```

---

## ⏰ Scheduler Jobs

| Job | Interval | Purpose |
|---|---|---|
| `check_reminders` | Every 60 min | Send 48h & 12h warnings |
| `check_expiry_kicks` | Every 15 min | Kick expired subscriptions |
| `cleanup_pending_joins` | Every 60 min | Mark unused invite links as expired |

---

## 📋 Subscription Statuses

| Status | Meaning |
|---|---|
| `pending_join` | Invite link sent, user not yet joined |
| `active` | User joined, subscription running |
| `expired` | Subscription ended (auto-kick or unused link) |
| `kicked` | Manually kicked by admin |
| `extended` | Reserved for future use |

---

## 🚀 Deployment

### Koyeb / Render

1. Push code to GitHub
2. Connect repo to Koyeb or Render
3. Set environment variables in platform dashboard
4. Set start command: `python bot.py`
5. Deploy

### Keep-Alive

For free-tier platforms that spin down on inactivity, add a simple HTTP keep-alive endpoint or use UptimeRobot to ping the service.

---

## 📄 Documentation

| Document | Description |
|---|---|
| [PRD](docs/PRD.md) | Product Requirements Document |
| [TRD](docs/TRD.md) | Technical Requirements Document |
| [UI/UX](docs/UIUX.md) | UI/UX Design Document |
| [Backend Plan](docs/BACKEND.md) | Schema & Implementation Plan |

---

## 📝 License

MIT License — free to use and modify.
