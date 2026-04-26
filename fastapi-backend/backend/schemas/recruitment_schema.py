from pydantic import BaseModel, EmailStr
from typing import Optional, Generic, TypeVar, Any

T = TypeVar('T')

class StandardResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

class RecruitmentDriveBase(BaseModel):
    company_name: str
    hr_email: EmailStr   # strict validation on input
    status: str

class RecruitmentDriveCreate(RecruitmentDriveBase):
    pass

class RecruitmentDriveUpdateStatus(BaseModel):
    status: str

class RecruitmentDriveResponse(BaseModel):
    """Response schema uses plain str for hr_email so existing DB records
    with non-standard addresses (e.g. 'hr@microsoft') don't crash serialization."""
    id: int
    company_name: str
    hr_email: str        # relaxed — read-only, no re-validation
    status: str
    spoc_name: Optional[str] = None
    spoc_email: Optional[str] = None

    class Config:
        from_attributes = True

class AssignSpocRequest(BaseModel):
    spoc_name: str
    spoc_email: str
