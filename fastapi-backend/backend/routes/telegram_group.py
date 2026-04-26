import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from backend.database.db import get_db
from backend.database.models import TelegramGroup, RecruitmentDrive, Company
from backend.services.orchestrator import orchestrator
from backend.schemas.recruitment_schema import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramGroupResponse(BaseModel):
    id: int
    company_id: int
    drive_id: Optional[int] = None
    chat_id: str
    group_name: str
    invite_link: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BroadcastRequest(BaseModel):
    invite_link: str
    company_name: str
    custom_message: Optional[str] = None


class PostToGroupRequest(BaseModel):
    chat_id: str
    message: str


@router.post("/create-group/{drive_id}", response_model=StandardResponse[TelegramGroupResponse])
def create_telegram_group_for_drive(drive_id: int, db: Session = Depends(get_db)):
    """
    Creates a dedicated Telegram supergroup for a confirmed recruitment drive.
    Requires telegram_session.session to exist (run setup_telegram_session.py first).
    """
    # Import here to avoid boot failures if session not yet set up
    from backend.services.telegram_group_service import create_company_telegram_group

    drive = db.query(RecruitmentDrive).filter(RecruitmentDrive.id == drive_id).first()
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")

    company = db.query(Company).filter(Company.company_name == drive.company_name).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company record not found for this drive")

    # Check if group already exists
    existing = db.query(TelegramGroup).filter(
        TelegramGroup.drive_id == drive_id,
        TelegramGroup.is_active == True
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Telegram group already exists for this drive: {existing.group_name}"
        )

    try:
        drive_date_str = None
        # Check if there is a logistics entry to get the drive date
        from backend.database.models import DriveLogistics
        logistics = db.query(DriveLogistics).filter(
            DriveLogistics.company_id == company.id
        ).order_by(DriveLogistics.drive_date.desc()).first()
        if logistics:
            drive_date_str = logistics.drive_date.strftime("%b %Y")

        result = create_company_telegram_group(drive.company_name, drive_date_str)

        # Persist to DB
        tg_group = TelegramGroup(
            company_id=company.id,
            drive_id=drive_id,
            chat_id=result["chat_id"],
            group_name=result["group_name"],
            invite_link=result["invite_link"],
        )
        db.add(tg_group)
        db.commit()
        db.refresh(tg_group)

        orchestrator.log_event(
            db=db, actor="SYSTEM", action="TELEGRAM_GROUP_CREATED",
            details=f"Created Telegram group '{result['group_name']}' (chat_id={result['chat_id']}) for {drive.company_name}. Invite: {result['invite_link']}",
            drive_id=drive_id, company_id=company.id
        )

        logger.info(f"Telegram group created for drive {drive_id}: {result['group_name']}")
        return {"success": True, "message": f"Telegram group '{result['group_name']}' created successfully!", "data": tg_group}

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e) + " Run 'python setup_telegram_session.py' to authenticate."
        )
    except Exception as e:
        logger.error(f"Failed to create Telegram group: {e}")
        raise HTTPException(status_code=500, detail=f"Group creation failed: {str(e)}")


@router.post("/broadcast-invite", response_model=StandardResponse[dict])
def broadcast_invite(req: BroadcastRequest, db: Session = Depends(get_db)):
    """Broadcasts the group invite link to the main student Telegram channel."""
    from backend.services.telegram_group_service import broadcast_invite_to_main_channel
    success = broadcast_invite_to_main_channel(req.invite_link, req.company_name, req.custom_message)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to broadcast invite to main channel")
    return {"success": True, "message": "Invite broadcasted to main student channel!", "data": {"invite_link": req.invite_link}}


@router.post("/post-to-group", response_model=StandardResponse[dict])
def post_to_group(req: PostToGroupRequest):
    """Posts a message to a specific company drive's Telegram group."""
    from backend.services.telegram_group_service import post_to_company_group
    success = post_to_company_group(req.chat_id, req.message)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to post to group")
    return {"success": True, "message": "Message posted to Telegram group!", "data": None}


@router.get("/group/{drive_id}", response_model=StandardResponse[TelegramGroupResponse])
def get_group_for_drive(drive_id: int, db: Session = Depends(get_db)):
    """Returns the Telegram group details for a given drive (if exists)."""
    group = db.query(TelegramGroup).filter(
        TelegramGroup.drive_id == drive_id,
        TelegramGroup.is_active == True
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="No active Telegram group found for this drive")
    return {"success": True, "message": "Group found", "data": group}


@router.get("/groups/all", response_model=StandardResponse[List[TelegramGroupResponse]])
def get_all_groups(db: Session = Depends(get_db)):
    """Returns all active Telegram groups."""
    groups = db.query(TelegramGroup).filter(TelegramGroup.is_active == True).all()
    return {"success": True, "message": f"{len(groups)} active groups", "data": groups}
