from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ClassroomBase(BaseModel):
    name: str
    building: Optional[str] = None
    capacity: int
    has_projector: bool = True

class ClassroomCreate(ClassroomBase):
    pass

class ClassroomResponse(ClassroomBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LogisticsCreate(BaseModel):
    company_id: int
    drive_date: datetime
    student_count: int
    registration_link: Optional[str] = None

class LogisticsResponse(BaseModel):
    id: int
    company_id: int
    classroom_id: Optional[int] = None
    drive_date: datetime
    student_count: int
    status: str
    registration_link: Optional[str] = None
    followup_questions: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FollowUpQuestionsUpdate(BaseModel):
    questions: List[str]
