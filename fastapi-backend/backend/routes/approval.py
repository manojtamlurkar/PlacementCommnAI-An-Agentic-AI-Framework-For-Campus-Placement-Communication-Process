import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from backend.database.db import get_db
from backend.schemas.approval_schema import ApprovalCreate, ApprovalActionRequest, ApprovalResponse
from backend.schemas.recruitment_schema import StandardResponse
from backend.services.approval import create_approval, get_pending_approvals, handle_action

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/approval",
    tags=["approval"]
)

@router.post("/request", response_model=StandardResponse[ApprovalResponse])
def create_approval_request(appr: ApprovalCreate, db: Session = Depends(get_db)):
    try:
        approval = create_approval(appr.recruitment_id, appr.action, db)
        logger.info(f"Approval explicitly created for recruitment {appr.recruitment_id}")
        return {"success": True, "message": "Approval request created successfully", "data": approval}
    except SQLAlchemyError as e:
        logger.error(f"Database error during approval creation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/pending", response_model=StandardResponse[List[ApprovalResponse]])
def get_pending_approvals_route(db: Session = Depends(get_db)):
    try:
        approvals = get_pending_approvals(db)
        return {"success": True, "message": "Pending approvals fetched", "data": approvals}
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/action", response_model=StandardResponse[ApprovalResponse])
def perform_approval_action(req: ApprovalActionRequest, db: Session = Depends(get_db)):
    if req.action not in ["APPROVE", "REJECT"]:
        raise HTTPException(status_code=400, detail="Invalid action. Must be 'APPROVE' or 'REJECT'.")
        
    try:
        approval = handle_action(req.approval_id, req.action, db)
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        logger.info(f"Approval {req.approval_id} processed with action {req.action}")
        return {"success": True, "message": f"Approval {req.action.lower()}d successfully", "data": approval}
    except SQLAlchemyError as e:
        logger.error(f"Database error during approval action: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
