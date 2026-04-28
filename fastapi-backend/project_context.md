# Project Context: Agentic AI Framework for Campus Recruitment Process

> **Purpose**: This document is the single source of truth for understanding the codebase across sessions. Read this before making any changes.

---

## 1. Overview

This is a **FastAPI-based autonomous recruitment orchestration system** built for **CDC (Career Development Centre) NITK Surathkal**. The system replaces manual, error-prone placement coordination with an AI-driven multi-agent pipeline.

### What it does:
1. Tracks companies and their recruitment drives
2. Orchestrates email communication with HR (outgoing invitations + incoming reply parsing via Gmail API)
3. On HR confirmation, assigns a SPOC (Single Point of Contact) from CDC
4. Automatically creates a dedicated **Telegram group** for each company drive using the Telethon MTProto API
5. Deploys a **Company Agent Bot** that listens to student questions in the Telegram group, auto-answers using LLM (Groq) + email context, and escalates unknowns to the SPOC
6. SPOC can view all escalated questions via a **SPOC Dashboard** and forward batched questions to HR via a Groq-drafted email
7. When HR responds, the SPOC posts the answer back to Telegram through the dashboard
8. All actions are logged in a **centralized audit trail** (ActivityLog) observable from the dashboard

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | FastAPI (Python 3.8) |
| ORM | SQLAlchemy |
| Database | SQLite (`recruitment.db`) |
| LLM | Groq API (llama-3.1-8b-instant) |
| Email (Send) | SMTP via Gmail App Password |
| Email (Read) | Gmail REST API (OAuth2 via google-auth) |
| Telegram (Bot) | Telegram Bot API (HTTP polling) |
| Telegram (Group Creation) | Telethon (MTProto user session) |
| Frontend | Vanilla HTML + TailwindCSS CDN (single `index.html`) |
| Deployment | Local `uvicorn main:app --reload` |

---

## 3. Project Directory Structure

```
Code/
└── fastapi-backend/
    ├── main.py                          # FastAPI entry point, lifespan startup (agent thread)
    ├── requirements.txt
    ├── setup_telegram_session.py        # One-time Telethon OTP auth script
    ├── recruitment.db                   # SQLite database
    ├── telegram_session.session         # Telethon session file (NOT committed)
    ├── token.json                       # Gmail OAuth token (NOT committed)
    ├── .env                             # All secrets (NOT committed)
    ├── frontend/
    │   └── index.html                   # Entire frontend (SPA, vanilla JS)
    └── backend/
        ├── database/
        │   ├── db.py                    # SQLAlchemy engine + get_db dependency
        │   └── models.py                # All 8 ORM models
        ├── routes/
        │   ├── recruitment.py           # /recruitment/* - Drive lifecycle
        │   ├── email.py                 # /emails/* - Send + read emails
        │   ├── email_actions.py         # /email-actions/* - Follow-up + history
        │   ├── company.py               # /company/* - Company CRUD
        │   ├── logistics.py             # /logistics/* /classroom/* - Logistics
        │   ├── approval.py              # /approvals/* - HITL approval queue
        │   ├── activity.py              # /activity/* - Audit timeline
        │   ├── telegram_group.py        # /telegram/* - Group creation + broadcast
        │   └── spoc.py                  # /spoc/* - Student question management
        ├── schemas/
        │   ├── recruitment_schema.py
        │   ├── company_schema.py
        │   ├── logistics_schema.py
        │   └── approval_schema.py
        └── services/
            ├── orchestrator.py          # State machine + audit log writer
            ├── llm_service.py           # All Groq LLM functions
            ├── email_service.py         # SMTP send + draft generation
            ├── gmail_reader.py          # Gmail API reader + email parsing
            ├── telegram_service.py      # Simple bot sendMessage functions
            ├── telegram_group_service.py # Telethon group creation service
            ├── company_agent.py         # Background polling thread (Company Agent)
            └── approval.py              # Approval creation helper
```

---

## 4. Environment Variables (`.env`)

