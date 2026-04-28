"""
Agent Console API
-----------------
Provides a unified endpoint that returns the full state of
every recruitment drive from the perspective of an autonomous agent.
For each drive, it reports:
  - current status & next recommended action
  - email counts (sent / received)
  - telegram group status
  - student questions breakdown
  - recent activity

It also exposes an /agent/run-step endpoint that lets the
frontend trigger the next automated action for a specific drive.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from backend.database.db import get_db
from backend.database.models import (
    RecruitmentDrive, Company, EmailLog, ActivityLog,
    TelegramGroup, StudentQuestion,
)
from backend.services.orchestrator import orchestrator, get_next_step

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent-console"])


# ── Response schemas ──────────────────────────────────────────────────

class DriveAgentState(BaseModel):
    drive_id: int
    company_id: Optional[int]
    company_name: str
    hr_email: str
    status: str
    spoc_name: Optional[str]
    next_action: str
    emails_sent: int
    emails_received: int
    has_telegram_group: bool
    telegram_group_name: Optional[str]
    telegram_invite_link: Optional[str]
    questions_total: int
    questions_auto_answered: int
    questions_forwarded: int
    questions_hr_answered: int
    questions_pending: int
    latest_activity: Optional[str]
    latest_activity_time: Optional[str]

class AgentSummary(BaseModel):
    total_drives: int
    active_drives: int
    pending_actions: int
    questions_awaiting_hr: int
    drives: List[DriveAgentState]

class RunStepRequest(BaseModel):
    action: str  # SEND_EMAIL | CREATE_TELEGRAM | DRAFT_BROADCAST | SYNC_EMAILS

class RunStepResponse(BaseModel):
    success: bool
    message: str
    action_taken: str


# ── GET /agent/status ─────────────────────────────────────────────────

@router.get("/status", response_model=AgentSummary)
def get_agent_status(db: Session = Depends(get_db)):
    """Returns the full agent-eye view of all recruitment drives."""

    drives = db.query(RecruitmentDrive).all()
    drive_states: List[DriveAgentState] = []
    total_pending = 0
    total_awaiting_hr = 0

    for drive in drives:
        company = db.query(Company).filter(
            Company.company_name == drive.company_name
        ).first()
        company_id = company.id if company else None

        # Email counts
        sent = received = 0
        if company_id:
            sent = db.query(EmailLog).filter(
                EmailLog.company_id == company_id, EmailLog.direction == "SENT"
            ).count()
            received = db.query(EmailLog).filter(
                EmailLog.company_id == company_id, EmailLog.direction == "RECEIVED"
            ).count()

        # Telegram group
        tg = db.query(TelegramGroup).filter(
            TelegramGroup.drive_id == drive.id, TelegramGroup.is_active == True
        ).first()

        # Student questions
        qs = db.query(StudentQuestion).filter(
            StudentQuestion.drive_id == drive.id
        ).all()
        q_auto = sum(1 for q in qs if q.status == "AUTO_ANSWERED")
        q_fwd = sum(1 for q in qs if q.status == "FORWARDED_TO_HR")
        q_hr = sum(1 for q in qs if q.status == "HR_ANSWERED")
        q_pend = sum(1 for q in qs if q.status in ("PENDING", "ESCALATED"))

        total_awaiting_hr += q_fwd
        
        # Determine next action
        next_action = get_next_step(drive.status)
        if next_action not in ("DONE", "UNKNOWN_STATUS"):
            total_pending += 1

        # Latest activity
        latest = db.query(ActivityLog).filter(
            ActivityLog.drive_id == drive.id
        ).order_by(ActivityLog.timestamp.desc()).first()

        drive_states.append(DriveAgentState(
            drive_id=drive.id,
            company_id=company_id,
            company_name=drive.company_name,
            hr_email=drive.hr_email,
            status=drive.status,
            spoc_name=drive.spoc_name,
            next_action=next_action,
            emails_sent=sent,
            emails_received=received,
            has_telegram_group=tg is not None,
            telegram_group_name=tg.group_name if tg else None,
            telegram_invite_link=tg.invite_link if tg else None,
            questions_total=len(qs),
            questions_auto_answered=q_auto,
            questions_forwarded=q_fwd,
            questions_hr_answered=q_hr,
            questions_pending=q_pend,
            latest_activity=latest.details if latest else None,
            latest_activity_time=str(latest.timestamp) if latest else None,
        ))

    active_count = sum(1 for d in drives if d.status not in ("COMPLETED", "DONE"))

    return AgentSummary(
        total_drives=len(drives),
        active_drives=active_count,
        pending_actions=total_pending,
        questions_awaiting_hr=total_awaiting_hr,
        drives=drive_states,
    )


# ── POST /agent/run-step/{drive_id} ──────────────────────────────────

@router.post("/run-step/{drive_id}", response_model=RunStepResponse)
def run_agent_step(drive_id: int, req: RunStepRequest, db: Session = Depends(get_db)):
    """Execute a specific automation step for a drive."""

    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    company = db.query(Company).filter(Company.company_name == drive.company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    action = req.action.upper()

    # ── SEND_EMAIL ──
    if action == "SEND_EMAIL":
        from backend.services.email_service import generate_email_draft, send_email
        from backend.services.llm_service import draft_questions_to_hr

        # Check for pending questions first
        pending_qs = db.query(StudentQuestion).filter(
            StudentQuestion.company_id == company.id,
            StudentQuestion.status.in_(["ESCALATED", "PENDING"])
        ).all()

        history = db.query(EmailLog).filter(EmailLog.company_id == company.id).order_by(EmailLog.timestamp.asc()).all()
        email_history = [{"direction": e.direction, "subject": e.subject, "body": e.body, "timestamp": str(e.timestamp)} for e in history]

        if pending_qs:
            q_texts = [q.question_text for q in pending_qs]
            spoc_name = drive.spoc_name or "CDC NITK Surathkal"
            draft = draft_questions_to_hr(q_texts, company.company_name, company.poc_name, spoc_name)
            subject = f"Student Queries - {company.company_name} Campus Drive"
        else:
            draft = generate_email_draft(company.company_name, company.poc_name, email_history)
            is_followup = bool(email_history)
            subject = (f"Follow-up regarding {company.company_name} campus drive" if is_followup
                       else f"Campus recruitment invitation - {company.company_name}")

        success = send_email(company.email, subject, draft, company.id, db)
        if not success:
            return RunStepResponse(success=False, message="Failed to send email", action_taken="SEND_EMAIL")

        # Update pending question statuses
        if pending_qs:
            for q in pending_qs:
                q.status = "FORWARDED_TO_HR"
            db.commit()

        if drive.status == "INIT":
            drive.status = "CONTACTED"
            db.commit()

        orchestrator.log_event(db, actor="AGENT", action="EMAIL_SENT",
                               details=f"Agent auto-sent email to {company.email} | Subject: {subject}",
                               drive_id=drive.id, company_id=company.id)

        return RunStepResponse(success=True, message=f"Email sent to {company.email}", action_taken="SEND_EMAIL")

    # ── SYNC_EMAILS ──
    elif action == "SYNC_EMAILS":
        from backend.services.gmail_reader import read_latest_emails
        try:
            read_latest_emails(db)
            orchestrator.log_event(db, actor="AGENT", action="EMAILS_SYNCED",
                                   details="Agent triggered email sync from Gmail",
                                   drive_id=drive.id, company_id=company.id)
            return RunStepResponse(success=True, message="Emails synced from Gmail", action_taken="SYNC_EMAILS")
        except Exception as e:
            return RunStepResponse(success=False, message=str(e), action_taken="SYNC_EMAILS")

    # ── CREATE_TELEGRAM ──
    elif action == "CREATE_TELEGRAM":
        existing = db.query(TelegramGroup).filter(
            TelegramGroup.drive_id == drive.id, TelegramGroup.is_active == True
        ).first()
        if existing:
            return RunStepResponse(success=True, message=f"Group already exists: {existing.group_name}", action_taken="CREATE_TELEGRAM")

        from backend.services.telegram_group_service import create_company_telegram_group
        try:
            result = create_company_telegram_group(company.company_name)
            tg = TelegramGroup(
                company_id=company.id, drive_id=drive.id,
                chat_id=result["chat_id"], group_name=result["group_name"],
                invite_link=result.get("invite_link")
            )
            db.add(tg)
            db.commit()
            orchestrator.log_event(db, actor="AGENT", action="TELEGRAM_GROUP_CREATED",
                                   details=f"Agent created Telegram group: {result['group_name']}",
                                   drive_id=drive.id, company_id=company.id)
            return RunStepResponse(success=True, message=f"Group created: {result['group_name']}", action_taken="CREATE_TELEGRAM")
        except Exception as e:
            return RunStepResponse(success=False, message=str(e), action_taken="CREATE_TELEGRAM")

    # ── DRAFT_BROADCAST ──
    elif action == "DRAFT_BROADCAST":
        tg = db.query(TelegramGroup).filter(
            TelegramGroup.drive_id == drive.id, TelegramGroup.is_active == True
        ).first()
        if not tg or not tg.invite_link:
            return RunStepResponse(success=False, message="No Telegram group with invite link found", action_taken="DRAFT_BROADCAST")

        from backend.services.llm_service import generate_telegram_broadcast_draft
        emails = db.query(EmailLog).filter(EmailLog.company_id == company.id).order_by(EmailLog.timestamp.desc()).limit(10).all()
        emails.reverse()
        email_history = [{"direction": e.direction, "subject": e.subject, "body": e.body} for e in emails]

        draft = generate_telegram_broadcast_draft(company.company_name, company.description, email_history, tg.invite_link)

        from backend.services.telegram_group_service import broadcast_invite_to_main_channel
        broadcast_invite_to_main_channel(tg.invite_link, company.company_name, draft)

        orchestrator.log_event(db, actor="AGENT", action="BROADCAST_SENT",
                               details=f"Agent drafted and broadcasted Telegram invite for {company.company_name}",
                               drive_id=drive.id, company_id=company.id)
        return RunStepResponse(success=True, message="Broadcast sent to main channel", action_taken="DRAFT_BROADCAST")

    # ── CONFIRM_DRIVE ──
    elif action == "CONFIRM_DRIVE":
        if drive.status in ("DRIVE_CONFIRMED", "SPOC_ASSIGNED", "SPOC_HANDLING"):
            return RunStepResponse(success=True, message="Drive already confirmed", action_taken="CONFIRM_DRIVE")
        drive.status = "DRIVE_CONFIRMED"
        db.commit()
        orchestrator.log_event(db, actor="AGENT", action="DRIVE_CONFIRMED",
                               details=f"Agent confirmed drive for {company.company_name}",
                               drive_id=drive.id, company_id=company.id)
        return RunStepResponse(success=True, message="Drive confirmed", action_taken="CONFIRM_DRIVE")

    else:
        return RunStepResponse(success=False, message=f"Unknown action: {action}", action_taken=action)


# ── GET /agent/kb/{company_id} ────────────────────────────────────────

class KBEntryResponse(BaseModel):
    id: int
    category: str
    topic: str
    content: str

@router.get("/kb/{company_id}", response_model=List[KBEntryResponse])
def get_company_knowledge_base(company_id: int, db: Session = Depends(get_db)):
    """Fetch all structured knowledge base entries for a given company."""
    from backend.database.models import KnowledgeBaseEntry
    entries = db.query(KnowledgeBaseEntry).filter(
        KnowledgeBaseEntry.company_id == company_id
    ).order_by(KnowledgeBaseEntry.category, KnowledgeBaseEntry.topic).all()
    
    return [
        KBEntryResponse(
            id=e.id,
            category=e.category or "General",
            topic=e.topic or "Fact",
            content=e.content
        )
        for e in entries
    ]
