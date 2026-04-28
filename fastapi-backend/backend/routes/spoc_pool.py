"""
SPOC Pool Management API
-------------------------
CRUD endpoints for managing the pool of available SPOCs
that the autonomous agent draws from when assigning coordinators to drives.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database.db import get_db
from backend.database.models import SpocPool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spoc-pool", tags=["spoc-pool"])


class SpocPoolCreate(BaseModel):
    name: str
    email: str

class SpocPoolResponse(BaseModel):
    id: int
    name: str
    email: str
    is_available: bool
    active_drives: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/add", response_model=SpocPoolResponse)
def add_spoc(req: SpocPoolCreate, db: Session = Depends(get_db)):
    """Add a new SPOC to the available pool."""
    existing = db.query(SpocPool).filter(SpocPool.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="SPOC with this email already exists")

    spoc = SpocPool(name=req.name, email=req.email)
    db.add(spoc)
    db.commit()
    db.refresh(spoc)
    logger.info(f"Added SPOC to pool: {spoc.name} ({spoc.email})")
    return spoc


@router.get("/list", response_model=List[SpocPoolResponse])
def list_spocs(db: Session = Depends(get_db)):
    """List all SPOCs in the pool."""
    return db.query(SpocPool).order_by(SpocPool.active_drives.asc()).all()


@router.delete("/{spoc_id}")
def remove_spoc(spoc_id: int, db: Session = Depends(get_db)):
    """Remove a SPOC from the pool."""
    spoc = db.query(SpocPool).filter(SpocPool.id == spoc_id).first()
    if not spoc:
        raise HTTPException(status_code=404, detail="SPOC not found")
    db.delete(spoc)
    db.commit()
    return {"success": True, "message": f"Removed SPOC {spoc.name}"}


@router.patch("/{spoc_id}/toggle")
def toggle_spoc_availability(spoc_id: int, db: Session = Depends(get_db)):
    """Toggle a SPOC's availability."""
    spoc = db.query(SpocPool).filter(SpocPool.id == spoc_id).first()
    if not spoc:
        raise HTTPException(status_code=404, detail="SPOC not found")
    spoc.is_available = not spoc.is_available
    db.commit()
    return {"success": True, "message": f"{spoc.name} is now {'available' if spoc.is_available else 'unavailable'}"}
