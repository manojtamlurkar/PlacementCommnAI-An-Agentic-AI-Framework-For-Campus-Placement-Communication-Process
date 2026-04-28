# Implementation Plan: Agentic AI Framework for Campus Recruitment

## Goal
Transform the CDC NITK Surathkal recruitment workflow into a fully autonomous, agent-based system where:
- The **Orchestrator** contacts companies, tracks replies, confirms drives, and assigns SPOCs
- The **SPOC** manages the entire drive via Telegram with bot assistance
- A **Company Agent Bot** handles student Q&A in dedicated Telegram groups
- A **Google Forms Agent** tracks registrations and suggests logistics

---

## Architecture at a Glance

```
Company HR ←→ Orchestrator (Email + Gmail) ←→ Admin Dashboard
                    ↓
              SPOC Assigned
                    ↓
         Telegram Group Created (Telethon)
                    ↓
         Company Bot (Polling Agent) listens
           ↙                      ↘
    Auto-answers              Escalates to SPOC
    (via LLM)              ↓
                    SPOC Dashboard
                    ↓         ↓
              Forward to HR   Post Answer → Telegram
```

---

## Phase 1: Foundation, Audit Log, and Orchestrator ✅ COMPLETE

### What was built:
- `ActivityLog` database model + `activity_logs` table
- `Orchestrator` class with `log_event()` and `check_stale_drives()`  
- State machine with correct `DRIVE_CONFIRMED → ASSIGN_SPOC` transition
- `PATCH /recruitment/confirm-drive/{id}` endpoint
- `GET /activity/{drive_id}` + `POST /activity/check-stale` endpoints
- Dashboard: "Confirm Drive" button, Activity Timeline panel, SPOC form conditional on `DRIVE_CONFIRMED`
- All routes (email, SPOC assignment, drive creation) log to `activity_logs`

---

## Phase 2: Telegram Group Automation ✅ COMPLETE

### What was built:
- `TelegramGroup` model + `telegram_groups` table
- `setup_telegram_session.py` — one-time Telethon OTP authentication (done, session saved)
- `telegram_group_service.py` — MTProto group creation, bot promotion, invite link export
- `backend/routes/telegram_group.py` — 7 endpoints for group management
- Dashboard drive card: "Create Telegram Group" button shown after SPOC assignment
- Dashboard: Telegram group status with invite link + "📢 Broadcast" button
- `POST /telegram/broadcast-invite` — posts invite to main student channel via bot

### Known issue fixed:
- Removed invalid `ExportInviteRequest` import from `telethon.tl.functions.channels` (uses `ExportChatInviteRequest` from `messages` instead)

---

## Phase 3: Company Agent + Student Question Pipeline ✅ COMPLETE

### What was built:
- `StudentQuestion` model + `student_questions` table
- `company_agent.py` — background thread polls bot `getUpdates` at server startup
  - Detects messages in registered company Telegram supergroups
  - Calls `answer_student_question()` LLM function with company JD + email history
  - Auto-replies in group if confident; otherwise escalates + notifies student
- `llm_service.py` — added `answer_student_question()` and `draft_questions_to_hr()`
- `backend/routes/spoc.py` — 3 endpoints: get questions, forward to HR, manual answer
- **SPOC Dashboard** (new sidebar tab):
  - Drive dropdown selector
  - Question queue with color-coded status badges + checkboxes
  - "Forward Selected to HR" button (LLM-drafts email + dispatches)
  - Action Panel: Click question → type answer → posts to Telegram group
- Bug fixed: Extra `}` in company form JS block that broke navigation

---

## Phase 4: Google Forms Auto-Creation + Registration Tracking 🔲 NOT STARTED

### Goal:
After logistics are confirmed, automatically create a Google Form for student registrations. Track the count via Google Sheets and trigger logistics recalculation when the count nears classroom capacity.

### What needs to be built:

#### Backend
- [ ] Enable **Google Forms API** and **Google Sheets API** in Google Cloud Console
- [ ] Add `google-api-python-client` to `requirements.txt`
- [ ] Add `google_form_id`, `registration_count` fields to `DriveLogistics` model + SQLite migration
- [ ] Write `backend/services/forms_service.py`:
  - `create_registration_form(company_name, drive_date)` → creates form, returns `form_id` + `form_link`
  - `get_registration_count(form_id)` → reads linked Google Sheet for response count
