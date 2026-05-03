# PlacementCommnAI — Agentic AI Framework for Campus Placement Communication

> An intelligent, event-driven AI framework that automates the end-to-end campus recruitment communication pipeline for the Career Development Centre (CDC), NITK Surathkal.

---

## 📌 Overview

Managing campus placement drives involves coordinating between HR representatives, students, SPOCs (Single Points of Contact), and administrative staff across multiple platforms. This system replaces manual, error-prone workflows with an **autonomous AI orchestrator** that:

- Reads and extracts context from HR emails via Gmail API
- Drafts and sends follow-up emails automatically
- Creates company-specific Telegram groups for student Q&A
- Broadcasts formatted announcements to the main student channel
- Answers student queries in real-time using a Retrieval-Augmented Generation (RAG) pipeline
- Escalates unanswered questions to human SPOCs via a queue-based dashboard
- Manages room logistics and drive scheduling

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     React + Vite Frontend                       │
│   Pipeline | Agent Console | SPOC Queue | Logistics | Activity  │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API (FastAPI)
┌─────────────────────────▼───────────────────────────────────────┐
│                    FastAPI Backend                               │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │ Orchestrator │  │   LLM Service   │  │  Telegram Service │  │
│  │  (State FSM) │  │  (Groq / LLaMA) │  │  (Telethon + Bot) │  │
│  └──────────────┘  └─────────────────┘  └───────────────────┘  │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────┐  │
│  │ Gmail Service│  │  Knowledge Base │  │  SQLite + ORM     │  │
│  │  (OAuth 2.0) │  │  (RAG Pipeline) │  │  (SQLAlchemy)     │  │
│  └──────────────┘  └─────────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **AI Orchestrator** | Event-driven state machine that autonomously drives each recruitment drive through its lifecycle |
| 📧 **Gmail Integration** | OAuth 2.0 authenticated email sync; LLM reads HR emails and drafts contextual replies |
| 💬 **Telegram Automation** | Programmatically creates company-specific Telegram supergroups and broadcasts announcements |
| 🧠 **Student Q&A Bot** | RAG-based Telegram bot answers student queries using HR email context; escalates unknowns |
| 👤 **SPOC Queue** | Dashboard for human coordinators to review, answer, and forward escalated questions |
| 📅 **Logistics Management** | Room inventory and drive logistics planning (date, expected students, registration link) |
| 📋 **Activity Audit Log** | Full chronological event trail for every action taken by AGENT, USER, or SYSTEM |
| ✅ **Human-in-the-Loop** | Approvals queue for sensitive actions before the pipeline proceeds |

---

