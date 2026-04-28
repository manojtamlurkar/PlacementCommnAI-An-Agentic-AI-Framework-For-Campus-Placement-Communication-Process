from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from backend.services.gmail_reader import read_latest_emails
from backend.services.email_service import generate_email_draft, send_email
from backend.database.db import get_db
from backend.database.models import Company, EmailLog, StudentQuestion, RecruitmentDrive
from backend.services.orchestrator import orchestrator
from backend.services.llm_service import draft_questions_to_hr

router = APIRouter(prefix="/emails", tags=["emails"])

class EmailDraftRequest(BaseModel):
    company_id: int

class EmailSendRequest(BaseModel):
    to_email: str
    subject: str
    body: str

@router.get("/latest")
def get_latest_emails():
    return read_latest_emails()

@router.post("/draft")
def request_email_draft(req: EmailDraftRequest, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == req.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company layout not found")

    history_records = (
        db.query(EmailLog)
        .filter(EmailLog.company_id == req.company_id)
        .order_by(EmailLog.timestamp.asc())
        .all()
    )
    email_history = [
        {
            "direction": r.direction,
            "subject": r.subject or "",
            "body": r.body or "",
            "timestamp": str(r.timestamp)
        }
        for r in history_records
    ] if history_records else []

    # Check for unanswered questions
    unanswered_questions = db.query(StudentQuestion).filter(
        StudentQuestion.company_id == company.id,
        StudentQuestion.status.in_(["ESCALATED", "PENDING"])
    ).all()

    if unanswered_questions:
        q_texts = [q.question_text for q in unanswered_questions]
        drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.company_name == company.company_name).first()
        spoc_name = drive.spoc_name if drive else "CDC NITK Surathkal"
        
        draft_content = draft_questions_to_hr(
            questions_list=q_texts,
            company_name=company.company_name,
            poc_name=company.poc_name,
            spoc_name=spoc_name
        )
    else:
        draft_content = generate_email_draft(company.company_name, company.poc_name, email_history)
        
    is_followup = bool(email_history)
    return {
        "draft": draft_content,
        "is_followup": is_followup,
        "emails_in_thread": len(email_history)
    }

@router.post("/send")
def process_send_email(req: EmailSendRequest, db: Session = Depends(get_db)):
    import json
    from backend.services.approval import create_approval
    
    target_company = db.query(Company).filter(Company.email.ilike(req.to_email)).first()
    company_id_link = target_company.id if target_company else None

    # Get recruitment drive
    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.company_name == target_company.company_name).first() if target_company else None
    
    if not drive:
        raise HTTPException(status_code=404, detail="Recruitment drive not found for this company")
        
    payload_str = json.dumps({
        "to_email": req.to_email,
        "subject": req.subject,
        "body": req.body
    })
    
    create_approval(drive.id, "SEND_EMAIL", db, payload_str)

    return {"success": True, "message": "Email queued for approval successfully!"}


@router.get("/notifications")
def get_email_notifications(since_id: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Returns all RECEIVED emails since a given email log ID.
    The frontend polls this every 30s and shows a notification bell
    when new HR responses arrive.
    """
    query = db.query(EmailLog, Company).join(
        Company, EmailLog.company_id == Company.id
    ).filter(
        EmailLog.direction == "RECEIVED"
    )

    if since_id:
        query = query.filter(EmailLog.id > since_id)

    results = query.order_by(desc(EmailLog.id)).all()

    notifications = [
        {
            "id": log.id,
            "company_name": company.company_name,
            "subject": log.subject,
            "snippet": (log.body or "")[:120] + ("..." if len(log.body or "") > 120 else ""),
            "timestamp": log.timestamp.isoformat() + "Z" if log.timestamp else None,
        }
        for log, company in results
    ]

    return {
        "success": True,
        "data": notifications,
        "latest_id": notifications[0]["id"] if notifications else since_id,
    }
