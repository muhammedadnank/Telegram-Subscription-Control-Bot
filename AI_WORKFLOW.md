# AI-Assisted Development Workflow
# Telegram Subscription Control Bot

**Version:** 1.0  
**Purpose:** Guidelines for working with AI (Claude) during development

---

## Table of Contents

1. [Rule of One Feature at a Time](#1-rule-of-one-feature-at-a-time)
2. [Micro-Committing](#2-micro-committing)
3. [Human-in-the-Loop](#3-human-in-the-loop)

---

## 1. Rule of One Feature at a Time

### What it means

When prompting Claude for code, request **one feature or one phase at a time** — never multiple features in a single prompt.

### Why it matters

- Claude generates cleaner, more focused code when the scope is narrow
- Easier to review and test before moving on
- If something breaks, the source is obvious
- Avoids large blocks of untested code piling up

### How to apply it on this project

This project already has 15 phases defined in the Backend Implementation Plan. Follow them strictly — one phase per Claude session.

**❌ Wrong approach:**
```
"Give Access flow, join detection, and scheduler 
 implement ചെയ്ത് തരൂ"
```

**✅ Right approach:**
```
"Phase 4 — Give Access flow implement ചെയ്യൂ.
 confirm_give handler വരെ മാത്രം.
 invite link creation + subscription creation included."
```

### Phase prompt template

Use this structure when starting each phase:

```
Phase [N] — [Phase Name]

Context:
- Previous phase complete: [what was built]
- Current files: [list relevant files]

Task:
- [Specific feature to implement]
- [Specific handler / function names expected]

Constraints:
- Do not touch [other files]
- Follow existing patterns in [file]
```

### Scope boundaries per phase

| Phase | Scope | Files to touch |
|---|---|---|
| 1 | Scaffold, DB connection | `db.py`, `config.py`, `bot.py` |
| 2 | User registration | `users.py`, `handlers/user.py`, `user_kb.py` |
| 3 | Admin entry, users menu | `handlers/admin.py`, `admin_kb.py` |
| 4 | Give Access flow | `subscriptions.py`, `invite.py`, `admin.py` |
| 5 | Join detection | `admin.py` (chat_member handlers only) |
| 6 | Scheduler | `scheduler/tasks.py`, `bot.py` (startup only) |
| 7 | User lists, pagination | `admin.py`, `admin_kb.py` |
| 8 | Profile, history, kick | `admin.py` |
| 9 | Course management | `courses.py`, `admin.py`, `fsm.py` |
| 10 | Revenue report | `subscriptions.py`, `admin.py` |
| 11 | Broadcast | `admin.py`, `fsm.py` |
| 12 | Search | `admin.py`, `fsm.py` |
| 13 | Settings panel | `admin.py`, `db.py`, `fsm.py` |
| 14 | Ban/Unban | `admin.py`, `users.py` |
| 15 | Hardening | All files (review only) |

---

## 2. Micro-Committing

### What it means

Commit to Git **after every working phase** — not at the end of the project.

### Why it matters

- Every commit is a safe rollback point
- If a new feature breaks something, `git revert` restores the last working state in seconds
- Commit history becomes a readable log of what was built and when
- Easier to share specific phases for review

### Commit after every phase

```bash
# Phase 1
git add .
git commit -m "feat: project scaffold, db connection, index creation"

# Phase 2
git add .
git commit -m "feat: user registration and /start handler"

# Phase 3
git add .
git commit -m "feat: admin panel entry and users submenu"

# Phase 4
git add .
git commit -m "feat: give access flow with one-time invite link"

# Phase 5
git add .
git commit -m "feat: chat_member join and leave detection"

# Phase 6
git add .
git commit -m "feat: scheduler — reminders, kicks, pending cleanup"

# Phase 7
git add .
git commit -m "feat: active users list and expired list with pagination"

# Phase 8
git add .
git commit -m "feat: user profile view, subscription history, kick"

# Phase 9
git add .
git commit -m "feat: course management — add, edit, toggle"

# Phase 10
git add .
git commit -m "feat: monthly revenue report with renewal tracking"

# Phase 11
git add .
git commit -m "feat: broadcast message with target selection"

# Phase 12
git add .
git commit -m "feat: user search by name and username"

# Phase 13
git add .
git commit -m "feat: settings panel — invite expiry and warning hours"

# Phase 14
git add .
git commit -m "feat: ban and unban management"

# Phase 15
git add .
git commit -m "chore: error handling audit and logging cleanup"
```

### Commit message format

```
type: short description of what was done

Types:
  feat     — new feature added
  fix      — bug fixed
  chore    — cleanup, refactor, no behavior change
  docs     — documentation only
  test     — test added or updated
```

### Branch strategy (optional but recommended)

```bash
main          ← stable, deployed code only
dev           ← active development
feature/xxx   ← individual phase branches (optional)

# Merge dev → main only after full phase test passes
git checkout main
git merge dev
git push origin main
```

### What NOT to commit

Add these to `.gitignore`:

```gitignore
.env
*.log
bot.log
__pycache__/
*.pyc
.DS_Store
```

---

## 3. Human-in-the-Loop

### What it means

AI generates code — **you review, test, and approve** before it runs in production. Never auto-deploy AI-generated code without manual verification, especially for destructive or sensitive operations.

### Why it matters

- Claude can write logically correct code that fails in your specific environment
- Destructive actions (kick, ban, expiry) cannot be undone automatically
- Secrets and credentials must never leave your machine
- Edge cases in production behave differently than in theory

### Rules for this project

#### Rule 1 — Never share secrets with Claude

These values must **never** appear in a Claude prompt:

```
❌ BOT_TOKEN
❌ MONGO_URI (contains username + password)
❌ ADMIN_ID (your personal Telegram ID)
❌ Channel IDs of private channels
```

When showing code context to Claude, replace real values:

```python
# ✅ Safe to share
BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = 123456789          # placeholder
MONGO_URI = "mongodb+srv://..."  # placeholder
```

#### Rule 2 — Review before running scheduler jobs

Scheduler jobs affect real users — review these manually before first run:

| Job | Risk | What to verify |
|---|---|---|
| `check_expiry_kicks` | Kicks users from channel | Confirm `expires_at` logic is correct |
| `check_reminders` | Sends messages to users | Confirm reminder flags work (no duplicates) |
| `cleanup_pending_joins` | Marks subs as expired | Confirm threshold calculation is correct |

**Test sequence:**
1. Run bot locally with a test channel
2. Create a test subscription with `expires_at` set to 2 minutes from now
3. Watch scheduler logs — verify kick fires correctly
4. Check MongoDB — verify status updated to `expired`
5. Only then deploy to production

#### Rule 3 — Destructive actions need manual confirmation

Never implement destructive callbacks without a confirmation step:

```
✅ Always required:
  - Kick user → confirmation dialog
  - Kick All → confirmation dialog
  - Ban user → confirmation dialog
  - Disable course → confirmation dialog

❌ Never do:
  - Single-tap kick
  - Single-tap ban
  - Bulk operations without preview
```

This is already implemented in the UI/UX design — do not remove these confirmation steps even if Claude suggests simplifying the flow.

#### Rule 4 — Test edge cases manually

These scenarios cannot be unit tested automatically — test them by hand:

| Edge Case | How to test |
|---|---|
| User blocks bot | Block bot from test account, trigger reminder |
| Bot removed from channel | Remove bot, trigger give access flow |
| User leaves channel before expiry | Manually leave, check `left_at` in DB |
| Invite link expires unused | Wait for cleanup job, check DB status |
| Admin gives access to already-active user | Trigger duplicate access warning |
| Stale callback tap | Give access, wait, tap old confirm button |

#### Rule 5 — Human review checklist before each phase deploy

Before merging any phase to `main`:

```
[ ] Code reviewed line by line
[ ] No secrets hardcoded anywhere
[ ] No print() statements left (use logging)
[ ] Error handling present in all Telegram API calls
[ ] All callback_query handlers call answer()
[ ] Destructive actions have confirmation step
[ ] Tested locally with test account
[ ] MongoDB documents inspected after test
[ ] Committed with meaningful message
```

---

## Quick Reference

```
One Feature at a Time  →  One phase per Claude session
                          Use phase prompt template
                          Never mix phases in one prompt

Micro-Committing       →  git commit after every working phase
                          Use feat/fix/chore prefix
                          Never commit .env

Human-in-the-Loop      →  Never share BOT_TOKEN or MONGO_URI
                          Review all scheduler logic manually
                          Test edge cases by hand
                          Confirmation step on every destructive action
```