## 🛠️ Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) — REST API framework
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM with SQLite database
- [Groq API](https://groq.com/) — LLM inference (LLaMA 3 / Mixtral)
- [Telethon](https://docs.telethon.dev/) — Telegram MTProto client for group creation
- [Telegram Bot API](https://core.telegram.org/bots/api) — Message broadcasting
- [Google Gmail API](https://developers.google.com/gmail/api) — Email read/send

**Frontend**
- [React 18](https://react.dev/) + TypeScript
- [Vite](https://vitejs.dev/) — Build tooling
- [React Router v6](https://reactrouter.com/) — Client-side routing

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Groq API key](https://console.groq.com/)
- A Telegram bot token (from [@BotFather](https://t.me/botfather))
- Google Cloud project with Gmail API enabled

### 1. Clone the Repository

```bash
git clone https://github.com/manojtamlurkar/PlacementCommnAI-An-Agentic-AI-Framework-For-Campus-Placement-Communication-Process.git
cd PlacementCommnAI-An-Agentic-AI-Framework-For-Campus-Placement-Communication-Process
```

### 2. Backend Setup

```bash
cd fastapi-backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file inside `fastapi-backend/`:

```env
GROQ_API_KEY=your_groq_api_key

TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=-100your_main_channel_chat_id
TELEGRAM_API_ID=your_telethon_api_id
TELEGRAM_API_HASH=your_telethon_api_hash
TELEGRAM_PHONE=+91xxxxxxxxxx
```

### 4. Set Up Gmail API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API for your project
3. Create OAuth 2.0 credentials and download `credentials.json`
4. Place `credentials.json` inside `fastapi-backend/`
5. On first run, a browser window will open for Gmail OAuth authentication

### 5. Set Up Telegram MTProto Session

```bash
python setup_telegram_session.py
```

This creates a `telegram_session.session` file. You only need to do this once.

### 6. Start the Backend

```bash
uvicorn main:app --reload
```

API is available at `http://localhost:8000`  
Swagger docs at `http://localhost:8000/docs`

### 7. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard is available at `http://localhost:5173`

---

## 📁 Project Structure

```
fastapi-backend/
├── main.py                   # FastAPI app entry point
├── requirements.txt
├── clear_db.py               # Utility to reset workflow data (preserves rooms)
├── setup_telegram_session.py # One-time Telegram MTProto auth
│
├── backend/
│   ├── database/
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   └── db.py             # DB session management
│   │
│   ├── routes/
│   │   ├── agent_console.py  # Agent step execution endpoint
│   │   ├── company.py        # Company CRUD + email sync
│   │   ├── drives.py         # Recruitment drive management
│   │   ├── telegram_group.py # Telegram group creation/broadcast
│   │   ├── spoc.py           # SPOC assignment & Q&A queue
│   │   ├── logistics.py      # Room inventory & drive logistics
│   │   └── activity.py       # Activity log retrieval
│   │
│   └── services/
│       ├── orchestrator.py         # Event-driven state machine
│       ├── llm_service.py          # Groq LLM prompting
│       ├── telegram_group_service.py # Telethon + Bot API integration
│       └── gmail_service.py        # Gmail API integration
│
└── frontend/
    └── src/
        ├── app/              # App shell & routing
        ├── features/         # Page-level feature modules
        └── shared/           # Reusable components & utilities
```

---

## 🔄 Recruitment Drive Workflow

```
INIT → CONTACTED → SPOC_HANDLING → ACTIVE_QA → SHORTLIST_RECEIVED
     → LOGISTICS_CONFIRMED → COMPLETED
```

Each status transition is handled autonomously by the AI orchestrator. At any stage, a human coordinator can intervene via the dashboard.

---

## 📸 Screenshots

> Add screenshots of your dashboard here after deployment.

---

## 📚 Project Documentation

This section lists all documents required for a B.Tech Major Project submission. All documents are stored in the `docs/` folder of this repository.

### Required Submission Documents

| # | Document | Description | Status |
|---|----------|-------------|--------|
| 1 | **Project Report** | Full thesis-format report covering all chapters (Introduction, Literature Survey, System Design, Implementation, Results, Conclusion) | ✅ Completed |
| 2 | **Synopsis / Abstract** | 1–2 page summary of the project objectives, methodology, and outcomes | ✅ Completed |
| 3 | **Presentation (PPT)** | Slides used during the final viva/presentation covering architecture, demo, and results | ✅ Completed |
| 4 | **IEEE / Research Paper** *(if applicable)* | Paper submitted to a conference or journal based on this project | 🔄 In Progress |

### Supporting Technical Documents

| # | Document | Description |
|---|----------|-------------|
| 5 | **System Requirements Specification (SRS)** | Functional and non-functional requirements of the system |
| 6 | **System Design Document (SDD)** | Architecture diagrams, ER diagram, data flow diagrams, and module descriptions |
| 7 | **API Documentation** | Auto-generated from FastAPI Swagger UI at `/docs` |
| 8 | **Test Report** | End-to-end workflow test results, bug log, and fix summary |
| 9 | **User Manual** | Step-by-step guide for CDC coordinators to operate the dashboard |

### Repository Structure for Docs

```
docs/
├── report/
│   └── PlacementCommnAI_Project_Report.pdf
├── synopsis/
│   └── synopsis.pdf
├── presentation/
│   └── final_presentation.pptx
├── srs/
│   └── SRS_Document.pdf
├── design/
│   ├── architecture_diagram.png
│   ├── er_diagram.png
│   └── data_flow_diagram.png
└── paper/
    └── research_paper_draft.pdf
```

> **Note for evaluators:** The full project report follows the NITK Surathkal B.Tech thesis format and covers all aspects of the system including literature review, system architecture, implementation details, and experimental results.

---

## 🤝 Contributing

This project was developed as a B.Tech final year major project at **NITK Surathkal**. Contributions and suggestions are welcome via GitHub Issues.

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 👤 Author

**Manoj Tamlurkar**  
B.Tech, NITK Surathkal  
[@TamlurkarManoj](https://twitter.com/TamlurkarManoj)
