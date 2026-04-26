import os
import smtplib
from email.mime.text import MIMEText
import logging
from sqlalchemy.orm import Session
from backend.services.llm_service import generate_email, generate_followup_email
from backend.database.models import EmailLog

logger = logging.getLogger(__name__)

def generate_email_draft(company_name: str, poc_name: str = None, email_history: list = None) -> str:
    """
    First contact  → official CDC NITK Surathkal template (no LLM).
    Follow-up       → LLM-generated draft with full thread context.
    """
    if email_history:
        return generate_followup_email(company_name, poc_name, email_history)
    return generate_email(company_name, poc_name)

def send_email(to_email: str, subject: str, body: str, company_id: int, db: Session) -> bool:
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")

    if not email_user or not email_pass:
        logger.error("Email credentials not found. Ensure EMAIL_USER and EMAIL_PASS are set in environment variables.")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = to_email

    try:
        # Use TLS on port 587
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        
        # Log injection cleanly
        new_log = EmailLog(
            company_id=company_id,
            direction="SENT",
            subject=subject,
            body=body
        )
        db.add(new_log)
        db.commit()
        
        logger.info(f"Email sent successfully to {to_email} and logged")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