- [ ] Write `backend/routes/forms.py`:
  - `POST /forms/create/{logistics_id}` — creates form, saves `form_id` + `form_link`
  - `GET /forms/count/{logistics_id}` — returns current registration count
  - `POST /forms/check-capacity/{logistics_id}` — compares count to classroom capacity, logs alert if near limit
- [ ] Register `forms_router` in `main.py`
- [ ] Hook into orchestrator to auto-create form when `LOGISTICS_CONFIRMED`

#### Frontend
- [ ] Add "Generate Registration Form" button to logistics cards
- [ ] Show form link + live registration count (auto-refreshed)
- [ ] Show capacity warning badge (e.g. "🔴 87% Full") when nearing limit

---

## Phase 5: Orchestrator Autonomous Follow-up ⚠️ PARTIALLY DONE

### Current state:
- `check_stale_drives()` manually triggered via `POST /activity/check-stale`
- Dashboard has no automatic scheduler

### What remains:
- [ ] Add a background scheduler (e.g. APScheduler or threading timer) that runs `check_stale_drives()` every 24 hours automatically
- [ ] Extend stale check to also auto-generate and send follow-up emails (not just log the alert)
- [ ] Add a "suggested action" section in the dashboard that shows pending STALE_ALERT items and a one-click "Send Follow-up" button

---

## Phase 6: SPOC → HR Email Reply Sync (Auto-fetch HR answers) 🔲 NOT STARTED

### Goal:
When HR replies to the student questions email, automatically detect the reply in Gmail, extract the answers, update the `StudentQuestion` records, and broadcast the answers back in the Telegram group — without SPOC manual intervention.

### What needs to be built:
- [ ] Extend `gmail_reader.py` to detect reply emails with a special subject tag (e.g. `[NITK-DRIVE-QUESTIONS]`)
- [ ] Parse the reply to extract Q&A pairs (via LLM)
- [ ] Auto-update matched `StudentQuestion` records to `HR_ANSWERED`
- [ ] Call `post_to_company_group()` to broadcast HR answers in Telegram
- [ ] Log event in `activity_logs` as `ORCHESTRATOR / HR_REPLY_PROCESSED`

---

## Current Issues / Technical Debt

| Issue | Severity | Status |
|---|---|---|
| `company_agent.py` uses long-polling which conflicts if uvicorn runs multiple workers | Medium | Acceptable for now (single worker) |
| `telegram_group_service.py` uses `asyncio.get_event_loop()` which is deprecated in Python 3.10+ | Low | Python 3.8 in use, works fine |
| No authentication on any FastAPI endpoint | High | Local dev only — add API key middleware before any deployment |
| `recruitment.db` is SQLite — not suitable for concurrent writes under load | Medium | Fine for demo; switch to PostgreSQL for production |
| `requirements.txt` is incomplete (missing google-api, google-auth, telethon, etc.) | Low | Install was done via pip; needs update for fresh deploys |

---

## Deployment Checklist (Before Production)

- [ ] Move to PostgreSQL (update `db.py` connection string)
- [ ] Add API key authentication middleware to FastAPI
- [ ] Move `recruitment.db` to a persistent volume
- [ ] Serve `index.html` via a proper web server (Nginx or FastAPI `StaticFiles`)
- [ ] Run uvicorn with `--workers 1` to avoid bot polling conflicts
- [ ] Store all `.env` values in proper secrets management (e.g. AWS Secrets Manager)
- [ ] Update `requirements.txt` with all actual installed packages (`pip freeze > requirements.txt`)

---

## What is Working Right Now (End-to-End)

1. ✅ Add companies to Company Repo
2. ✅ Create a recruitment drive for a company
3. ✅ Generate + send initial contact email to HR (CDC template)
4. ✅ Read Gmail inbox, parse replies, log as `RECEIVED`
5. ✅ Generate context-aware follow-up email based on thread
6. ✅ Confirm drive (button) → `DRIVE_CONFIRMED` status
7. ✅ Assign SPOC → SPOC notified by email automatically
8. ✅ Create Telegram group for the company drive (Telethon)
9. ✅ Broadcast invite link to main student Telegram channel
10. ✅ Students join group, ask questions, bot responds or escalates
11. ✅ SPOC views escalated questions in SPOC Dashboard
12. ✅ SPOC forwards selected questions to HR (Groq-drafted email sent)
13. ✅ SPOC posts HR answer manually → bot replies in Telegram group
14. ✅ All actions logged in activity timeline per drive
15. ✅ Orchestrator stale drive scan (manual trigger)
16. ✅ Logistics and classroom management with auto-assignment
