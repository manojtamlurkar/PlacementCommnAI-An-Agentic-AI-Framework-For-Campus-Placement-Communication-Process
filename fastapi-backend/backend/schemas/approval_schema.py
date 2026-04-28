from pydantic import BaseModel
from typing import Optional

class ApprovalBase(BaseModel):
    recruitment_id: int
    action: str
    status: Optional[str] = "PENDING"
    payload: Optional[str] = None

class ApprovalCreate(BaseModel):
    recruitment_id: int
    action: str
    payload: Optional[str] = None

class ApprovalActionRequest(BaseModel):
    approval_id: int
    action: str  # "APPROVE" or "REJECT"
    updated_payload: Optional[str] = None

class ApprovalResponse(ApprovalBase):
    id: int

    class Config:
        from_attributes = True
