import logging
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database.db import get_db
from backend.database.models import RecruitmentDrive
from backend.services.gmail_reader import read_latest_emails
from backend.services.llm_service import parse_email_content
from backend.services.approval import create_approval
from backend.schemas.recruitment_schema import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"])

class EmailProcessRequest(BaseModel):
    email_index: int

@router.post("/process", response_model=StandardResponse[dict])
def process_email_action(req: EmailProcessRequest, db: Session = Depends(get_db)):
    emails = read_latest_emails()
    
    if req.email_index < 0 or req.email_index >= len(emails):
        raise HTTPException(status_code=400, detail="Invalid email index")
        
    target_email = emails[req.email_index]
    
    # Safely extract actual HR email string if formatted as: "Name <email@domain.com>"
    sender = target_email.get('sender', '')
    match = re.search(r'<([^>]+)>', sender)
    hr_email_address = match.group(1).strip() if match else sender.strip()
    
    # Locate matching deployment drive
    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.hr_email.ilike(hr_email_address)).first()
    
    if not drive:
        raise HTTPException(status_code=404, detail="No recruitment drive matches this HR email address")
        
    # Process unstructured email with Groq
    parsed_data = parse_email_content(target_email['snippet'])
    
    # Ensure human-in-the-loop by packing the requested intent into the Action string implicitly
    # Format ensures we can still track exactly what is occurring without altering DB tables.
    action_key = f"PROCESS_HR_RESPONSE|{parsed_data.get('intent', 'UNKNOWN')}"
    
    approval = create_approval(drive.id, action_key, db)
    logger.info(f"Generated Approval ticket #{approval.id} evaluating HR response to {drive.company_name}")
    
    return {
        "success": True,
        "message": "Awaiting human approval",
        "data": {
            "email": target_email,
            "parsed": parsed_data,
            "approval_id": approval.id
        }
    }