```
EMAIL_USER=manojtamlurkar@gmail.com
EMAIL_PASS=<gmail-app-password>
TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_CHAT_ID=<main-group-chat-id>
TELEGRAM_API_ID=31188685
TELEGRAM_API_HASH=<api-hash>
TELEGRAM_PHONE=+918792884386
GROQ_API_KEY=<groq-key>
```

> **Note**: The `telegram_session.session` file is created by `setup_telegram_session.py`. It must exist on the server for Telegram group creation to work.

---

## 5. Database Schema (SQLite: `recruitment.db`)

### Tables

#### `recruitment_drive`
| Column | Type | Notes |
|---|---|---|
| id | PK | |
| company_name | String | Matches `companies.company_name` |
| hr_email | String | The HR's email address |
| status | String | State machine status (see §6) |
| spoc_name | String | Assigned SPOC's name |
| spoc_email | String | Assigned SPOC's email |

#### `companies`
| Column | Type | Notes |
|---|---|---|
| id | PK | |
| company_name | String | |
| email | String | Primary HR email |
| priority | String | |
| description | Text | Used by Company Agent LLM as context |
| poc_name | String | Point of Contact name |
| poc_email | String | |
| alternate_poc_* | String | Secondary POC fields |
| location / address | String/Text | |

#### `email_logs`
| Column | Type | Notes |
|---|---|---|
| company_id | FK → companies | |
| direction | String | `SENT` or `RECEIVED` |
| subject / body | String/Text | |
| timestamp | DateTime | |

#### `classrooms`
| Column | Type | Notes |
|---|---|---|
| name, building | String | |
| capacity | Integer | Used for auto-assignment |
| has_projector | Boolean | |

#### `drive_logistics`
| Column | Type | Notes |
|---|---|---|
| company_id | FK | |
| classroom_id | FK (auto-assigned) | |
| drive_date | DateTime | |
| student_count | Integer | |
| status | String | `PENDING` / `CONFIRMED` / `MANUAL_OVERRIDE_NEEDED` |
| registration_link | String | |
| followup_questions | Text | JSON array of strings |

#### `activity_logs`
| Column | Type | Notes |
|---|---|---|
| drive_id | FK (nullable) | |
| company_id | FK (nullable) | |
| actor | String | `ORCHESTRATOR` / `SPOC` / `AGENT` / `SYSTEM` / `USER` |
| action | String | `EMAIL_SENT`, `SPOC_ASSIGNED`, `DRIVE_CONFIRMED`, `STALE_ALERT`, etc. |
| details | Text | Human-readable description |
| timestamp | DateTime | |

#### `telegram_groups`
| Column | Type | Notes |
|---|---|---|
| company_id | FK | |
| drive_id | FK | |
| chat_id | String | Telegram supergroup ID (e.g. `-100xxx`) |
| group_name | String | e.g. "Microsoft — Apr 2026" |
| invite_link | String | `t.me/joinchat/...` |
| is_active | Boolean | |

#### `student_questions`
| Column | Type | Notes |
|---|---|---|
| company_id | FK | |
| drive_id | FK | |
| telegram_user | String | Display name of student |
| telegram_user_id | String | Telegram numeric user ID |
| question_text | Text | The actual question asked |
| status | String | `PENDING` / `ESCALATED` / `AUTO_ANSWERED` / `FORWARDED_TO_HR` / `HR_ANSWERED` |
| auto_answer | Text | LLM auto-generated answer (if any) |
| hr_answer | Text | Final answer from HR/SPOC |
| message_id | String | Telegram message ID (for threading) |

#### `approvals`
| Column | Type | Notes |
|---|---|---|
| recruitment_id | FK | |
| action | String | What action is pending approval |
| status | String | `PENDING` / `APPROVED` / `REJECTED` |

---

## 6. State Machine (Workflow Map)

The orchestrator drives state transitions via `WORKFLOW_MAP` in `orchestrator.py`:

