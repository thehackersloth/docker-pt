"""
Data management endpoints (retention, deletion, export)
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional
from app.core.database import SessionLocal, get_db
from app.core.security import require_admin, get_current_user
from app.models.user import User
from app.services.data_retention import DataRetentionService

router = APIRouter()
retention_service = DataRetentionService()


class RetentionConfig(BaseModel):
    scan_retention_days: int = 90
    report_retention_days: int = 90
    audit_retention_days: int = 365
    auto_delete_enabled: bool = False


@router.post("/retention/delete-old-scans")
async def delete_old_scans(
    days: Optional[int] = None,
    current_user: User = Depends(require_admin)
):
    """Delete scans older than retention period"""
    result = retention_service.delete_old_scans(days)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.post("/retention/delete-old-reports")
async def delete_old_reports(
    days: Optional[int] = None,
    current_user: User = Depends(require_admin)
):
    """Delete reports older than retention period"""
    result = retention_service.delete_old_reports(days)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.post("/user/{user_id}/delete")
async def delete_user_data(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete all user data (GDPR right to deletion)"""
    # Users can only delete their own data, or admins can delete any
    if str(current_user.id) != user_id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own data"
        )
    
    result = retention_service.secure_delete_user_data(user_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.get("/user/{user_id}/export")
async def export_user_data(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Export all user data (GDPR data export)"""
    # Users can only export their own data, or admins can export any
    if str(current_user.id) != user_id and current_user.role.value != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only export your own data"
        )
    
    data = retention_service.export_user_data(user_id)
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return data
