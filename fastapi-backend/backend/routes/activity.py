import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database.db import get_db
from backend.database.models import ActivityLog, RecruitmentDrive
from backend.services.orchestrator import orchestrator
from backend.schemas.recruitment_schema import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityLogResponse(BaseModel):
    id: int
    drive_id: Optional[int] = None
    company_id: Optional[int] = None
    actor: str
    action: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


@router.get("/{drive_id}", response_model=StandardResponse[List[ActivityLogResponse]])
def get_drive_activity(drive_id: int, db: Session = Depends(get_db)):
    """Return the full chronological activity timeline for a recruitment drive."""
    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.drive_id == drive_id)
        .order_by(ActivityLog.timestamp.asc())
        .all()
    )
    return {"success": True, "message": f"Activity log for drive {drive_id}", "data": logs}


@router.get("/company/{company_id}", response_model=StandardResponse[List[ActivityLogResponse]])
def get_company_activity(company_id: int, db: Session = Depends(get_db)):
    """Return all activity for a specific company (across drives)."""
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.company_id == company_id)
        .order_by(ActivityLog.timestamp.asc())
        .all()
    )
    return {"success": True, "message": f"Activity log for company {company_id}", "data": logs}


@router.post("/check-stale", response_model=StandardResponse[dict])
def trigger_stale_check(db: Session = Depends(get_db)):
    """Manually trigger the orchestrator stale-drive scan."""
    stale_ids = orchestrator.check_stale_drives(db)
    return {
        "success": True,
        "message": f"Stale scan complete. {len(stale_ids)} drive(s) flagged.",
        "data": {"stale_drive_ids": stale_ids}
    }
