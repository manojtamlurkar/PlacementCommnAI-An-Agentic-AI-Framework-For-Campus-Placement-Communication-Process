"""
Autonomous Agent Engine
-----------------------
Background daemon that continuously monitors all active recruitment drives
and autonomously executes the next logical step in the pipeline.

Lifecycle:  Drive Created → Send Email → Wait for Reply → Analyze Intent
            → Confirm Drive → Assign SPOC → Create Telegram → Broadcast
            → Monitor Student Queries → Batch Email HR → Relay Answers
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal
from backend.database.models import (
    RecruitmentDrive, Company, EmailLog, TelegramGroup,
    StudentQuestion, ActivityLog, SpocPool,
)
from backend.services.orchestrator import orchestrator

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────
AGENT_TICK_SECONDS = 30        # How often the agent wakes up
STALE_THRESHOLD_DAYS = 3       # Days without reply before auto follow-up
QUERY_BATCH_THRESHOLD = 3      # Min pending student Qs before emailing HR


# ── Main Loop ─────────────────────────────────────────────────────────

def _agent_loop():
    """Background daemon: wake → inspect all drives → act → sleep."""
    logger.info("[AUTONOMOUS AGENT] Started. Polling every %ds.", AGENT_TICK_SECONDS)
    # Small startup delay to let other services initialize
    time.sleep(5)

    while True:
        db = SessionLocal()
        try:
            process_all_drives(db)
        except Exception as e:
            logger.error(f"[AUTONOMOUS AGENT] Tick error: {e}")
        finally:
            db.close()
        time.sleep(AGENT_TICK_SECONDS)


def process_all_drives(db: Session):
    """Iterate every active drive and decide what to do next."""
    drives = db.query(RecruitmentDrive).filter(
        RecruitmentDrive.status.notin_(["COMPLETED", "DONE"])
    ).all()

    for drive in drives:
        company = db.query(Company).filter(
            Company.company_name == drive.company_name
        ).first()
        if not company:
            continue
        try:
            process_single_drive(db, drive, company)
        except Exception as e:
            logger.error(f"[AGENT] Error processing drive {drive.id} ({drive.company_name}): {e}")


# ── State Machine Executor ────────────────────────────────────────────

def process_single_drive(db: Session, drive: RecruitmentDrive, company: Company):
    """Core decision engine — inspects current status and acts."""
    
    # Always sync knowledge base with new emails first
    _sync_knowledge_base(db, drive, company)

    status = drive.status.upper()

    # ── INIT → Send first invitation email ────────────────────────
    if status == "INIT":
        _handle_init(db, drive, company)

    # ── CONTACTED → Wait for reply, check for new emails ──────────
    elif status == "CONTACTED":
        _handle_contacted(db, drive, company)

    # ── INFO_SHARED → HR shared JD but no confirmation yet ────────
    elif status == "INFO_SHARED":
        _handle_contacted(db, drive, company)  # same logic: wait for confirmation

    # ── DRIVE_CONFIRMED → Auto-assign SPOC ────────────────────────
    elif status == "DRIVE_CONFIRMED":
        _handle_drive_confirmed(db, drive, company)

    # ── SPOC_ASSIGNED → Create Telegram + Broadcast ───────────────
    elif status == "SPOC_ASSIGNED":
        _handle_spoc_assigned(db, drive, company)

    # ── SPOC_HANDLING → Monitor student queries ───────────────────
    elif status == "SPOC_HANDLING":
        _handle_spoc_handling(db, drive, company)


# ── Step Handlers ─────────────────────────────────────────────────────

def _sync_knowledge_base(db: Session, drive: RecruitmentDrive, company: Company):
    """Syncs new HR emails into the company's Knowledge Base table."""
    from backend.database.models import KnowledgeBaseEntry
    
    received_emails = db.query(EmailLog).filter(
        EmailLog.company_id == company.id,
        EmailLog.direction == "RECEIVED"
    ).order_by(EmailLog.timestamp.asc()).all()

    for email in received_emails:
        already_merged = db.query(ActivityLog).filter(
            ActivityLog.company_id == company.id,
            ActivityLog.action == "KNOWLEDGE_BASE_UPDATED",
            ActivityLog.details.contains(f"#{email.id}")
        ).first()

        if not already_merged:
            from backend.services.llm_service import extract_knowledge_entries
            entries = extract_knowledge_entries(company.company_name, email.body)
            
            for item in entries:
                # Basic deduplication by topic for the same company
                existing = db.query(KnowledgeBaseEntry).filter(
                    KnowledgeBaseEntry.company_id == company.id,
                    KnowledgeBaseEntry.topic == item.get("topic", "")
                ).first()
                
                if existing:
                    existing.content = item.get("content", "")
                else:
                    new_entry = KnowledgeBaseEntry(
                        company_id=company.id,
                        category=item.get("category", "General"),
                        topic=item.get("topic", "Fact"),
                        content=item.get("content", ""),
                        source_email_id=email.id
                    )
                    db.add(new_entry)

            db.commit()

            from backend.services.orchestrator import orchestrator
            orchestrator.log_event(
                db, actor="AGENT", action="KNOWLEDGE_BASE_UPDATED",
                details=f"Extracted {len(entries)} facts from HR email #{email.id} into Knowledge Base.",
                drive_id=drive.id, company_id=company.id,
            )
            logger.info(f"[AGENT] Extracted {len(entries)} KB facts for {company.company_name} from email #{email.id}")

