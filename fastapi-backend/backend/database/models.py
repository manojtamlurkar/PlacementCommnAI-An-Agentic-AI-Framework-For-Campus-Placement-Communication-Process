from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean
from datetime import datetime
from backend.database.db import Base

class RecruitmentDrive(Base):
    __tablename__ = "recruitment_drive"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True)
    hr_email = Column(String)
    status = Column(String)
    spoc_name = Column(String, nullable=True)
    spoc_email = Column(String, nullable=True)

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    recruitment_id = Column(Integer, ForeignKey("recruitment_drive.id"))
    action = Column(String)
    status = Column(String, default="PENDING")

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True, nullable=False)
    email = Column(String, nullable=False)
    priority = Column(String)
    description = Column(Text)

    poc_name = Column(String)
    poc_phone = Column(String)
    poc_email = Column(String)

    alternate_poc_name = Column(String)
    alternate_poc_phone = Column(String)
    alternate_poc_email = Column(String)

    location = Column(String)
    address = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    direction = Column(String, nullable=False) # "SENT" or "RECEIVED"
    subject = Column(String)
    body = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    building = Column(String)
    capacity = Column(Integer, nullable=False)
    has_projector = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DriveLogistics(Base):
    __tablename__ = "drive_logistics"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    drive_date = Column(DateTime, nullable=False)
    student_count = Column(Integer, nullable=False)
    status = Column(String, default="PENDING")  # PENDING / CONFIRMED / MANUAL_OVERRIDE_NEEDED
    registration_link = Column(String)
    followup_questions = Column(Text)  # JSON array of strings
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    drive_id = Column(Integer, ForeignKey("recruitment_drive.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    actor = Column(String, nullable=False)  # ORCHESTRATOR / SPOC / AGENT / SYSTEM / USER
    action = Column(String, nullable=False)  # EMAIL_SENT, SPOC_ASSIGNED, DRIVE_CONFIRMED, etc.
    details = Column(Text)                   # Human-readable description
    timestamp = Column(DateTime, default=datetime.utcnow)

class TelegramGroup(Base):
    __tablename__ = "telegram_groups"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    drive_id = Column(Integer, ForeignKey("recruitment_drive.id"), nullable=True)
    chat_id = Column(String, nullable=False)
    group_name = Column(String, nullable=False)
    invite_link = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class StudentQuestion(Base):
    __tablename__ = "student_questions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    drive_id = Column(Integer, ForeignKey("recruitment_drive.id"), nullable=True)
    telegram_user = Column(String)            # Display name of user who asked
    telegram_user_id = Column(String)         # Telegram numeric user ID
    question_text = Column(Text, nullable=False)
    status = Column(String, default="PENDING")  # PENDING / AUTO_ANSWERED / ESCALATED / FORWARDED_TO_HR / HR_ANSWERED
    auto_answer = Column(Text, nullable=True)    # LLM auto-generated answer (if confident)
    hr_answer = Column(Text, nullable=True)      # HR's response after forwarding
    message_id = Column(String, nullable=True)   # Telegram message_id for threading
    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)


