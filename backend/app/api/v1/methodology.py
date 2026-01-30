"""
Methodology endpoints based on Offensive Security PDFs
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.scan import Scan, ScanType
from app.models.finding import Finding
from app.services.methodology_service import MethodologyService

router = APIRouter()
methodology_service = MethodologyService()


@router.get("/phases")
async def get_scan_phases(
    scan_type: ScanType = Query(..., description="Type of scan"),
    current_user: User = Depends(get_current_user)
):
    """Get recommended phases for scan type based on methodology"""
    phases = methodology_service.get_scan_phases(scan_type)
    return {
        "scan_type": scan_type.value,
        "phases": phases,
        "methodology_sources": list(methodology_service.methodologies.keys())
    }


@router.get("/scan/{scan_id}/apply")
async def apply_methodology_to_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Apply methodology to a specific scan"""
    result = methodology_service.apply_methodology_to_scan(scan_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/finding/{finding_id}/exploitation")
async def get_exploitation_workflow(
    finding_id: str,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get exploitation workflow for a finding"""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    workflow = methodology_service.get_exploitation_workflow(finding)
    return workflow


@router.get("/tool/{tool}/command")
async def get_tool_command(
    tool: str,
    phase: str = Query(..., description="Phase of pentest"),
    target: str = Query(..., description="Target IP/URL"),
    current_user: User = Depends(get_current_user)
):
    """Get recommended command for tool based on methodology"""
    command = methodology_service.get_tool_command(tool, phase, target)
    if not command:
        raise HTTPException(status_code=404, detail=f"No command found for {tool} in {phase} phase")
    return {
        "tool": tool,
        "phase": phase,
        "target": target,
        "command": command
    }


@router.get("/sources")
async def get_methodology_sources(
    current_user: User = Depends(get_current_user)
):
    """Get list of loaded methodology sources"""
    return {
        "sources": list(methodology_service.methodologies.keys()),
        "count": len(methodology_service.methodologies)
    }


@router.get("/reload")
async def reload_methodologies(
    current_user: User = Depends(get_current_user)
):
    """Reload methodologies from PDFs"""
    methodology_service._load_methodologies()
    return {
        "message": "Methodologies reloaded",
        "sources": list(methodology_service.methodologies.keys())
    }
