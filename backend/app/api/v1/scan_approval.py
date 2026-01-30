"""
Scan approval workflow endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.scan import Scan, ScanStatus
from app.models.scan_approval import ScanApproval, ApprovalStatus
from sqlalchemy.orm import Session

router = APIRouter()


class ApprovalRequest(BaseModel):
    scan_id: str
    reason: Optional[str] = None
    expires_in_hours: int = 24


class ApprovalResponse(BaseModel):
    id: str
    scan_id: str
    status: str
    requested_by: str
    approved_by: Optional[str]
    reason: Optional[str]
    requested_at: datetime
    approved_at: Optional[datetime]


@router.post("/request")
async def request_approval(
    request: ApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Request approval for a scan"""
    # Get scan
    scan = db.query(Scan).filter(Scan.id == request.scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Check if already approved
    existing = db.query(ScanApproval).filter(
        ScanApproval.scan_id == request.scan_id
    ).first()
    
    if existing and existing.status == ApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Scan is already approved"
        )
    
    # Create approval request
    approval = ScanApproval(
        scan_id=request.scan_id,
        requested_by=str(current_user.id),
        status=ApprovalStatus.PENDING,
        reason=request.reason,
        expires_at=datetime.utcnow() + timedelta(hours=request.expires_in_hours)
    )
    
    db.add(approval)
    db.commit()
    db.refresh(approval)
    
    return ApprovalResponse(
        id=str(approval.id),
        scan_id=str(approval.scan_id),
        status=approval.status.value,
        requested_by=str(approval.requested_by),
        approved_by=str(approval.approved_by) if approval.approved_by else None,
        reason=approval.reason,
        requested_at=approval.requested_at,
        approved_at=approval.approved_at
    )


@router.post("/{approval_id}/approve")
async def approve_scan(
    approval_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Approve a scan"""
    approval = db.query(ScanApproval).filter(ScanApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval is not pending")
    
    if approval.expires_at and datetime.utcnow() > approval.expires_at:
        approval.status = ApprovalStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="Approval request has expired")
    
    # Approve
    approval.status = ApprovalStatus.APPROVED
    approval.approved_by = str(current_user.id)
    approval.approved_at = datetime.utcnow()
    
    # Update scan status
    scan = db.query(Scan).filter(Scan.id == approval.scan_id).first()
    if scan:
        scan.status = ScanStatus.PENDING  # Ready to run
    
    db.commit()
    
    return {"message": "Scan approved", "approval_id": approval_id}


@router.post("/{approval_id}/reject")
async def reject_scan(
    approval_id: str,
    reason: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reject a scan"""
    approval = db.query(ScanApproval).filter(ScanApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval is not pending")
    
    # Reject
    approval.status = ApprovalStatus.REJECTED
    approval.approved_by = str(current_user.id)
    approval.rejection_reason = reason
    
    db.commit()
    
    return {"message": "Scan rejected", "approval_id": approval_id}


@router.get("/pending", response_model=List[ApprovalResponse])
async def list_pending_approvals(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List pending approval requests"""
    approvals = db.query(ScanApproval).filter(
        ScanApproval.status == ApprovalStatus.PENDING
    ).order_by(ScanApproval.requested_at.desc()).all()
    
    return [
        ApprovalResponse(
            id=str(a.id),
            scan_id=str(a.scan_id),
            status=a.status.value,
            requested_by=str(a.requested_by),
            approved_by=str(a.approved_by) if a.approved_by else None,
            reason=a.reason,
            requested_at=a.requested_at,
            approved_at=a.approved_at
        )
        for a in approvals
    ]
