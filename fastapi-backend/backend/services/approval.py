import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from backend.database.models import Approval, RecruitmentDrive
from backend.services.telegram_service import send_telegram_message

logger = logging.getLogger(__name__)

def create_approval(recruitment_id: int, step_name: str, db: Session):
    try:
        new_approval = Approval(recruitment_id=recruitment_id, action=step_name, status="PENDING")
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

def handle_action(approval_id: int, action: str, db: Session):
    try:
        approval = db.query(Approval).filter(Approval.id == approval_id).first()
        
        if not approval:
            return None
            
        if action == "APPROVE":
            approval.status = "APPROVED"
            db.commit()
            
            # Trigger workflow actions upon approval automatically
            if approval.action == "SEND_EMAIL":
                # Execution shifted perfectly to Draft -> Edit -> Send UI flow
                pass
                    
                    
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