def _handle_init(db: Session, drive: RecruitmentDrive, company: Company):
    """INIT → Generate and send the invitation email to HR."""
    from backend.services.email_service import generate_email_draft, send_email

    # Check if we already sent an email (prevent duplicate sends on restart)
    existing_sent = db.query(EmailLog).filter(
        EmailLog.company_id == company.id,
        EmailLog.direction == "SENT"
    ).first()
    if existing_sent:
        # Already sent but status wasn't updated — fix it
        drive.status = "CONTACTED"
        db.commit()
        return

    draft = generate_email_draft(company.company_name, company.poc_name)
    subject = f"Campus recruitment invitation - {company.company_name}"

    success = send_email(company.email, subject, draft, company.id, db)
    if success:
        drive.status = "CONTACTED"
        db.commit()
        orchestrator.log_event(
            db, actor="AGENT", action="EMAIL_SENT",
            details=f"Agent auto-sent invitation email to {company.email}",
            drive_id=drive.id, company_id=company.id,
        )
        logger.info(f"[AGENT] Sent invitation to {company.company_name}")
    else:
        logger.error(f"[AGENT] Failed to send invitation for {company.company_name}")


def _handle_contacted(db: Session, drive: RecruitmentDrive, company: Company):
    """CONTACTED → Check for new HR replies and analyze intent."""
    from backend.services.llm_service import analyze_hr_response_intent
    from backend.services.email_service import generate_email_draft, send_email

    # Find the latest RECEIVED email for this company
    latest_received = db.query(EmailLog).filter(
        EmailLog.company_id == company.id,
        EmailLog.direction == "RECEIVED"
    ).order_by(EmailLog.timestamp.desc()).first()

    if latest_received:
        # Check if we've already analyzed this email (avoid re-processing)
        already_analyzed = db.query(ActivityLog).filter(
            ActivityLog.company_id == company.id,
            ActivityLog.action == "HR_EMAIL_ANALYZED",
            ActivityLog.details.contains(str(latest_received.id))
        ).first()

        if not already_analyzed:
            # Analyze the HR response
            analysis = analyze_hr_response_intent(latest_received.body, latest_received.subject)
            intent = analysis.get("intent", "UNKNOWN").upper()
            summary = analysis.get("summary", "")

            orchestrator.log_event(
                db, actor="AGENT", action="HR_EMAIL_ANALYZED",
                details=f"Analyzed email #{latest_received.id} | Intent: {intent} | {summary}",
                drive_id=drive.id, company_id=company.id,
            )

            if intent == "DRIVE_CONFIRMED":
                drive.status = "DRIVE_CONFIRMED"
                db.commit()
                orchestrator.log_event(
                    db, actor="AGENT", action="DRIVE_CONFIRMED",
                    details=f"HR confirmed the drive for {company.company_name}. Auto-transitioning.",
                    drive_id=drive.id, company_id=company.id,
                )
                logger.info(f"[AGENT] Drive CONFIRMED for {company.company_name}")

            elif intent == "INFO_SHARED":
                drive.status = "INFO_SHARED"
                db.commit()
                # Send a follow-up acknowledging the info and requesting confirmation
                history = _get_email_history(db, company.id)
                draft = generate_email_draft(company.company_name, company.poc_name, history)
                subject = f"Re: {latest_received.subject}"
                send_email(company.email, subject, draft, company.id, db)
                orchestrator.log_event(
                    db, actor="AGENT", action="FOLLOWUP_SENT",
                    details=f"HR shared info. Agent sent follow-up to request drive confirmation.",
                    drive_id=drive.id, company_id=company.id,
                )

            elif intent == "QUERY":
                # HR asked questions — send a context-aware reply
                history = _get_email_history(db, company.id)
                draft = generate_email_draft(company.company_name, company.poc_name, history)
                subject = f"Re: {latest_received.subject}"
                send_email(company.email, subject, draft, company.id, db)
                orchestrator.log_event(
                    db, actor="AGENT", action="FOLLOWUP_SENT",
                    details=f"HR asked questions. Agent sent a reply.",
                    drive_id=drive.id, company_id=company.id,
                )

            elif intent == "REJECTION":
                drive.status = "COMPLETED"
                db.commit()
                orchestrator.log_event(
                    db, actor="AGENT", action="DRIVE_REJECTED",
                    details=f"HR declined participation for {company.company_name}. Drive closed.",
                    drive_id=drive.id, company_id=company.id,
                )
                logger.info(f"[AGENT] Drive REJECTED for {company.company_name}")

    else:
        # No reply yet — check for staleness
        latest_sent = db.query(EmailLog).filter(
            EmailLog.company_id == company.id,
            EmailLog.direction == "SENT"
        ).order_by(EmailLog.timestamp.desc()).first()

        if latest_sent and latest_sent.timestamp:
            days_since = (datetime.utcnow() - latest_sent.timestamp).days
            if days_since >= STALE_THRESHOLD_DAYS:
                # Check we haven't already sent a follow-up recently
                recent_followup = db.query(ActivityLog).filter(
                    ActivityLog.drive_id == drive.id,
                    ActivityLog.action == "FOLLOWUP_SENT",
                    ActivityLog.timestamp >= datetime.utcnow() - timedelta(days=STALE_THRESHOLD_DAYS)
                ).first()

                if not recent_followup:
                    history = _get_email_history(db, company.id)
                    draft = generate_email_draft(company.company_name, company.poc_name, history)
                    subject = f"Follow-up regarding {company.company_name} campus drive"
                    send_email(company.email, subject, draft, company.id, db)
                    orchestrator.log_event(
                        db, actor="AGENT", action="FOLLOWUP_SENT",
                        details=f"No HR reply for {days_since} days. Agent sent auto follow-up.",
                        drive_id=drive.id, company_id=company.id,
                    )
                    logger.info(f"[AGENT] Auto follow-up sent for {company.company_name} (stale {days_since}d)")


