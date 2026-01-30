"""
Full automation endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.models.scan import Scan, ScanStatus
from app.services.automation_engine import AutomationEngine

router = APIRouter()


class AutomationRequest(BaseModel):
    scan_id: str
    auto_exploit: bool = True
    auto_report: bool = True
    auto_analyze: bool = True


@router.post("/scan/{scan_id}/full-automation")
async def start_full_automation(
    scan_id: str,
    background_tasks: BackgroundTasks,
    auto_exploit: bool = True,
    auto_report: bool = True,
    auto_analyze: bool = True,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Start full automation for a scan"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan.status == ScanStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Scan is already running")
    
    # Start automation in background
    def run_automation():
        engine = AutomationEngine(scan_id)
        engine.automate_full_workflow()
    
    background_tasks.add_task(run_automation)
    
    return {
        "message": "Full automation started",
        "scan_id": scan_id,
        "status": "running",
        "automation_features": {
            "auto_exploit": auto_exploit,
            "auto_report": auto_report,
            "auto_analyze": auto_analyze
        }
    }


@router.post("/scan/{scan_id}/auto-phase/{phase}")
async def automate_phase(
    scan_id: str,
    phase: str,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Automate a specific phase"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    engine = AutomationEngine(scan_id)
    
    # Get phases
    from app.services.methodology_service import MethodologyService
    methodology = MethodologyService()
    phases = methodology.get_scan_phases(scan.scan_type)
    
    # Find matching phase
    phase_data = next((p for p in phases if p['phase'].lower() == phase.lower()), None)
    if not phase_data:
        raise HTTPException(status_code=404, detail=f"Phase {phase} not found")
    
    # Execute phase
    result = engine._automate_phase(phase_data)
    
    return {
        "phase": phase,
        "results": result
    }


@router.get("/scan/{scan_id}/automation-status")
async def get_automation_status(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get automation status for a scan"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    from app.models.finding import Finding
    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
    
    return {
        "scan_id": scan_id,
        "status": scan.status.value,
        "findings_count": len(findings),
        "automation_enabled": True,
        "phases_completed": scan.status == ScanStatus.COMPLETED
    }


@router.post("/enable-full-auto")
async def enable_full_automation(
    current_user: User = Depends(require_admin)
):
    """Enable full automation mode globally"""
    # This would update global config
    return {
        "message": "Full automation enabled",
        "features": {
            "auto_methodology": True,
            "auto_tool_selection": True,
            "auto_execution": True,
            "auto_exploitation": True,
            "auto_analysis": True,
            "auto_reporting": True,
            "auto_next_steps": True
        }
    }
