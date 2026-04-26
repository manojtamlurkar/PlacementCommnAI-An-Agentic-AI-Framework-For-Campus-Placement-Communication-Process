from pydantic import BaseModel
from typing import Optional

class ApprovalBase(BaseModel):
    recruitment_id: int
    action: str
    status: Optional[str] = "PENDING"

class ApprovalCreate(BaseModel):
    recruitment_id: int
    action: str

class ApprovalActionRequest(BaseModel):
    approval_id: int
    action: str  # "APPROVE" or "REJECT"

class ApprovalResponse(ApprovalBase):
    id: int

    class Config:
        from_attributes = True
