import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from backend.database.db import get_db
from backend.database.models import Company, EmailLog
from backend.schemas.company_schema import CompanyCreate, CompanyUpdate, CompanyResponse, EmailLogResponse
from backend.schemas.recruitment_schema import StandardResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/company", tags=["company"])

@router.post("/create", response_model=StandardResponse[CompanyResponse])
def create_company(company_data: CompanyCreate, db: Session = Depends(get_db)):
    try:
        new_company = Company(**company_data.model_dump())
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        logger.info(f"Created new company '{new_company.company_name}' in database")
        return {"success": True, "message": "Company created successfully", "data": new_company}
    except SQLAlchemyError as e:
        logger.error(f"Database error during company creation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/all", response_model=StandardResponse[List[CompanyResponse]])
def get_all_companies(db: Session = Depends(get_db)):
    try:
        companies = db.query(Company).all()
        return {"success": True, "message": "Fetched all companies", "data": companies}
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching companies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{id}", response_model=StandardResponse[CompanyResponse])
def get_company(id: int, db: Session = Depends(get_db)):
    try:
        company = db.query(Company).filter(Company.id == id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        return {"success": True, "message": "Fetched company successfully", "data": company}
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching company #{id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{id}", response_model=StandardResponse[CompanyResponse])
def update_company(id: int, company_data: CompanyUpdate, db: Session = Depends(get_db)):
    try:
        company = db.query(Company).filter(Company.id == id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        update_dict = company_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(company, key, value)
            
        db.commit()
        db.refresh(company)
        logger.info(f"Updated company '{company.company_name}'")
        return {"success": True, "message": "Company updated successfully", "data": company}
    except SQLAlchemyError as e:
        logger.error(f"Database error updating company #{id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{id}", response_model=StandardResponse[dict])
def delete_company(id: int, db: Session = Depends(get_db)):
    try:
        company = db.query(Company).filter(Company.id == id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        db.delete(company)
        db.commit()
        logger.info(f"Deleted company #{id}")
        return {"success": True, "message": "Company deleted successfully", "data": None}
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting company #{id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{id}/emails", response_model=StandardResponse[List[EmailLogResponse]])
def get_company_emails(id: int, db: Session = Depends(get_db)):
    try:
        # Check if exists
        company = db.query(Company).filter(Company.id == id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
            
        emails = db.query(EmailLog).filter(EmailLog.company_id == id).order_by(EmailLog.timestamp.desc()).all()
        return {"success": True, "message": "Fetched company emails securely", "data": emails}
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching emails for company #{id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