```
INIT               → SEND_EMAIL          (Send first contact email to HR)
CONTACTED          → WAIT_FOR_REPLY      (Awaiting HR response)
DRIVE_CONFIRMED    → ASSIGN_SPOC         ← Primary flow: HR says yes → assign SPOC
SPOC_ASSIGNED      → SPOC_HANDLING       (SPOC takes over, create Telegram group)
SPOC_HANDLING      → MONITOR_DRIVE       (Company Agent active, SPOC managing)
LOGISTICS_CONFIRMED→ ASSIGN_SPOC         (Legacy fallback)
COMPLETED          → DONE
```

Status changes are triggered by:
- **Manual**: Dashboard buttons (`Confirm Drive`, `Assign SPOC`, `Proceed`)
- **Automatic**: `DriveLogistics` creation → status set to `LOGISTICS_CONFIRMED`
- **Agent**: Company Agent sets questions as `ESCALATED` or `AUTO_ANSWERED`

---

## 7. API Routes Reference

### Recruitment (`/recruitment`)
| Method | Path | Description |
|---|---|---|
| POST | `/recruitment/create` | Create a new recruitment drive |
| GET | `/recruitment/all` | Get all drives |
| GET | `/recruitment/next-step/{id}` | Get next workflow step |
| POST | `/recruitment/execute/{id}` | Execute next step (creates HITL approval if needed) |
| PATCH | `/recruitment/update-status/{id}` | Manually update status |
| PUT | `/recruitment/assign-spoc/{id}` | Assign SPOC + dispatch SPOC email |
| PATCH | `/recruitment/confirm-drive/{id}` | Confirm drive (HR confirmed → `DRIVE_CONFIRMED`) |

### Email (`/emails`, `/email-actions`)
| Method | Path | Description |
|---|---|---|
| GET | `/emails/latest` | Fetch + parse latest Gmail inbox (OAuth) |
| POST | `/emails/draft` | Generate context-aware follow-up email draft |
| POST | `/emails/send` | Send email via SMTP |
| GET | `/email-actions/history/{company_id}` | Full email thread for a company |

### Company (`/company`)
| Method | Path | Description |
|---|---|---|
| POST | `/company/create` | Create company |
| GET | `/company/all` | List all companies |
| PUT | `/company/{id}` | Update company |
| DELETE | `/company/{id}` | Delete company |
| GET | `/company/{id}/emails` | Email history for company |

### Logistics (`/logistics`, `/classroom`)
| Method | Path | Description |
|---|---|---|
| POST | `/classroom/create` | Add a classroom |
| GET | `/classroom/all` | List classrooms |
| POST | `/logistics/create` | Create logistics entry (auto-assigns classroom) |
| GET | `/logistics/{company_id}` | Get logistics for a company |
| POST | `/logistics/telegram-draft` | Generate Telegram announcement draft |
| POST | `/logistics/telegram-send` | Broadcast to main Telegram channel |
| POST | `/logistics/followup-email-draft` | Draft follow-up questions email |

### Telegram (`/telegram`)
| Method | Path | Description |
|---|---|---|
| POST | `/telegram/create-group/{drive_id}` | Create company Telegram supergroup via Telethon |
| GET | `/telegram/group/{drive_id}` | Get group info for a drive |
| GET | `/telegram/groups/all` | List all active groups |
| POST | `/telegram/broadcast-invite` | Send invite link to main channel via bot |
| POST | `/telegram/post-to-group` | Post a message to a company group |

### SPOC (`/spoc`)
| Method | Path | Description |
|---|---|---|
| GET | `/spoc/{drive_id}/questions` | Get student questions for a drive |
| POST | `/spoc/{drive_id}/forward-to-hr` | Draft + email selected questions to HR |
| POST | `/spoc/{drive_id}/answer-question/{q_id}` | Post manual answer to Telegram |

### Activity (`/activity`)
| Method | Path | Description |
|---|---|---|
| GET | `/activity/{drive_id}` | Full audit timeline for a drive |
| GET | `/activity/company/{company_id}` | Activity by company |
| POST | `/activity/check-stale` | Trigger orchestrator stale drive scan |

