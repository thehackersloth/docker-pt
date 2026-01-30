"""
Backup management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from app.core.backup_service import BackupService
from app.core.security import require_admin
from app.models.user import User

router = APIRouter()
backup_service = BackupService()


class BackupResponse(BaseModel):
    timestamp: str
    postgres: Optional[str]
    neo4j: Optional[str]
    data: Optional[str]
    success: bool


@router.post("/full", response_model=BackupResponse)
async def create_full_backup(current_user: User = Depends(require_admin)):
    """Create full backup (admin only)"""
    results = backup_service.full_backup()
    return BackupResponse(**results)


@router.post("/postgres")
async def backup_postgres(current_user: User = Depends(require_admin)):
    """Backup PostgreSQL database"""
    backup_file = backup_service.backup_postgres()
    if not backup_file:
        raise HTTPException(status_code=500, detail="Backup failed")
    return {"success": True, "backup_file": backup_file}


@router.post("/neo4j")
async def backup_neo4j(current_user: User = Depends(require_admin)):
    """Backup Neo4j database"""
    backup_file = backup_service.backup_neo4j()
    if not backup_file:
        raise HTTPException(status_code=500, detail="Backup failed")
    return {"success": True, "backup_file": backup_file}


@router.post("/data")
async def backup_data(current_user: User = Depends(require_admin)):
    """Backup application data"""
    backup_file = backup_service.backup_data()
    if not backup_file:
        raise HTTPException(status_code=500, detail="Backup failed")
    return {"success": True, "backup_file": backup_file}
