# Product Requirements Document (PRD)
# Telegram Subscription Control Bot

**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2025  

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Personas](#3-user-personas)
4. [Scope](#4-scope)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [User Stories](#7-user-stories)
8. [Edge Cases & Constraints](#8-edge-cases--constraints)
9. [Out of Scope](#9-out-of-scope)
10. [Risks & Mitigations](#10-risks--mitigations)

---

## 1. Product Overview

### 1.1 Summary

A Telegram bot that allows a single admin to manually manage course subscriptions. Users register through the bot, admin grants channel access via one-time invite links, and the bot automates reminder notifications and subscription expiry enforcement.

### 1.2 Problem Statement

Course admins managing paid Telegram channel access face several manual, error-prone tasks:
- Manually generating and sending invite links after payment
- Remembering to kick users after 30 days
- Tracking who paid how much and when
- Sending expiry reminders manually

This bot eliminates all of the above through automation.

### 1.3 Solution

A single-admin Telegram bot that:
- Registers users and maintains a database
- Generates secure, one-time invite links per user per course
- Detects when a user joins and tracks their subscription
- Sends automated reminders before expiry
- Auto-kicks users on Day 30
- Provides admin with full control panel, reports, and user management

---

## 2. Goals & Success Metrics

### 2.1 Business Goals

| Goal | Metric |
|---|---|
| Eliminate manual link sharing | 100% of access grants via bot |
| Eliminate manual kicks | 0 users remaining in channel after expiry |
| Reduce admin workload | Admin spends < 2 min per new subscription |
| Improve revenue visibility | Monthly report generated in < 3 seconds |

### 2.2 Product Success Metrics

- Invite link delivery success rate: > 99%
- Reminder delivery rate: > 98%
- Auto-kick accuracy: 100% (zero missed kicks)
- Admin panel response time: < 1 second per action

---

## 3. User Personas

### 3.1 Admin (Primary User)

- Single person managing all courses
- Receives payments externally (UPI, cash, etc.)
- Needs quick access to user management from mobile
- Not necessarily technical — needs intuitive inline keyboard UI
- Wants to see revenue summaries and active user counts at a glance

### 3.2 Subscriber (End User)

- Pays admin outside the bot
- Expects quick access after payment
- Needs to receive join link without friction
- Expects reminders before their subscription expires
- May subscribe to multiple courses simultaneously

---

## 4. Scope

### 4.1 In Scope (v1.0)

| ID | Feature |
|---|---|
| F1 | User registration via /start |
| F2 | Admin panel with inline keyboards |
| F3 | One-time invite link generation |
| F4 | Auto join detection via chat_member events |
| F5 | Subscription reminder notifications (configurable) |
| F6 | Auto-kick on expiry |
| F7 | Per-user subscription history |
| F8 | Active users list (course-filtered) |
| F9 | Kicked/expired users list |
| F10 | User profile view |
| F11 | Monthly revenue report |
| F12 | Broadcast message to users |
| F13 | Course management (add/edit/disable) |
| F14 | Custom price per course |
| F15 | Search users by name/username |
| F16 | Settings panel (invite expiry, warning hours) |
| F17 | Ban/Unban management |

### 4.2 Version Constraints

- Single admin only (no multi-admin in v1.0)
- No in-bot payment processing (external UPI/cash only)
- No automated renewal (admin must manually re-grant access)

---

## 5. Functional Requirements

### 5.1 User Registration (F1)

**REQ-F1-01:** Bot must detect new vs returning users on `/start`.  
**REQ-F1-02:** New users must be registered automatically using Telegram profile data (name, username, user_id, profile photo).  
**REQ-F1-03:** Registered users must see their active courses and days remaining on `/start`.  
**REQ-F1-04:** Banned users must receive a block message and no further interaction must be possible.  
**REQ-F1-05:** Admin must receive a notification for every new user registration.

### 5.2 Admin Panel (F2)

**REQ-F2-01:** Admin panel must be accessible only to the configured admin ID.  
**REQ-F2-02:** All admin actions must use inline keyboards (no typed commands for management tasks).  
**REQ-F2-03:** Give Access flow must warn admin if user already has an active subscription for the same course.  
**REQ-F2-04:** Give Access confirmation must display course name, price, duration, and calculated expiry date before confirmation.

### 5.3 One-Time Invite Link (F3)

**REQ-F3-01:** Invite links must be created with `member_limit=1`.  
**REQ-F3-02:** Invite links must have an expiry time based on `settings.invite_link_expiry_hours`.  
**REQ-F3-03:** Invite link URL must be stored in the subscription document.  
**REQ-F3-04:** The invite link URL (not a separate ID field) must be used for revocation.

### 5.4 Join Detection (F4)

**REQ-F4-01:** Bot must listen to `chat_member` updates on all managed channels.  
**REQ-F4-02:** On join, subscription status must be updated from `pending_join` to `active` with `joined_at` and `expires_at` timestamps.  
**REQ-F4-03:** On manual leave, `left_at` and `days_used` must be recorded; expiry timer continues.  
**REQ-F4-04:** `pending_join` subscriptions older than `invite_link_expiry_hours + 1` must be cleaned up by a scheduler job and marked `expired`.

### 5.5 Reminders (F5)

**REQ-F5-01:** Scheduler must check active subscriptions every hour.  
**REQ-F5-02:** Reminders must be sent at intervals defined in `settings.warning_hours`.  
**REQ-F5-03:** Each reminder type (48h, 12h) must be sent exactly once per subscription (tracked via flags).  
**REQ-F5-04:** Admin must also receive a notification for each reminder sent.

### 5.6 Auto Kick (F6)

**REQ-F6-01:** Scheduler must check for expired subscriptions every 15 minutes.  
**REQ-F6-02:** Kick must be implemented as ban + immediate unban (removes user without permanent ban).  
**REQ-F6-03:** If user already left the channel, kick attempt exception must be caught and processing must continue.  
**REQ-F6-04:** Invite link must be revoked upon expiry.  
**REQ-F6-05:** Subscription status must be updated to `expired` with `kicked_at` timestamp.  
**REQ-F6-06:** User and admin must both receive expiry notifications.

### 5.7 Revenue Report (F11)

**REQ-F11-01:** Report must be filterable by month with prev/next navigation.  
**REQ-F11-02:** Report must show per-course subscriber count and revenue.  
**REQ-F11-03:** Report must distinguish new subscribers (`is_renewal: false`) from renewals (`is_renewal: true`).  
**REQ-F11-04:** `is_renewal` flag must be set at subscription creation time by checking for prior subscriptions for the same user+course.

### 5.8 Broadcast (F12)

**REQ-F12-01:** Broadcast must support targeting all active users or specific course subscribers.  
**REQ-F12-02:** Admin must preview message and recipient count before sending.  
**REQ-F12-03:** Messages must be sent with `asyncio.sleep(0.05)` between each to respect Telegram rate limits.  
**REQ-F12-04:** Result must show count of successful sends and failed sends (e.g., user blocked bot).

### 5.9 Settings (F16)

**REQ-F16-01:** Admin must be able to change invite link expiry hours from the bot.  
**REQ-F16-02:** Admin must be able to change warning hours (comma-separated input).  
**REQ-F16-03:** Settings changes must take effect immediately for new invite links and from the next scheduler check for reminders.

### 5.10 Ban Management (F17)

**REQ-F17-01:** Banning a user must immediately prevent them from interacting with the bot.  
**REQ-F17-02:** Banning must not automatically kick the user from active channels — admin must manually kick if needed.  
**REQ-F17-03:** Unbanning must restore full bot access.

---

## 6. Non-Functional Requirements

### 6.1 Performance

- Bot must respond to any inline keyboard action within 1 second
- MongoDB queries must use indexes on `user_id`, `course_id`, `status`, `expires_at`
- Broadcast to 100 users must complete within ~10 seconds

### 6.2 Reliability

- APScheduler must resume jobs after bot restart
- All scheduler jobs must be idempotent (safe to run multiple times)
- Bot must handle Telegram API errors gracefully (retry on 429, skip on 403)

### 6.3 Security

- Admin panel restricted to single `ADMIN_ID` from environment variable
- No sensitive data (phone numbers, payment details) stored in DB
- Invite links are one-time use and time-limited

### 6.4 Maintainability

- All configurable values (warning hours, invite expiry) must come from DB settings, not hardcoded
- File structure must follow modular separation (handlers, database, scheduler, utils)

---

## 7. User Stories

### Admin Stories

| ID | Story |
|---|---|
| US-A1 | As admin, I want to give a user access to a course in under 2 minutes so that I can process payments quickly. |
| US-A2 | As admin, I want to be notified when a user joins their course channel so that I know the link was used. |
| US-A3 | As admin, I want to see all active subscribers per course so that I can track engagement. |
| US-A4 | As admin, I want a monthly revenue report so that I can track income without a spreadsheet. |
| US-A5 | As admin, I want to broadcast a message to a specific course's subscribers so that I can communicate course updates. |
| US-A6 | As admin, I want to ban a problematic user so that they cannot interact with the bot. |
| US-A7 | As admin, I want to configure reminder timing without editing code so that I can adjust without redeployment. |

### Subscriber Stories

| ID | Story |
|---|---|
| US-S1 | As a subscriber, I want to receive my join link immediately after admin approves so that I can access my course quickly. |
| US-S2 | As a subscriber, I want to receive a reminder before my subscription expires so that I can renew in time. |
| US-S3 | As a subscriber, I want to see my active courses and days remaining so that I know my subscription status. |
| US-S4 | As a subscriber, I want registration to be automatic so that I don't need to fill out any forms. |

---

## 8. Edge Cases & Constraints

| Scenario | Expected Behavior |
|---|---|
| User joins using someone else's link (impossible) | `member_limit=1` prevents this automatically |
| Admin gives access to already-active user | Warning shown, admin can override |
| User leaves channel before expiry | `left_at` + `days_used` recorded; kick skipped on expiry; status → `expired` |
| User blocks the bot | Reminder/kick notification fails silently; `TelegramForbiddenError` caught and logged |
| Invite link expires before user joins | Subscription stays `pending_join`; scheduler cleanup marks it `expired` after threshold |
| Bot restarts mid-scheduler-cycle | APScheduler with MongoDB job store resumes pending jobs |
| Admin deletes a course with active subscribers | Guard confirmation required; existing subscriptions continue; no new access grants allowed |
| Two subscriptions for same user+course simultaneously | Warning shown to admin; `is_renewal: true` if prior record exists |

---

## 9. Out of Scope

- In-bot payment processing (Stripe, Razorpay, etc.)
- Multi-admin support
- Automated subscription renewal
- User-facing subscription purchase flow
- Analytics dashboard (web UI)
- Email notifications
- Referral or discount system

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Telegram rate limiting during broadcast | Messages fail silently | `asyncio.sleep(0.05)` throttle + failed count tracking |
| Bot loses admin rights in channel | Kick/invite link creation fails | Error handling + admin notification |
| MongoDB Atlas quota exceeded | Bot crashes | Monitor usage; indexes reduce query cost |
| APScheduler misses a kick job | User stays in channel after expiry | 15-min check interval; idempotent job logic |
| User ID collision with MongoDB `_id` | Data integrity issue | Use integer Telegram ID as `_id` consistently |
