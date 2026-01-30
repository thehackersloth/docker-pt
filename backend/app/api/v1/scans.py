"""
Scan management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
from app.core.database import SessionLocal, get_db
from app.models.scan import Scan, ScanStatus, ScanType
from app.tasks.scan_tasks import execute_scan_task
from app.services.scan_safety import ScanSafetyService
from app.core.security import get_current_user
from app.models.user import User
from sqlalchemy.orm import Session

router = APIRouter()


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanType(str, Enum):
    NETWORK = "network"
    WEB = "web"
    AD = "ad"
    FULL = "full"


class ScanCreate(BaseModel):
    name: str
    scan_type: ScanType
    targets: List[str]
    description: Optional[str] = None


class ScanResponse(BaseModel):
    id: str
    name: str
    scan_type: ScanType
    status: ScanStatus
    targets: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan: ScanCreate,
    auto_start: bool = True,
    full_automation: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new scan"""
    # Safety validation
    safety_service = ScanSafetyService()
    is_valid, msg = safety_service.validate_scan_request(
        scan.targets,
        scan.scan_type.value,
        str(current_user.id)
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # Create scan record
    db_scan = Scan(
        name=scan.name,
        description=scan.description,
        scan_type=ScanType(scan.scan_type),
        status=ScanStatus.PENDING,
        targets=scan.targets,
        created_by=str(current_user.id),
    )
    db.add(db_scan)
    db.commit()
    db.refresh(db_scan)

    # Auto-start scan execution via Celery
    if auto_start:
        from app.tasks.scan_tasks import execute_full_pentest_task, execute_scan_task
        if full_automation:
            # Full penetration test workflow
            execute_full_pentest_task.delay(str(db_scan.id))
        else:
            # Standard scan execution (recon only)
            execute_scan_task.delay(str(db_scan.id))
    
    return ScanResponse(
        id=str(db_scan.id),
        name=db_scan.name,
        scan_type=db_scan.scan_type.value,
        status=db_scan.status.value,
        targets=db_scan.targets,
        created_at=db_scan.created_at,
        updated_at=db_scan.updated_at,
    )


@router.get("", response_model=List[ScanResponse])
async def list_scans(skip: int = 0, limit: int = 100, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all scans"""
    scans = db.query(Scan).offset(skip).limit(limit).all()
    return [
        ScanResponse(
            id=str(scan.id),
            name=scan.name,
            scan_type=scan.scan_type.value,
            status=scan.status.value,
            targets=scan.targets,
            created_at=scan.created_at,
            updated_at=scan.updated_at,
        )
        for scan in scans
    ]


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get scan by ID"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return ScanResponse(
        id=str(scan.id),
        name=scan.name,
        scan_type=scan.scan_type.value,
        status=scan.status.value,
        targets=scan.targets,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


@router.post("/{scan_id}/start")
async def start_scan(scan_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start a scan"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.status != ScanStatus.PENDING:
        raise HTTPException(status_code=400, detail="Scan is not in pending status")
    
    # Start scan execution
    execute_scan_task.delay(scan_id)
    
    return {"message": "Scan started", "scan_id": scan_id}


@router.post("/{scan_id}/cancel")
async def cancel_scan(scan_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cancel a scan"""
    from app.tasks.scan_tasks import cancel_scan_task

    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    cancel_scan_task.delay(scan_id)

    return {"message": "Scan cancellation requested", "scan_id": scan_id}


@router.get("/{scan_id}/logs")
async def get_scan_logs(scan_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get scan output logs (for live terminal view)"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    return {
        "scan_id": scan_id,
        "status": scan.status.value if scan.status else "unknown",
        "progress": scan.progress_percent or 0,
        "logs": scan.output_log or "",
        "started_at": scan.started_at.isoformat() if scan.started_at else None,
        "error": scan.error_message
    }
