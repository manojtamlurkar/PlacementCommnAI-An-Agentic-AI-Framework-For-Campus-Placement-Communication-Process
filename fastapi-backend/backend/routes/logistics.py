import logging
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from backend.database.db import get_db
from backend.database.models import Classroom, DriveLogistics, Company, RecruitmentDrive, EmailLog
from backend.schemas.logistics_schema import ClassroomCreate, ClassroomResponse, LogisticsCreate, LogisticsResponse, FollowUpQuestionsUpdate
from backend.schemas.recruitment_schema import StandardResponse
from backend.services.llm_service import generate_telegram_drive_message, generate_followup_questions_email
from backend.services.telegram_service import send_telegram_draft

logger = logging.getLogger(__name__)

router = APIRouter(tags=["logistics"])

# --- CLASSROOM ROUTES ---

@router.post("/classroom/create", response_model=StandardResponse[ClassroomResponse])
def create_classroom(room: ClassroomCreate, db: Session = Depends(get_db)):
    try:
        db_room = Classroom(**room.model_dump())
        db.add(db_room)
        db.commit()
        db.refresh(db_room)
        return {"success": True, "message": "Classroom added recursively", "data": db_room}
    except SQLAlchemyError as e:
        logger.error(f"DB Error creating classroom: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal DB error")

@router.get("/classroom/all", response_model=StandardResponse[List[ClassroomResponse]])
def get_all_classrooms(db: Session = Depends(get_db)):
    rooms = db.query(Classroom).all()
    return {"success": True, "message": "Fetched all classrooms", "data": rooms}

@router.delete("/classroom/{id}", response_model=StandardResponse[dict])
def delete_classroom(id: int, db: Session = Depends(get_db)):
    room = db.query(Classroom).filter(Classroom.id == id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Classroom not found")
    db.delete(room)
    db.commit()
    return {"success": True, "message": "Classroom removed", "data": None}


# --- LOGISTICS ROUTES ---

@router.post("/logistics/create", response_model=StandardResponse[LogisticsResponse])
def create_logistics(logistics: LogisticsCreate, db: Session = Depends(get_db)):
    """Creates logistics entry and auto-assigns the best-fit available classroom."""
    try:
        # Avoid duplicate drive configs for same company + date
        existing = db.query(DriveLogistics).filter(
            DriveLogistics.company_id == logistics.company_id,
            DriveLogistics.drive_date == logistics.drive_date
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Logistics for this company on this date already exists.")
            
        # 1. Find classrooms with capacity >= student_count
        capable_rooms = db.query(Classroom).filter(Classroom.capacity >= logistics.student_count).all()
        
        # 2. Exclude booked rooms
        booked_logistics = db.query(DriveLogistics).filter(
            DriveLogistics.drive_date == logistics.drive_date,
            DriveLogistics.classroom_id != None
        ).all()
        booked_room_ids = {bl.classroom_id for bl in booked_logistics}
        available_rooms = [r for r in capable_rooms if r.id not in booked_room_ids]
        
        # 3. Best fit (smallest room that fits)
        assigned_room_id = None
        status = "MANUAL_OVERRIDE_NEEDED"
        if available_rooms:
            # Sort by capacity ascending
            best_room = sorted(available_rooms, key=lambda x: x.capacity)[0]
            assigned_room_id = best_room.id
            status = "CONFIRMED"
            
        new_log = DriveLogistics(
            company_id=logistics.company_id,
            drive_date=logistics.drive_date,
            student_count=logistics.student_count,
            registration_link=logistics.registration_link,
            classroom_id=assigned_room_id,
            status=status
        )
        db.add(new_log)
        
        # Update recruitment drive status automatically
        company = db.query(Company).filter(Company.id == logistics.company_id).first()
        if company:
            drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.company_name == company.company_name).first()
            if drive:
                drive.status = "LOGISTICS_CONFIRMED"
                
        db.commit()
        db.refresh(new_log)
        return {"success": True, "message": f"Logistics created. Status: {status}", "data": new_log}
    except SQLAlchemyError as e:
        logger.error(f"DB error logistics creation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal error")

@router.get("/logistics/{company_id}", response_model=StandardResponse[List[LogisticsResponse]])
def get_logistics_for_company(company_id: int, db: Session = Depends(get_db)):
    logs = db.query(DriveLogistics).filter(DriveLogistics.company_id == company_id).order_by(DriveLogistics.drive_date.desc()).all()
    return {"success": True, "message": "Fetched logistics", "data": logs}

@router.put("/logistics/{id}/followup-questions", response_model=StandardResponse[LogisticsResponse])
def update_followup_questions(id: int, req: FollowUpQuestionsUpdate, db: Session = Depends(get_db)):
    log = db.query(DriveLogistics).filter(DriveLogistics.id == id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Logistics not found")
        
    log.followup_questions = json.dumps(req.questions)
    db.commit()
    db.refresh(log)
    return {"success": True, "message": "Questions updated", "data": log}


# --- DRAFTS & COMMUNICATION FLOW ---

from pydantic import BaseModel
class TelegramDraftRequest(BaseModel):
    logistics_id: int

class TelegramSendRequest(BaseModel):
    message: str

class FollowupEmailDraftRequest(BaseModel):
    logistics_id: int

@router.post("/logistics/telegram-draft")
def generate_telegram_draft_route(req: TelegramDraftRequest, db: Session = Depends(get_db)):
    log = db.query(DriveLogistics).filter(DriveLogistics.id == req.logistics_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Logistics entry not found")
        
    company = db.query(Company).filter(Company.id == log.company_id).first()
    room_name = "TBA"
    if log.classroom_id:
        room = db.query(Classroom).filter(Classroom.id == log.classroom_id).first()
        room_name = room.name if room else "TBA"
        
    questions = json.loads(log.followup_questions) if log.followup_questions else []
    
    date_str = log.drive_date.strftime("%B %d, %Y")
    draft = generate_telegram_drive_message(
        company_name=company.company_name,
        drive_date=date_str,
        classroom_name=room_name,
        registration_link=log.registration_link,
        followup_questions=questions
    )
    return {"success": True, "draft": draft}

@router.post("/logistics/telegram-send")
def send_telegram_route(req: TelegramSendRequest):
    success = send_telegram_draft(req.message)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send Telegram message.")
    return {"success": True, "message": "Broadcasted out via Telegram!"}

@router.post("/logistics/followup-email-draft")
def generate_followup_email_route(req: FollowupEmailDraftRequest, db: Session = Depends(get_db)):
    log = db.query(DriveLogistics).filter(DriveLogistics.id == req.logistics_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Logistics entry not found")
        
    company = db.query(Company).filter(Company.id == log.company_id).first()
    questions = json.loads(log.followup_questions) if log.followup_questions else []
    
    if not questions:
        raise HTTPException(status_code=400, detail="There are zero follow-up questions tied to this node right now.")
        
    history_records = db.query(EmailLog).filter(EmailLog.company_id == company.id).order_by(EmailLog.timestamp.asc()).all()
    email_history = [{
        "direction": r.direction,
        "subject": r.subject or "",
        "body": r.body or "",
        "timestamp": str(r.timestamp)
    } for r in history_records]
    
    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.company_name == company.company_name).first()
    spoc_name = drive.spoc_name if drive else None
    
    draft = generate_followup_questions_email(company.company_name, company.poc_name, questions, email_history, spoc_name)
    return {"success": True, "draft": draft}
