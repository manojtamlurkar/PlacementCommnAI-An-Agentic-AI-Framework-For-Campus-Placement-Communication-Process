import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database.db import get_db
from backend.database.models import StudentQuestion, RecruitmentDrive, Company
from backend.schemas.recruitment_schema import StandardResponse
from backend.services.llm_service import draft_questions_to_hr
from backend.services.email_service import send_email
from backend.services.orchestrator import orchestrator
from backend.services.telegram_group_service import post_to_company_group

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spoc", tags=["spoc"])

class StudentQuestionResponse(BaseModel):
    id: int
    company_id: int
    drive_id: Optional[int]
    telegram_user: str
    question_text: str
    status: str
    auto_answer: Optional[str]
    hr_answer: Optional[str]
    created_at: datetime
    answered_at: Optional[datetime]

    class Config:
        from_attributes = True

class ForwardQuestionsRequest(BaseModel):
    question_ids: List[int]

class AnswerQuestionRequest(BaseModel):
    answer: str

@router.get("/{drive_id}/questions", response_model=StandardResponse[List[StudentQuestionResponse]])
def get_student_questions(drive_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Fetch student questions for a specific drive, optionally filtering by status."""
    query = db.query(StudentQuestion).filter(StudentQuestion.drive_id == drive_id)
    if status:
        query = query.filter(StudentQuestion.status == status)
    
    questions = query.order_by(StudentQuestion.created_at.desc()).all()
    return {"success": True, "message": "Questions retrieved", "data": questions}


@router.post("/{drive_id}/forward-to-hr")
def forward_questions_to_hr(drive_id: int, req: ForwardQuestionsRequest, db: Session = Depends(get_db)):
    """Drafts and sends an email to HR with the selected escalated questions."""
    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == drive_id).first()
    if not drive or not drive.spoc_name:
        raise HTTPException(status_code=400, detail="Drive or SPOC not found")

    company = db.query(Company).filter(Company.company_name == drive.company_name).first()
    if not company:
        raise HTTPException(status_code=400, detail="Company not found")

    questions = db.query(StudentQuestion).filter(StudentQuestion.id.in_(req.question_ids)).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No valid questions selected")

    q_texts = [q.question_text for q in questions]
    
    # Draft email via LLM
    draft = draft_questions_to_hr(
        questions_list=q_texts,
        company_name=company.company_name,
        poc_name=company.poc_name,
        spoc_name=drive.spoc_name
    )

    # Send email
    subject = f"Clarifications Required - {company.company_name} Campus Drive"
    success = send_email(company.email, subject, draft, company.id, db)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email to HR")

    # Update question statuses
    for q in questions:
        q.status = "FORWARDED_TO_HR"
    db.commit()

    orchestrator.log_event(
        db=db, actor="SPOC", action="QUESTIONS_ESCALATED",
        details=f"SPOC forwarded {len(questions)} student questions to HR",
        drive_id=drive_id, company_id=company.id
    )

    return {"success": True, "message": "Questions successfully forwarded to HR", "data": None}


@router.post("/{drive_id}/answer-question/{q_id}")
def manually_answer_question(drive_id: int, q_id: int, req: AnswerQuestionRequest, db: Session = Depends(get_db)):
    """SPOC manually answers a question. Posts the answer back to the Telegram group."""
    question = db.query(StudentQuestion).filter(StudentQuestion.id == q_id, StudentQuestion.drive_id == drive_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    from backend.database.models import TelegramGroup
    tg_group = db.query(TelegramGroup).filter(TelegramGroup.drive_id == drive_id).first()
    if not tg_group:
        raise HTTPException(status_code=400, detail="No Telegram group found for this drive")

    question.hr_answer = req.answer
    question.status = "HR_ANSWERED"
    question.answered_at = datetime.utcnow()
    db.commit()

    # Post reply to Telegram group
    reply_text = f"@{question.telegram_user} Update regarding your query ('{question.question_text[:30]}...'):\n\n{req.answer}"
    post_to_company_group(tg_group.chat_id, reply_text)

    orchestrator.log_event(
        db=db, actor="SPOC", action="QUESTION_ANSWERED",
        details=f"SPOC manually answered a student question",
        drive_id=drive_id
    )

    return {"success": True, "message": "Answer posted to Telegram group", "data": None}
