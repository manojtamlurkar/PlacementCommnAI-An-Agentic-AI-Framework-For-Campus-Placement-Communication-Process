from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    company_name: str
    email: EmailStr
    priority: Optional[str] = None
    description: Optional[str] = None

    poc_name: Optional[str] = None
    poc_phone: Optional[str] = None
    poc_email: Optional[EmailStr] = None

    alternate_poc_name: Optional[str] = None
    alternate_poc_phone: Optional[str] = None
    alternate_poc_email: Optional[EmailStr] = None

    location: Optional[str] = None
    address: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(CompanyBase):
    company_name: Optional[str] = None
    email: Optional[EmailStr] = None

class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class EmailLogResponse(BaseModel):
    id: int
    company_id: int
    direction: str
    subject: str
    body: str
    timestamp: datetime

    class Config:
        from_attributes = True
