from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.services.gmail_reader import read_latest_emails
from backend.services.email_service import generate_email_draft, send_email
from backend.database.db import get_db
from backend.database.models import Company, EmailLog
from backend.services.orchestrator import orchestrator

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

    draft_content = generate_email_draft(company.company_name, company.poc_name, email_history)
    is_followup = bool(email_history)
    return {
        "draft": draft_content,
        "is_followup": is_followup,
        "emails_in_thread": len(email_history)
    }

@router.post("/send")
def process_send_email(req: EmailSendRequest, db: Session = Depends(get_db)):
    target_company = db.query(Company).filter(Company.email.ilike(req.to_email)).first()
    company_id_link = target_company.id if target_company else None

    success = send_email(req.to_email, req.subject, req.body, company_id_link, db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to physically connect payload to SMTP server")

    # Log to orchestrator activity trail
    orchestrator.log_event(
        db=db, actor="USER", action="EMAIL_SENT",
        details=f"Email dispatched to {req.to_email} | Subject: {req.subject}",
        company_id=company_id_link
    )
    return {"success": True, "message": "Email dispatched to HR securely!"}