def _handle_drive_confirmed(db: Session, drive: RecruitmentDrive, company: Company):
    """DRIVE_CONFIRMED → Auto-assign SPOC from pool."""
    spoc = auto_assign_spoc(db)
    if spoc:
        drive.spoc_name = spoc.name
        drive.spoc_email = spoc.email
        drive.status = "SPOC_ASSIGNED"
        spoc.active_drives += 1
        db.commit()

        # Send SPOC assignment notification email
        from backend.services.llm_service import generate_spoc_assignment_email
        from backend.services.email_service import send_email
        draft = generate_spoc_assignment_email(spoc.name, company.company_name, company.email)
        send_email(spoc.email, f"SPOC Assignment - {company.company_name}", draft, company.id, db)

        orchestrator.log_event(
            db, actor="AGENT", action="SPOC_ASSIGNED",
            details=f"Auto-assigned SPOC {spoc.name} ({spoc.email}) to {company.company_name}",
            drive_id=drive.id, company_id=company.id,
        )
        logger.info(f"[AGENT] SPOC {spoc.name} assigned to {company.company_name}")
    else:
        logger.warning(f"[AGENT] No available SPOCs for {company.company_name}. Waiting...")


def _handle_spoc_assigned(db: Session, drive: RecruitmentDrive, company: Company):
    """SPOC_ASSIGNED → Create Telegram group, post JD, broadcast."""
    # Check if group already exists
    existing_group = db.query(TelegramGroup).filter(
        TelegramGroup.drive_id == drive.id,
        TelegramGroup.is_active == True
    ).first()

    if not existing_group:
        try:
            from backend.services.telegram_group_service import create_company_telegram_group
            result = create_company_telegram_group(company.company_name)
            tg = TelegramGroup(
                company_id=company.id,
                drive_id=drive.id,
                chat_id=result["chat_id"],
                group_name=result["group_name"],
                invite_link=result.get("invite_link"),
            )
            db.add(tg)
            db.commit()
            existing_group = tg
            orchestrator.log_event(
                db, actor="AGENT", action="TELEGRAM_GROUP_CREATED",
                details=f"Auto-created Telegram group: {result['group_name']}",
                drive_id=drive.id, company_id=company.id,
            )
            logger.info(f"[AGENT] Created Telegram group for {company.company_name}")
        except Exception as e:
            logger.error(f"[AGENT] Failed to create Telegram group for {company.company_name}: {e}")
            return

    # Post JD to the group
    if existing_group:
        _post_jd_to_group(db, drive, company, existing_group)

        # Broadcast invite to main channel
        if existing_group.invite_link:
            _broadcast_to_main_channel(db, drive, company, existing_group)

        # Transition to SPOC_HANDLING
        drive.status = "SPOC_HANDLING"
        db.commit()
        orchestrator.log_event(
            db, actor="AGENT", action="DRIVE_SETUP_COMPLETE",
            details=f"Telegram group created, JD posted, broadcast sent. Drive is now in SPOC_HANDLING.",
            drive_id=drive.id, company_id=company.id,
        )


