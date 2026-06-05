# Folder Structure and File Reorganization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the repository documentation files and scaffold the Python project structure under `bot/`.

**Architecture:** Moving all markdown documentation files to `docs/` and renaming them to match project references. Creating the Python packages/modules structure under a unified `bot/` directory.

**Tech Stack:** Bash commands, Git, Python 3.11+.

---

### Task 1: Reorganize Documentation Files

**Files:**
- Modify: `AI_WORKFLOW.md` (move to `docs/AI_WORKFLOW.md`)
- Modify: `BACKEND_Subscription_Bot.md` (move to `docs/BACKEND.md`)
- Modify: `PRD_Subscription_Bot.md` (move to `docs/PRD.md`)
- Modify: `TRD_Subscription_Bot.md` (move to `docs/TRD.md`)
- Modify: `UIUX_Subscription_Bot.md` (move to `docs/UIUX.md`)

- [ ] **Step 1: Move and rename documentation files using git**

Run:
```bash
git mv PRD_Subscription_Bot.md docs/PRD.md
git mv TRD_Subscription_Bot.md docs/TRD.md
git mv UIUX_Subscription_Bot.md docs/UIUX.md
git mv BACKEND_Subscription_Bot.md docs/BACKEND.md
git mv AI_WORKFLOW.md docs/AI_WORKFLOW.md
```

Expected output: Files moved successfully in Git status.

- [ ] **Step 2: Verify git status**

Run: `git status`
Expected: 5 renamed files shown.

- [ ] **Step 3: Commit**

Run: `git commit -m "chore: move and rename documentation files to docs/"`
Expected: Clean commit.

---

### Task 2: Update README.md References

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update subscription_bot/ to bot/ in README.md**

Modify: `README.md` around lines 38-40:
```markdown
bot/
├── bot.py                  # Entry point
```

- [ ] **Step 2: Verify git diff**

Run: `git diff README.md`
Expected: Line modified showing `bot/` instead of `subscription_bot/`.

- [ ] **Step 3: Commit**

Run: `git add README.md && git commit -m "docs: update project structure directory to bot/ in README.md"`
Expected: Clean commit.

---

### Task 3: Scaffold Python Project Structure

**Files:**
- Create: `bot/__init__.py`
- Create: `bot/bot.py`
- Create: `bot/config.py`
- Create: `bot/database/__init__.py`
- Create: `bot/database/db.py`
- Create: `bot/database/users.py`
- Create: `bot/database/courses.py`
- Create: `bot/database/subscriptions.py`
- Create: `bot/handlers/__init__.py`
- Create: `bot/handlers/user.py`
- Create: `bot/handlers/admin.py`
- Create: `bot/keyboards/__init__.py`
- Create: `bot/keyboards/user_kb.py`
- Create: `bot/keyboards/admin_kb.py`
- Create: `bot/scheduler/__init__.py`
- Create: `bot/scheduler/tasks.py`
- Create: `bot/states/__init__.py`
- Create: `bot/states/fsm.py`
- Create: `bot/utils/__init__.py`
- Create: `bot/utils/invite.py`

- [ ] **Step 1: Create directories**

Run:
```bash
mkdir -p bot/database bot/handlers bot/keyboards bot/scheduler bot/states bot/utils
```

- [ ] **Step 2: Create init and module files with basic docstrings**

Create the following files with their corresponding docstrings:

- `bot/__init__.py`:
```python
"""
Telegram Subscription Control Bot package.
"""
```

- `bot/bot.py`:
```python
"""
Main entry point for the Telegram Subscription Control Bot.
"""
```

- `bot/config.py`:
```python
"""
Configuration settings and environment variables.
"""
```

- `bot/database/__init__.py`:
```python
"""
Database package for MongoDB CRUD operations.
"""
```

- `bot/database/db.py`:
```python
"""
Database connection and initialization.
"""
```

- `bot/database/users.py`:
```python
"""
User CRUD database operations.
"""
```

- `bot/database/courses.py`:
```python
"""
Course CRUD database operations.
"""
```

- `bot/database/subscriptions.py`:
```python
"""
Subscription CRUD database operations.
"""
```

- `bot/handlers/__init__.py`:
```python
"""
Telegram bot handlers package.
"""
```

- `bot/handlers/user.py`:
```python
"""
User commands and callbacks handlers.
"""
```

- `bot/handlers/admin.py`:
```python
"""
Admin commands and callbacks handlers.
"""
```

- `bot/keyboards/__init__.py`:
```python
"""
Inline and reply keyboards package.
"""
```

- `bot/keyboards/user_kb.py`:
```python
"""
User-facing keyboard definitions.
"""
```

- `bot/keyboards/admin_kb.py`:
```python
"""
Admin-facing keyboard definitions.
"""
```

- `bot/scheduler/__init__.py`:
```python
"""
Scheduled background tasks package.
"""
```

- `bot/scheduler/tasks.py`:
```python
"""
Scheduler jobs for reminders and kicks.
"""
```

- `bot/states/__init__.py`:
```python
"""
FSM States package.
"""
```

- `bot/states/fsm.py`:
```python
"""
Finite State Machine state group definitions.
```

- `bot/utils/__init__.py`:
```python
"""
Utility functions and helpers package.
"""
```

- `bot/utils/invite.py`:
```python
"""
Telegram invite link creation and validation helpers.
"""
```

- [ ] **Step 3: Verify structure via directory listing**

Run: `find bot -maxdepth 3 -not -path '*/.*'`
Expected output listing all files and directories created.

- [ ] **Step 4: Commit all scaffold files**

Run:
```bash
git add bot/
git commit -m "feat: scaffold python project directory structure under bot/"
```
Expected: Clean commit.
