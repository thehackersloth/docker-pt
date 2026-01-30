"""
Finding management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
from app.core.database import SessionLocal, get_db
from app.models.finding import Finding, FindingStatus, FindingSeverity
from sqlalchemy.orm import Session

router = APIRouter()


class FindingResponse(BaseModel):
    id: str
    scan_id: str
    title: str
    description: str
    severity: str
    status: str
    target: str
    port: Optional[str]
    service: Optional[str]
    cve_id: Optional[str]
    cvss_score: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FindingUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    comments: Optional[List[dict]] = None
    tags: Optional[List[str]] = None


@router.get("", response_model=List[FindingResponse])
async def list_findings(
    scan_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List findings with filters"""
    query = db.query(Finding)
    
    if scan_id:
        query = query.filter(Finding.scan_id == scan_id)
    if severity:
        query = query.filter(Finding.severity == FindingSeverity(severity))
    if status:
        query = query.filter(Finding.status == FindingStatus(status))
    
    findings = query.offset(skip).limit(limit).all()
    
    return [
        FindingResponse(
            id=str(f.id),
            scan_id=str(f.scan_id),
            title=f.title,
            description=f.description,
            severity=f.severity.value,
            status=f.status.value,
            target=f.target,
            port=f.port,
            service=f.service,
            cve_id=f.cve_id,
            cvss_score=f.cvss_score,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )
        for f in findings
    ]


@router.get("/{finding_id}", response_model=FindingResponse)
async def get_finding(finding_id: str, db: Session = Depends(get_db)):
    """Get finding by ID"""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    return FindingResponse(
        id=str(finding.id),
        scan_id=str(finding.scan_id),
        title=finding.title,
        description=finding.description,
        severity=finding.severity.value,
        status=finding.status.value,
        target=finding.target,
        port=finding.port,
        service=finding.service,
        cve_id=finding.cve_id,
        cvss_score=finding.cvss_score,
        created_at=finding.created_at,
        updated_at=finding.updated_at,
    )


@router.put("/{finding_id}", response_model=FindingResponse)
async def update_finding(
    finding_id: str,
    update: FindingUpdate,
    db: Session = Depends(get_db)
):
    """Update finding"""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    if update.status:
        finding.status = FindingStatus(update.status)
    if update.assigned_to:
        finding.assigned_to = update.assigned_to
    if update.comments:
        finding.comments = update.comments
    if update.tags:
        finding.tags = update.tags
    
    db.commit()
    db.refresh(finding)
    
    return FindingResponse(
        id=str(finding.id),
        scan_id=str(finding.scan_id),
        title=finding.title,
        description=finding.description,
        severity=finding.severity.value,
        status=finding.status.value,
        target=finding.target,
        port=finding.port,
        service=finding.service,
        cve_id=finding.cve_id,
        cvss_score=finding.cvss_score,
        created_at=finding.created_at,
        updated_at=finding.updated_at,
    )