def _handle_spoc_handling(db: Session, drive: RecruitmentDrive, company: Company):
    """SPOC_HANDLING → Monitor for pending student queries and batch-email HR."""
    pending_qs = db.query(StudentQuestion).filter(
        StudentQuestion.company_id == company.id,
        StudentQuestion.status.in_(["ESCALATED", "PENDING"]),
    ).all()

    if len(pending_qs) >= QUERY_BATCH_THRESHOLD:
        # Check we haven't emailed HR about these already (cooldown: 1 hour)
        recent_escalation = db.query(ActivityLog).filter(
            ActivityLog.drive_id == drive.id,
            ActivityLog.action == "QUESTIONS_BATCH_EMAILED",
            ActivityLog.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).first()

        if not recent_escalation:
            from backend.services.llm_service import draft_questions_to_hr
            from backend.services.email_service import send_email

            q_texts = [q.question_text for q in pending_qs]
            spoc_name = drive.spoc_name or "CDC NITK Surathkal"

            draft = draft_questions_to_hr(q_texts, company.company_name, company.poc_name, spoc_name)
            subject = f"Student Queries - {company.company_name} Campus Drive"
            success = send_email(company.email, subject, draft, company.id, db)

            if success:
                for q in pending_qs:
                    q.status = "FORWARDED_TO_HR"
                db.commit()

                orchestrator.log_event(
                    db, actor="AGENT", action="QUESTIONS_BATCH_EMAILED",
                    details=f"Auto-batched {len(pending_qs)} student questions and emailed HR.",
                    drive_id=drive.id, company_id=company.id,
                )
                logger.info(f"[AGENT] Batched {len(pending_qs)} Qs and emailed HR for {company.company_name}")


# ── Helper Functions ──────────────────────────────────────────────────

def auto_assign_spoc(db: Session) -> SpocPool:
    """Pick the least-loaded available SPOC from the pool."""
    spoc = db.query(SpocPool).filter(
        SpocPool.is_available == True
    ).order_by(SpocPool.active_drives.asc()).first()
    return spoc


def _get_email_history(db: Session, company_id: int) -> list:
    """Fetch full email thread for a company."""
    emails = db.query(EmailLog).filter(
        EmailLog.company_id == company_id
    ).order_by(EmailLog.timestamp.asc()).all()
    return [
        {"direction": e.direction, "subject": e.subject, "body": e.body, "timestamp": str(e.timestamp)}
        for e in emails
    ]


def _post_jd_to_group(db: Session, drive: RecruitmentDrive, company: Company, tg_group: TelegramGroup):
    """
    Post the FULL JD + eligibility + CTC details to the COMPANY-SPECIFIC Telegram group.
    This is the detailed information message pinned inside the group.
    """
    from backend.services.telegram_group_service import post_to_company_group
    from backend.services.company_agent import _send_bot_message

    email_history = _get_email_history(db, company.id)

    if email_history:
        from backend.services.llm_service import generate_company_group_jd_post
        jd_message = generate_company_group_jd_post(company.company_name, email_history)
    else:
        jd_message = (
            f"📢 Welcome to the **{company.company_name}** Placement Drive group!\n\n"
            f"Full details (JD, eligibility, CTC) will be shared here shortly. Stay tuned!"
        )

    _send_bot_message(tg_group.chat_id, jd_message)
    logger.info(f"[AGENT] Posted full JD to company group for {company.company_name}")


def _broadcast_to_main_channel(db: Session, drive: RecruitmentDrive, company: Company, tg_group: TelegramGroup):
    """
    Post a DETAILED announcement to the MAIN student announcement channel.
    Contains: full JD, eligibility criteria, CTC, and the invite link to the company group.
    """
    from backend.services.telegram_group_service import broadcast_invite_to_main_channel
    from backend.services.llm_service import generate_telegram_broadcast_draft

    email_history = _get_email_history(db, company.id)

    announcement = generate_telegram_broadcast_draft(
        company.company_name, company.description, email_history, tg_group.invite_link
    )
    broadcast_invite_to_main_channel(tg_group.invite_link, company.company_name, announcement)
    logger.info(f"[AGENT] Sent detailed JD announcement to main channel for {company.company_name}")


# ── Thread Launcher ───────────────────────────────────────────────────

def start_autonomous_agent_thread():
    """Start the autonomous agent as a daemon thread."""
    thread = threading.Thread(target=_agent_loop, daemon=True, name="AutonomousAgent")
    thread.start()
    logger.info("[AUTONOMOUS AGENT] Thread launched.")
