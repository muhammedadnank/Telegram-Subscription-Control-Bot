# UI/UX Design Document
# Telegram Subscription Control Bot

**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2025

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Message Formatting Conventions](#2-message-formatting-conventions)
3. [User Flows](#3-user-flows)
   - [U1 — New User Registration](#u1--new-user-registration)
   - [U2 — Returning User /start](#u2--returning-user-start)
   - [U3 — Banned User](#u3--banned-user)
4. [Admin Flows](#4-admin-flows)
   - [A1 — Admin Entry (/admin)](#a1--admin-entry-admin)
   - [A2 — Give Access Flow](#a2--give-access-flow)
   - [A3 — User Profile View](#a3--user-profile-view)
   - [A4 — Active Users List](#a4--active-users-list)
   - [A5 — Kicked / Expired List](#a5--kicked--expired-list)
   - [A6 — Search Users](#a6--search-users)
   - [A7 — Subscription History](#a7--subscription-history)
   - [A8 — Monthly Revenue Report](#a8--monthly-revenue-report)
   - [A9 — Broadcast Message](#a9--broadcast-message)
   - [A10 — Course Management](#a10--course-management)
   - [A11 — Settings Panel](#a11--settings-panel)
   - [A12 — Ban Management](#a12--ban-management)
5. [Automated Message Templates](#5-automated-message-templates)
   - [M1 — Registration Confirmation (User)](#m1--registration-confirmation-user)
   - [M2 — New User Alert (Admin)](#m2--new-user-alert-admin)
   - [M3 — Access Granted (User)](#m3--access-granted-user)
   - [M4 — Join Confirmation (User)](#m4--join-confirmation-user)
   - [M5 — Join Alert (Admin)](#m5--join-alert-admin)
   - [M6 — 48h Reminder (User)](#m6--48h-reminder-user)
   - [M7 — 12h Reminder (User)](#m7--12h-reminder-user)
   - [M8 — Reminder Alert (Admin)](#m8--reminder-alert-admin)
   - [M9 — Expiry Notification (User)](#m9--expiry-notification-user)
   - [M10 — Expiry Alert (Admin)](#m10--expiry-alert-admin)
   - [M11 — Manual Leave Detection (Internal)](#m11--manual-leave-detection-internal)
6. [Keyboard Layout Reference](#6-keyboard-layout-reference)
7. [Navigation Map](#7-navigation-map)
8. [UX Rules & Guidelines](#8-ux-rules--guidelines)

---

## 1. Design Principles

| Principle | Application |
|---|---|
| **Mobile-first** | All keyboards max 2 columns; long lists paginated |
| **Confirm before destruct** | Kick, ban, kick-all always show confirmation step |
| **Inline everything** | No typed commands for management — pure inline keyboards |
| **Clear status at a glance** | Emojis used consistently as status indicators |
| **Minimal steps** | Give Access flow completes in 5 taps |
| **Feedback always** | Every action shows a result message — never silent |

### 1.1 Status Emoji Convention

| Emoji | Meaning |
|---|---|
| 🟢 | Active / Enabled |
| 🔴 | Disabled / Inactive |
| ⏳ | Pending / Waiting |
| ✅ | Success / Confirmed |
| ❌ | Failed / Kicked / Expired |
| ⚠️ | Warning / Caution |
| 🚨 | Critical / Urgent |
| 🚫 | Banned |
| 🔄 | Renewal / Refresh |
| 📋 | History / List |
| 💰 | Payment / Revenue |
| 📢 | Broadcast |
| 🔍 | Search |
| ⚙️ | Settings |
| 🎓 | Course Access |

---

## 2. Message Formatting Conventions

- **Bold** → Section headers, course names, user names
- `monospace` → IDs, dates, amounts
- Separator lines → `──────────────────` (18 dashes)
- Section dividers → blank line between sections
- Max message length → Keep under 4096 chars (Telegram limit)
- Parse mode → `HTML` throughout (not Markdown — avoids escaping issues)

### 2.1 Date Format

```
Jan 01, 2025          ← List views (short)
January 2025          ← Report headers
Jan 01, 2025 – Jan 31, 2025   ← History ranges
```

### 2.2 Currency Format

```
₹499        ← Amounts
₹10,184     ← Totals (comma-separated thousands)
```

---

## 3. User Flows

### U1 — New User Registration

**Step 1: /start received (user not in DB)**

```
👋 Welcome to [Bot Name]!

Access exclusive course content through
this bot. Register below to get started.

━━━━━━━━━━━━━━━━━━━━
```
**Keyboard:**
```
[ 📝 Register ]
```

---

**Step 2: User taps [📝 Register]**

Bot auto-collects from Telegram:
- `user.id` → `_id`
- `user.first_name + user.last_name` → `name`
- `user.username` → `username`
- `getProfilePhotos()[0]` → `photo_file_id`

Saves to DB, then replies:

```
✅ Registration complete!

👤 Rahul Kumar
🆔 123456789

Admin will contact you once your
course access is approved.
```
**Keyboard:**
```
[ 📊 My Status ]
```

---

**Step 3: Admin receives notification**

```
🔔 New Registration

👤 Rahul Kumar
🔗 @rahul123
🆔 123456789
📅 Jan 01, 2025

[ 👁 View Profile ]
```

---

### U2 — Returning User /start

**User with active subscriptions:**

```
👋 Welcome back, Rahul!

📚 Active Courses:
🐍 Python Basics — 15 days left
🌐 Django — 8 days left

📋 Total Subscriptions: 3
```
**Keyboard:**
```
[ 📊 My Status ]  [ 🔄 Refresh ]
```

---

**[📊 My Status] → Detailed view:**

```
📊 My Subscriptions

🐍 Python Basics
   Status: 🟢 Active
   Joined: Jan 01, 2025
   Expires: Jan 31, 2025
   ⏳ 15 days remaining
   💰 ₹499

🌐 Django
   Status: 🟢 Active
   Joined: Jan 23, 2025
   Expires: Feb 22, 2025
   ⏳ 8 days remaining
   💰 ₹699

──────────────────
💰 Total Paid: ₹2,993
```
**Keyboard:**
```
[ 🔙 Back ]
```

---

**User with no active subscriptions:**

```
👋 Welcome back, Rahul!

📚 No active courses.

Contact admin to get course access.
```
**Keyboard:**
```
[ 📋 My History ]
```

---

### U3 — Banned User

```
🚫 Access Restricted

You are not allowed to use this bot.
Contact admin if you believe this
is a mistake.
```
**Keyboard:** None

---

## 4. Admin Flows

### A1 — Admin Entry (/admin)

**Step 1: /admin command**

```
👋 Welcome, Admin!

🤖 Status: Running
👥 Active Users: 25
⚠️ Expiring Today: 2
📅 Jan 01, 2025
```
**Keyboard:**
```
[ 🛠 Open Admin Panel ]
```

---

**Step 2: Admin Panel Main Menu**

```
🛠 Admin Panel
```
**Keyboard:**
```
[ 👥 Users    ]  [ 📋 Courses  ]
[ 📊 Reports  ]  [ 📢 Broadcast]
[ 🔍 Search   ]  [ ⚙️ Settings ]
```

---

**Users Submenu:**

```
👥 User Management
```
**Keyboard:**
```
[ 🟢 Active Users  ]
[ ❌ Expired / Kicked ]
[ 🚫 Banned Users  ]
[ 🔙 Back          ]
```

---

### A2 — Give Access Flow

**Step 1: Admin selects user from list**

```
👤 Rahul Kumar
🔗 @rahul123 · 🆔 123456789
📅 Registered: Jan 01, 2025
📚 Active Courses: None
```
**Keyboard:**
```
[ 🎓 Give Access ]  [ 👁 Profile ]
[ 🚫 Ban         ]  [ 🔙 Back    ]
```

---

**Step 2: Admin taps [🎓 Give Access] — Course list**

```
🎓 Select Course for Rahul Kumar

Choose a course to grant access:
```
**Keyboard (one button per course):**
```
[ 🐍 Python Basics — ₹499 ]
[ 🌐 Django — ₹699        ]
[ 📊 Data Science — ₹899  ]
[ 🔙 Back                 ]
```

---

**Step 3a: User already has active sub for this course**

```
⚠️ Already Subscribed

Rahul Kumar is already active in
Python Basics.

Expires: Jan 31, 2025
⏳ 15 days remaining
```
**Keyboard:**
```
[ ✅ Give Anyway ]  [ ❌ Cancel ]
```

---

**Step 3b: Normal confirmation**

```
🎓 Confirm Access

👤 Rahul Kumar
📚 Python Basics
💰 ₹499
⏳ 30 days
📅 Expires: Feb 01, 2025
```
**Keyboard:**
```
[ ✅ Confirm ]  [ ❌ Cancel ]
```

---

**Step 4: After confirm — success**

```
✅ Access Granted

Link sent to Rahul Kumar
for Python Basics.
```

---

### A3 — User Profile View

```
👤 User Profile
━━━━━━━━━━━━━━━━━━━━
Name:     Rahul Kumar
Username: @rahul123
ID:       123456789
Joined:   Jan 01, 2025

📚 Active Courses: 1
  • 🐍 Python Basics (15 days left)

📋 Total Subscriptions: 3
💰 Total Paid: ₹1,697
📅 Last Active: Jan 16, 2025
━━━━━━━━━━━━━━━━━━━━
```
**Keyboard:**
```
[ 🎓 Give Access ]  [ 📋 History  ]
[ ❌ Kick All    ]  [ 🚫 Ban User ]
[ 🔙 Back        ]
```

---

**[❌ Kick All] → Confirmation:**

```
⚠️ Kick from All Courses?

Rahul Kumar will be removed from:
  • 🐍 Python Basics
  • 🌐 Django

This cannot be undone.
```
**Keyboard:**
```
[ ✅ Confirm Kick ]  [ ❌ Cancel ]
```

---

### A4 — Active Users List

**Filter bar + list:**

```
🟢 Active Subscribers

Filter by course:
```
**Keyboard (filter row):**
```
[ All ]  [ Python ]  [ Django ]  [ Data Sci ]
```

**List (after filter selected):**

```
🟢 Active — Python Basics (8 users)
──────────────────
👤 Rahul Kumar (@rahul123)
   ⏳ 15 days left · Expires Jan 31

👤 Arun Nair (@arun)
   ⏳ 3 days left · Expires Jan 19
```
**Per-user keyboard:**
```
[ 👁 Profile ]  [ ❌ Kick ]
```

**Bottom navigation:**
```
[ ◀ Prev ]  Page 1/3  [ Next ▶ ]
[ 🔙 Back ]
```

> **Pagination:** 5 users per page.  
> **Sort:** Expiry date ascending (soonest expiry first).

---

### A5 — Kicked / Expired List

```
❌ Expired / Kicked Users
──────────────────
👤 Rahul Kumar (@rahul123)
   📚 Python Basics
   📅 Kicked: Jan 31, 2025
   Reason: Subscription expired
```
**Per-entry keyboard:**
```
[ 👁 Profile ]  [ 🔄 Re-subscribe ]
```

**Bottom navigation:**
```
[ ◀ Prev ]  Page 1/2  [ Next ▶ ]
[ 🔙 Back ]
```

> `[🔄 Re-subscribe]` triggers Give Access flow (A2) with user pre-selected.

---

### A6 — Search Users

**Step 1: Trigger search**

```
🔍 Search Users

Type a name or @username to search:
```
*(FSM: SearchState.waiting_query)*

---

**Step 2: Results found**

```
🔍 Results for "rahul"

1. 👤 Rahul Kumar (@rahul123) · 🟢 Active
2. 👤 Rahul Nair (@rahulnair) · ❌ Expired
```
**Per-result keyboard:**
```
[ 👁 Rahul Kumar ]
[ 👁 Rahul Nair  ]
[ 🔙 Back        ]
```

---

**Step 2: No results**

```
🔍 No Results

No users found for "xyz".
Try a different name or @username.
```
**Keyboard:**
```
[ 🔍 Search Again ]  [ 🔙 Back ]
```

---

### A7 — Subscription History

```
📋 History — Rahul Kumar (@rahul123)
━━━━━━━━━━━━━━━━━━━━
1. 🐍 Python Basics
   Dec 01 – Dec 31, 2024
   💰 ₹499 · ✅ Completed

2. 🐍 Python Basics
   Jan 01 – Jan 31, 2025
   💰 ₹499 · 🟢 Active · 🔄 Renewal

3. 🌐 Django
   Dec 01 – Dec 31, 2024
   💰 ₹699 · ❌ Expired
━━━━━━━━━━━━━━━━━━━━
💰 Total Paid: ₹1,697
```
**Keyboard:**
```
[ 🔙 Back to Profile ]
```

> `🔄 Renewal` tag shown only when `is_renewal: true`.

---

### A8 — Monthly Revenue Report

**Step 1: Month selector**

```
📊 Revenue Report

Select month:
```
**Keyboard:**
```
[ ◀ ]  January 2025  [ ▶ ]
[ 📊 View Report      ]
[ 🔙 Back             ]
```

---

**Step 2: Report view**

```
📊 Revenue — January 2025
━━━━━━━━━━━━━━━━━━━━
🐍 Python Basics
   👥 Subscribers: 8
   💰 Revenue: ₹3,992

🌐 Django
   👥 Subscribers: 5
   💰 Revenue: ₹3,495

📊 Data Science
   👥 Subscribers: 3
   💰 Revenue: ₹2,697
━━━━━━━━━━━━━━━━━━━━
💰 Total Revenue: ₹10,184
👥 Total Subscribers: 16
🆕 New this month: 7
🔄 Renewals: 9
```
**Keyboard:**
```
[ ◀ Dec 2024 ]  [ Feb 2025 ▶ ]
[ 🔙 Back      ]
```

---

### A9 — Broadcast Message

**Step 1: Target selection**

```
📢 Broadcast Message

Select target audience:
```
**Keyboard:**
```
[ 📢 All Active Users      ]
[ 🐍 Python Basics only    ]
[ 🌐 Django only           ]
[ 📊 Data Science only     ]
[ 🔙 Back                  ]
```

---

**Step 2: Type message**

```
📢 Broadcast to: All Active Users

Type your message below:
```
*(FSM: BroadcastState.waiting_message)*

---

**Step 3: Preview + confirm**

```
📢 Preview

────────────────────
[Admin's message here]
────────────────────

Recipients: 16 users
```
**Keyboard:**
```
[ ✅ Send Now ]  [ ❌ Cancel ]
```

---

**Step 4: Result**

```
✅ Broadcast Complete

✅ Sent: 14
❌ Failed: 2 (blocked bot)
```

---

### A10 — Course Management

**Step 1: Course list**

```
📋 Course Management
```
**Keyboard:**
```
[ ➕ Add New Course        ]
[ 🟢 Python Basics — 12 👥 ]
[ 🟢 Django — 8 👥         ]
[ 🔴 Data Science — DISABLED]
[ 🔙 Back                  ]
```

---

**Step 2: Course selected**

```
📚 Python Basics
━━━━━━━━━━━━━━━━━━━━
💰 Price: ₹499
⏳ Duration: 30 days
👥 Active: 12 subscribers
Status: 🟢 Active
━━━━━━━━━━━━━━━━━━━━
```
**Keyboard:**
```
[ ✏️ Edit Name   ]  [ ✏️ Edit Price ]
[ 🖼 Edit Photo  ]  [ 🔴 Disable    ]
[ 🔙 Back        ]
```

> If course is disabled, `[🔴 Disable]` becomes `[🟢 Enable]`.

---

**Add Course FSM Steps:**

```
Step 1 — Name:
  "Enter course name:"

Step 2 — Photo:
  "Send course photo (optional):"
  Keyboard: [ ⏭ Skip ]

Step 3 — Channel ID:
  "Forward any message from the course
   channel, or enter channel ID manually:"

Step 4 — Price:
  "Enter course price in ₹:"

Step 5 — Confirm:
  "✅ Confirm New Course?

   Name:    Python Basics
   Channel: -1001234567890
   Price:   ₹499
   Duration: 30 days"

  Keyboard: [ ✅ Create ]  [ ❌ Cancel ]
```

---

### A11 — Settings Panel

**Settings view:**

```
⚙️ Bot Settings
━━━━━━━━━━━━━━━━━━━━
🔗 Invite Link Expiry:  2 hours
⚠️ Warning Times:       48h, 12h
━━━━━━━━━━━━━━━━━━━━
```
**Keyboard:**
```
[ ✏️ Edit Invite Expiry  ]
[ ✏️ Edit Warning Hours  ]
[ 🔙 Back                ]
```

---

**Edit Invite Expiry:**

```
✏️ Invite Link Expiry

Current: 2 hours
Enter new value in hours (e.g. 24):
```
*(FSM: SettingsState.waiting_invite_expiry)*

Success:
```
✅ Updated

Invite link expiry set to 24 hours.
Applies to all new links.
```

---

**Edit Warning Hours:**

```
✏️ Warning Hours

Current: 48, 12
Enter two values separated by comma
(e.g. 72, 24):
```
*(FSM: SettingsState.waiting_warning_hours)*

Success:
```
✅ Updated

Warning times set to 72h and 24h.
Takes effect from next check.
```

---

### A12 — Ban Management

**Banned users list:**

```
🚫 Banned Users (2)
──────────────────
👤 Rahul Kumar (@rahul123)
   Banned: Jan 01, 2025

👤 Arun Nair (@arun456)
   Banned: Jan 05, 2025
```
**Per-user keyboard:**
```
[ 👁 Profile ]  [ ✅ Unban ]
```

**Bottom:**
```
[ 🔙 Back ]
```

---

**Ban confirmation (from profile):**

```
⚠️ Ban User?

Rahul Kumar (@rahul123) will be
blocked from using this bot.

Note: This does NOT kick them from
active channels automatically.
```
**Keyboard:**
```
[ ✅ Confirm Ban ]  [ ❌ Cancel ]
```

**Ban success:**
```
🚫 Rahul Kumar has been banned.
```

**Unban success:**
```
✅ Rahul Kumar has been unbanned.
```

---

## 5. Automated Message Templates

### M1 — Registration Confirmation (User)

```
✅ Registration Complete!

👤 Rahul Kumar
🆔 123456789

Admin will contact you once your
course access is approved.
```

---

### M2 — New User Alert (Admin)

```
🔔 New Registration

👤 Rahul Kumar
🔗 @rahul123
🆔 123456789
📅 Jan 01, 2025
```
**Keyboard:**
```
[ 👁 View Profile ]
```

---

### M3 — Access Granted (User)

```
🎓 Course Access Approved!

📚 Python Basics

👇 Your one-time join link:
[https://t.me/+xxxxxxxxxx]

⚠️ Do not share this link.
⚠️ Link expires in 2 hours or
   once you join.
```

---

### M4 — Join Confirmation (User)

```
✅ Welcome to Python Basics!

📅 Subscription Active
🗓 Joined:   Jan 01, 2025
📅 Expires:  Jan 31, 2025
⏳ Duration: 30 days

You'll receive reminders before
your subscription expires.
```

---

### M5 — Join Alert (Admin)

```
✅ User Joined

👤 Rahul Kumar (@rahul123)
📚 Python Basics
📅 Expires: Jan 31, 2025
```

---

### M6 — 48h Reminder (User)

```
⚠️ Subscription Expiring Soon

📚 Python Basics expires in 2 days.
📅 Expiry: Jan 31, 2025

Contact admin to renew your access
before it expires.
```

---

### M7 — 12h Reminder (User)

```
🚨 Final Warning!

📚 Python Basics expires in 12 hours.
📅 Expiry: Jan 31, 2025

Contact admin immediately to renew.
```

---

### M8 — Reminder Alert (Admin)

```
🔔 Expiry Reminder Sent

👤 Rahul Kumar (@rahul123)
📚 Python Basics
⏳ Expires in [48h / 12h]
📅 Jan 31, 2025
```

---

### M9 — Expiry Notification (User)

```
❌ Subscription Expired

📚 Python Basics access has ended.
📅 Expired: Jan 31, 2025

Contact admin to renew and
regain access.
```

---

### M10 — Expiry Alert (Admin)

```
📋 Subscription Expired

👤 Rahul Kumar (@rahul123)
📚 Python Basics
📅 Expired: Jan 31, 2025
Reason: Subscription expired
```

---

### M11 — Manual Leave Detection (Internal)

> No message sent to user on manual leave.  
> Admin receives silent log entry only.  
> User receives normal expiry message (M9) on Day 30.

---

## 6. Keyboard Layout Reference

### Layout Conventions

| Context | Layout |
|---|---|
| Main menu | 2×3 grid (2 columns, 3 rows) |
| Course list | 1 column (full width per course) |
| User list items | 2 buttons per user: [👁 Profile] [❌ Kick] |
| Confirmation dialogs | 2 buttons: [✅ Confirm] [❌ Cancel] |
| Navigation | [🔙 Back] always last, full width |
| Pagination | [◀ Prev] [Page X/Y] [Next ▶] row |

### Back Navigation Rule

Every sub-view must have a `[🔙 Back]` button that returns to the immediate parent — not the main menu. Exception: profile opened from search → back returns to search results.

---

## 7. Navigation Map

```
/start
  ├── (new user) → Register → Confirmation
  └── (returning) → Home → [My Status]

/admin
  └── Admin Panel
        ├── 👥 Users
        │     ├── 🟢 Active Users
        │     │     └── User Card → [👁 Profile] [❌ Kick]
        │     ├── ❌ Expired / Kicked
        │     │     └── Entry Card → [👁 Profile] [🔄 Re-subscribe]
        │     └── 🚫 Banned Users
        │           └── Entry Card → [👁 Profile] [✅ Unban]
        │
        ├── 📋 Courses
        │     ├── ➕ Add Course (FSM)
        │     └── [Course] → Edit / Disable
        │
        ├── 📊 Reports
        │     └── Month Selector → Revenue Report
        │
        ├── 📢 Broadcast
        │     └── Target → Message (FSM) → Preview → Send
        │
        ├── 🔍 Search
        │     └── Query (FSM) → Results → Profile
        │
        └── ⚙️ Settings
              ├── Edit Invite Expiry (FSM)
              └── Edit Warning Hours (FSM)

Profile View (accessible from anywhere)
  ├── 🎓 Give Access → Course Select → Confirm → Done
  ├── 📋 History
  ├── ❌ Kick All → Confirm
  └── 🚫 Ban → Confirm
```

---

## 8. UX Rules & Guidelines

### 8.1 Destructive Action Guard

All destructive actions (kick, ban, kick-all) must:
1. Show a clear confirmation message
2. List what will be affected
3. Require explicit `[✅ Confirm]` tap
4. Never be reversible from the same flow (unban is a separate action)

### 8.2 FSM Cancel

Every FSM flow must support `/cancel` command or `[❌ Cancel]` button to exit the state cleanly without side effects.

### 8.3 Stale Callback Guard

If a user taps an inline button on an old message (e.g., after data changed), bot must:
1. Catch `MessageNotModified` gracefully
2. Show updated data with `answer_callback_query(show_alert=False)`

### 8.4 Empty State Messages

| List | Empty State |
|---|---|
| Active users | "No active subscribers at the moment." |
| Expired list | "No expired subscriptions found." |
| Banned users | "No banned users." |
| Search results | "No users found for '[query]'." |
| Course list | "No courses added yet. Tap ➕ Add." |

### 8.5 Pagination

- Page size: **5 items** per page
- Show current page and total: `Page 1 / 3`
- `[◀ Prev]` hidden on page 1
- `[Next ▶]` hidden on last page

### 8.6 Admin-Only Enforcement

Any non-admin user sending `/admin` or manipulating admin callback data receives:

```
⛔ Unauthorized

This command is for admins only.
```

No further processing.

### 8.7 Callback Answer

Every `callback_query` handler must call `answer_callback_query()` to dismiss the Telegram loading spinner — even if no message update is needed.
