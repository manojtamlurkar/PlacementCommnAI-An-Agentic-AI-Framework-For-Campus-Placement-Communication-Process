import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from backend.database.models import Approval, RecruitmentDrive
from backend.services.telegram_service import send_telegram_message

logger = logging.getLogger(__name__)

def create_approval(recruitment_id: int, step_name: str, db: Session, payload: str = None):
    try:
        new_approval = Approval(recruitment_id=recruitment_id, action=step_name, status="PENDING", payload=payload)
        db.add(new_approval)
        db.commit()
        db.refresh(new_approval)
        return new_approval
    except SQLAlchemyError as e:
        logger.error(f"Error creating approval for recruitment id {recruitment_id}: {e}")
        db.rollback()
        raise

def get_pending_approvals(db: Session):
    try:
        return db.query(Approval).filter(Approval.status == "PENDING").all()
    except SQLAlchemyError as e:
        logger.error(f"Error fetching pending approvals: {e}")
        raise

def handle_action(approval_id: int, action: str, db: Session, updated_payload: str = None):
    try:
        approval = db.query(Approval).filter(Approval.id == approval_id).first()
        
        if not approval:
            return None
            
        if action == "APPROVE":
            approval.status = "APPROVED"
            
            # If payload was updated, save it back
            if updated_payload is not None:
                approval.payload = updated_payload
                
            db.commit()
            
            # Trigger workflow actions upon approval automatically
            if approval.action == "SEND_EMAIL":
                import json
                from backend.services.email_service import send_email
                from backend.database.models import StudentQuestion, Company
                from backend.services.orchestrator import orchestrator
                
                payload_str = approval.payload
                if payload_str:
                    payload_data = json.loads(payload_str)
                    to_email = payload_data.get("to_email")
                    subject = payload_data.get("subject")
                    body = payload_data.get("body")
                    
                    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == approval.recruitment_id).first()
                    target_company = db.query(Company).filter(Company.company_name == drive.company_name).first() if drive else None
                    company_id_link = target_company.id if target_company else None
                    
                    success = send_email(to_email, subject, body, company_id_link, db)
                    if success:
                        questions = db.query(StudentQuestion).filter(
                            StudentQuestion.company_id == company_id_link,
                            StudentQuestion.status.in_(["ESCALATED", "PENDING"])
                        ).all()
                        if questions:
                            for q in questions:
                                q.status = "FORWARDED_TO_HR"
                            db.commit()
                            
                        orchestrator.log_event(
                            db=db, actor="USER", action="EMAIL_SENT",
                            details=f"Email dispatched to {to_email} | Subject: {subject}",
                            company_id=company_id_link
                        )
            elif approval.action == "NOTIFY_STUDENTS":
                drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == approval.recruitment_id).first()
                if drive:
                    send_telegram_message(drive.company_name)
                    
            elif approval.action.startswith("PROCESS_HR_RESPONSE"):
                action_parts = approval.action.split("|")
                intent = action_parts[1] if len(action_parts) > 1 else ""
                
                if intent == "SCHEDULE_CONFIRM":
                    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == approval.recruitment_id).first()
                    if drive:
                        drive.status = "SCHEDULE_RECEIVED"
                        logger.info(f"Drive {drive.id} status actively promoted to SCHEDULE_RECEIVED via HR interaction")
                        db.commit()
                        
            db.refresh(approval)
            
        elif action == "REJECT":
            approval.status = "REJECTED"
            db.commit()
            db.refresh(approval)
            
        return approval
    except SQLAlchemyError as e:
        logger.error(f"Error handling action for approval {approval_id}: {e}")
        db.rollback()
        raise
