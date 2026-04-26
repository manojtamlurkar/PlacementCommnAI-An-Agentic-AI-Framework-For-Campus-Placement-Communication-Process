import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from backend.database.db import get_db
from backend.database.models import RecruitmentDrive, Company
from backend.schemas.recruitment_schema import RecruitmentDriveCreate, RecruitmentDriveResponse, StandardResponse, RecruitmentDriveUpdateStatus, AssignSpocRequest
from backend.services.orchestrator import get_next_step, orchestrator
from backend.services.approval import create_approval
from backend.services.llm_service import generate_spoc_assignment_email
from backend.services.email_service import send_email

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/recruitment",
    tags=["recruitment"]
)

@router.post("/create", response_model=StandardResponse[RecruitmentDriveResponse])
def create_recruitment_drive(drive: RecruitmentDriveCreate, db: Session = Depends(get_db)):
    try:
        db_drive = RecruitmentDrive(**drive.model_dump())
        db.add(db_drive)
        db.commit()
        db.refresh(db_drive)
        orchestrator.log_event(
            db=db, actor="USER", action="DRIVE_CREATED",
            details=f"Recruitment drive created for {db_drive.company_name} with status {db_drive.status}",
            drive_id=db_drive.id
        )
        logger.info(f"Recruitment created: {db_drive.company_name}")
        return {"success": True, "message": "Recruitment drive created successfully", "data": db_drive}
    except SQLAlchemyError as e:
        logger.error(f"Database error during creation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/all", response_model=StandardResponse[List[RecruitmentDriveResponse]])
def get_all_recruitment_drives(db: Session = Depends(get_db)):
    try:
        drives = db.query(RecruitmentDrive).all()
        return {"success": True, "message": "Fetched all drives", "data": drives}
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/next-step/{id}", response_model=StandardResponse[dict])
def get_recruitment_next_step(id: int, db: Session = Depends(get_db)):
    try:
        drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == id).first()
        if not drive:
            raise HTTPException(status_code=404, detail="Recruitment drive not found")
            
        next_action = get_next_step(drive.status)
        return {
            "success": True,
            "message": "Next step determined",
            "data": {
                "current_status": drive.status,
                "next_action": next_action
            }
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/execute/{id}", response_model=StandardResponse[dict])
def execute_next_step(id: int, db: Session = Depends(get_db)):
    try:
        drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == id).first()
        if not drive:
            raise HTTPException(status_code=404, detail="Recruitment drive not found")
        
        next_action = get_next_step(drive.status)
        hitl_actions = ["SEND_EMAIL", "REQUEST_LOGISTICS", "NOTIFY_STUDENTS"]
        
        if next_action in hitl_actions:
            approval = create_approval(id, next_action, db)
            logger.info(f"Approval requested for recruitment {id}: {next_action}")
            return {
                "success": True,
                "message": f"Action {next_action} requires approval. Approval request created.",
                "data": {"approval_id": approval.id}
            }
            
        return {"success": True, "message": f"Action {next_action} executed successfully directly.", "data": None}
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/update-status/{id}", response_model=StandardResponse[RecruitmentDriveResponse])
def update_recruitment_status(id: int, update_data: RecruitmentDriveUpdateStatus, db: Session = Depends(get_db)):
    try:
        drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == id).first()
        if not drive:
            raise HTTPException(status_code=404, detail="Recruitment drive not found")
        
        drive.status = update_data.status
        db.commit()
        db.refresh(drive)
        orchestrator.log_event(
            db=db, actor="USER", action="STATUS_UPDATED",
            details=f"Drive status changed to {update_data.status}",
            drive_id=drive.id
        )
        logger.info(f"Recruitment status updated for id {id} to {drive.status}")
        return {"success": True, "message": "Status updated successfully", "data": drive}
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/assign-spoc/{id}", response_model=StandardResponse[RecruitmentDriveResponse])
def assign_spoc_to_drive(id: int, request: AssignSpocRequest, db: Session = Depends(get_db)):
    try:
        drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == id).first()
        if not drive:
            raise HTTPException(status_code=404, detail="Recruitment drive not found")
            
        drive.spoc_name = request.spoc_name
        drive.spoc_email = request.spoc_email
        drive.status = "SPOC_ASSIGNED"
        
        db.commit()
        db.refresh(drive)
        
        # Dispatch email to the newly assigned SPOC
        draft = generate_spoc_assignment_email(request.spoc_name, drive.company_name, drive.hr_email)
        
        target_company = db.query(Company).filter(Company.company_name == drive.company_name).first()
        company_id_link = target_company.id if target_company else None
        
        ext_success = send_email(request.spoc_email, f"URGENT: SPOC Assignment - {drive.company_name}", draft, company_id_link, db)
        
        orchestrator.log_event(
            db=db, actor="USER", action="SPOC_ASSIGNED",
            details=f"SPOC {request.spoc_name} ({request.spoc_email}) bound to {drive.company_name}",
            drive_id=drive.id
        )
        return {
            "success": True,
            "message": f"Assigned SPOC {request.spoc_name} successfully" + (" and email dispatched." if ext_success else " but email dispatch failed."),
            "data": drive
        }
    except SQLAlchemyError as e:
        logger.error(f"DB error assigning SPOC: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal DB exception")

@router.patch("/confirm-drive/{id}", response_model=StandardResponse[RecruitmentDriveResponse])
def confirm_recruitment_drive(id: int, db: Session = Depends(get_db)):
    """Mark a drive as DRIVE_CONFIRMED — triggers SPOC assignment step."""
    try:
        drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == id).first()
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")

        drive.status = "DRIVE_CONFIRMED"
        db.commit()
        db.refresh(drive)

        orchestrator.log_event(
            db=db, actor="ORCHESTRATOR", action="DRIVE_CONFIRMED",
            details=f"HR confirmed the recruitment drive for {drive.company_name}. SPOC assignment is now required.",
            drive_id=drive.id
        )
        return {"success": True, "message": "Drive marked as confirmed. Assign a SPOC to proceed.", "data": drive}
    except SQLAlchemyError as e:
        logger.error(f"DB error confirming drive: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal DB error")
