# 🤖 Telegram Subscription Control Bot

A single-admin Telegram bot for managing paid course subscriptions. Handles invite link generation, auto-reminders, and expiry kicks — all from a comprehensive, secure inline keyboard dashboard.

---

## ✨ Features

- 📝 **Auto Registration** — Collects user info from Telegram automatically
- 🎓 **Give Access** — Generates one-time invite links per user per course
- 🔔 **Smart Reminders** — Configurable 48h & 12h expiry warning notifications
- ⏱ **Auto Kick** — Removes users from the channel on Day 30 (via APScheduler)
- 📊 **Revenue Reports** — Monthly course-wise income breakdown (New vs Renewal)
- 📢 **Broadcast** — Target message all active users, specific course subscribers, or direct DM single users
- 🔍 **Search** — Search registered users by name or @username
- 🚫 **Ban Management** — Block/unblock users from interacting with the bot
- ⚙️ **Settings Panel** — Configure invite expiry & warning hours dynamically from the bot
- 🛡 **Global Exception Handler** — Real-time admin alerting and safe callback error handling

---

## 🛠 Tech Stack

| Package | Version | Purpose |
| :--- | :--- | :--- |
| **`aiogram`** | 3.7.0 | Telegram Bot framework |
| **`motor`** | 3.4.0 | Async MongoDB driver |
| **`apscheduler`** | 3.10.4 | Scheduled background jobs (reminders, kicks) |
| **`python-dotenv`** | 1.0.0 | Environment variables management |
| **`pymongo`** | 4.6.0 | MongoDB driver (required for FSM storage) |

- **Python:** 3.11+  
- **Database:** MongoDB Atlas (Persistent storage)

---

## 📁 Project Structure

```
Telegram-Subscription-Control-Bot/
├── bot/
│   ├── bot.py                  # Main entry point
│   ├── config.py               # Environment variables & constants
│   ├── database/
│   │   ├── db.py               # Database connections, indexes, settings init
│   │   ├── users.py            # User CRUD operations
│   │   ├── courses.py          # Course CRUD operations
│   │   └── subscriptions.py    # Subscription CRUD operations
│   ├── handlers/
│   │   ├── user.py             # User handlers (/start, /status, /cancel)
│   │   └── admin.py            # Admin handlers (/admin, all panel callbacks)
│   ├── keyboards/
│   │   ├── user_kb.py          # User inline keyboards
│   │   └── admin_kb.py         # Admin inline keyboards
│   ├── scheduler/
│   │   └── tasks.py            # Reminder, kick & cleanup background jobs
│   ├── states/
│   │   └── fsm.py              # Finite State Machine state definitions
│   └── utils/
│       └── invite.py           # Telegram invite link helpers
├── docs/
│   ├── AI_WORKFLOW.md          # Guidelines & workflow for AI development
│   ├── BACKEND.md              # 15-phase implementation plan & schema details
│   ├── PRD.md                  # Product Requirements Document
│   ├── TRD.md                  # Technical Requirements Document
│   └── UIUX.md                 # UI/UX Specifications & text templates
├── verify_phase/               # Regression verification scripts (Phases 1-9)
├── .env.example
├── requirements.txt
├── README.md
└── CHANGELOG.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/muhammedadnank/Telegram-Subscription-Control-Bot.git
cd Telegram-Subscription-Control-Bot
```

### 2. Install dependencies

Ensure you are using Python 3.11+ and create a virtual environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate
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
| :--- | :--- |
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Your Telegram user ID |
| `MONGO_URI` | MongoDB connection string |
| `DB_NAME` | Database name (default: `subscription_bot`) |

### 4. Add bot to course channels

Add the bot as an **administrator** to every course channel with these permissions:
- ✅ Invite users via link
- ✅ Restrict members (required for kick action)
- ✅ Manage chat (required for link revocation)

### 5. Run the bot locally

```bash
python bot/bot.py
```

---

## 🗄 Database Collections

| Collection | Purpose |
| :--- | :--- |
| **`users`** | Registered user accounts, including profile picture files & ban status |
| **`courses`** | Course definitions, custom pricing, duration, and Telegram channel links |
| **`subscriptions`** | Subscription records, lifecycle states (`pending_join`, `active`, `expired`, `kicked`) |
| **`settings`** | Global bot settings (default invite link expiry & warning hours) |

---

## 🔄 Subscription Lifecycle

```
Admin grants course access
    ↓
One-time invite link generated (expires in N hours)
    ↓
Invite link sent to user
    ↓
User joins channel → Subscription activated (expires in N days)
    ↓
48h before expiry → Warning reminder notification sent
12h before expiry → Final warning reminder notification sent
    ↓
Day 30 → Auto kick (ban + immediate unban) → Subscription marked expired
```

---

## ⏰ Scheduler Jobs

| Job | Interval | Purpose |
| :--- | :--- | :--- |
| `check_reminders` | Every 60 min | Sends warning DMs to users with expiring access |
| `check_expiry_kicks` | Every 15 min | Kicks expired users and revokes invite links |
| `cleanup_pending_joins` | Every 60 min | Marks unused invite links as expired after threshold |

---

## 📋 Subscription Statuses

| Status | Meaning |
| :--- | :--- |
| `pending_join` | Invite link generated and sent; user has not yet clicked it |
| `active` | User joined the channel; subscription is running |
| `expired` | Subscription ended naturally or invite link expired before joining |
| `kicked` | Manually kicked from the channel by the administrator |

---

## 🚀 Deployment

### Koyeb / Render

1. Push the repository to GitHub.
2. Link the repository to Koyeb or Render.
3. Configure the environment variables (`BOT_TOKEN`, `ADMIN_ID`, `MONGO_URI`, `DB_NAME`) in the platform's dashboard.
4. Set the start command to:
   ```bash
   python bot/bot.py
   ```
5. Deploy the application.

---

## 📄 Documentation

| Document | Description |
| :--- | :--- |
| **[PRD](docs/PRD.md)** | Product Requirements Document |
| **[TRD](docs/TRD.md)** | Technical Requirements Document |
| **[UI/UX Specifications](docs/UIUX.md)** | UI/UX specifications, layouts, and copy templates |
| **[Backend Implementation Plan](docs/BACKEND.md)** | Schema design & 15-phase backend roadmap |
| **[AI Workflow Guidelines](docs/AI_WORKFLOW.md)** | AI developer guidelines, boundaries, and safety checks |

---

## 📝 License

MIT License — free to use and modify.