### Approvals (`/approvals`)
| Method | Path | Description |
|---|---|---|
| GET | `/approvals/pending` | List pending HITL approvals |
| POST | `/approvals/{id}/approve` | Approve an action |
| POST | `/approvals/{id}/reject` | Reject an action |

---

## 8. Key Services

### `orchestrator.py`
- Singleton `Orchestrator` class  
- `log_event(db, actor, action, details, drive_id, company_id)` — writes to `activity_logs`
- `check_stale_drives(db, stale_days=3)` — flags inactive drives with `STALE_ALERT`
- `get_next_step(status)` — returns the next workflow action from `WORKFLOW_MAP`

### `llm_service.py` (Groq — llama-3.1-8b-instant)
| Function | Purpose |
|---|---|
| `generate_email()` | Official CDC placement invitation email (static template) |
| `generate_followup_email()` | Context-aware follow-up based on email thread |
| `generate_spoc_assignment_email()` | Email to notify newly assigned SPOC |
| `generate_telegram_message()` | Announcement for Telegram channel |
| `generate_telegram_drive_message()` | Detailed Telegram drive announcement |
| `generate_followup_questions_email()` | Email to HR with a list of questions |
| `parse_email_content()` | Extract intent/time from incoming email snippet |
| `answer_student_question()` | Try to auto-answer a student question using context |
| `draft_questions_to_hr()` | Draft an email with escalated student questions |

### `telegram_group_service.py` (Telethon MTProto)
- `create_company_telegram_group(company_name, drive_date)` — creates a Telegram supergroup, adds the bot, promotes bot to admin, returns `{chat_id, group_name, invite_link}`
- `broadcast_invite_to_main_channel(invite_link, company_name)` — posts invite to main `TELEGRAM_CHAT_ID`
- `post_to_company_group(chat_id, message)` — posts a message in the company group via Bot API

### `company_agent.py` (Background Thread)
- Started at FastAPI lifespan startup via `start_agent_thread()`
- Continuously polls `getUpdates` via Bot API (long-polling, 30s timeout)
- For each message in a **registered company supergroup**:
  1. Calls `answer_student_question()` with company description + email history
  2. If `can_answer=True`: replies in group + saves as `AUTO_ANSWERED`
  3. If `can_answer=False`: tells student it will be escalated, saves as `ESCALATED`
- Only processes messages from `supergroup` chats registered in `telegram_groups` table

### `gmail_reader.py` (Gmail API)
- Reads latest 15 emails from the CDC Gmail inbox
- Parses sender, subject, snippet
- Calls `parse_email_content()` to extract intent
- Matches sender email to a `Company` record and logs as `RECEIVED` in `email_logs`

---

## 9. Frontend (Single Page App — `frontend/index.html`)

Tabs / Views:
| Sidebar Tab | View ID | What it shows |
|---|---|---|
| Dashboard | `view-dashboard` | All active drives with status, SPOC, Telegram group, activity timeline |
| SPOC Dashboard | `view-spoc` | Escalated student questions, forward to HR, manual answer panel |
| Approvals | `view-approvals` | HITL pending approvals |
| Communications | `view-comms` | Email inbox + compose/send terminal |
| Logistics & Venues | `view-logistics` | Classroom management + drive logistics |
| Company Repo | `view-companies` | Company CRUD |

**Drive Card features** (on Dashboard):
- Status badge + next action badge
- "Confirm Drive" button (when `CONTACTED`)
- "Assign SPOC" form (when `DRIVE_CONFIRMED`)
- SPOC name/email display (when assigned)
- "Create Telegram Group" button (when SPOC assigned, no group yet)
- Telegram group status + invite link + "📢 Broadcast" button (when group exists)
- Activity Timeline collapsible panel (chronological audit log)

---

## 10. Startup & Running

```bash
# Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv requests groq telethon

# One-time: Authenticate Telethon session
python setup_telegram_session.py

# Start backend
uvicorn main:app --reload

# Open frontend
# Open fastapi-backend/frontend/index.html in browser
```

The **Company Agent polling thread** starts automatically when the server boots.
