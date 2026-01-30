"""
Dashboard statistics and metrics endpoints
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.core.database import SessionLocal, get_db
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.asset import Asset
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter()


class DashboardStats(BaseModel):
    total_scans: int
    running_scans: int
    completed_scans: int
    failed_scans: int
    total_findings: int
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    total_assets: int
    recent_scans: list
    top_vulnerabilities: list


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    # Scan statistics
    total_scans = db.query(Scan).count()
    running_scans = db.query(Scan).filter(Scan.status == ScanStatus.RUNNING).count()
    completed_scans = db.query(Scan).filter(Scan.status == ScanStatus.COMPLETED).count()
    failed_scans = db.query(Scan).filter(Scan.status == ScanStatus.FAILED).count()
    
    # Finding statistics
    total_findings = db.query(Finding).count()
    critical_findings = db.query(Finding).filter(Finding.severity == FindingSeverity.CRITICAL).count()
    high_findings = db.query(Finding).filter(Finding.severity == FindingSeverity.HIGH).count()
    medium_findings = db.query(Finding).filter(Finding.severity == FindingSeverity.MEDIUM).count()
    low_findings = db.query(Finding).filter(Finding.severity == FindingSeverity.LOW).count()
    
    # Asset statistics
    total_assets = db.query(Asset).count()
    
    # Recent scans
    recent_scans = db.query(Scan).order_by(Scan.created_at.desc()).limit(5).all()
    recent_scans_data = [
        {
            "id": str(s.id),
            "name": s.name,
            "status": s.status.value,
            "created_at": s.created_at.isoformat(),
            "findings_count": s.findings_count,
        }
        for s in recent_scans
    ]
    
    # Top vulnerabilities (by count)
    top_vulns = db.query(
        Finding.cve_id,
        func.count(Finding.id).label('count')
    ).filter(
        Finding.cve_id.isnot(None)
    ).group_by(
        Finding.cve_id
    ).order_by(
        func.count(Finding.id).desc()
    ).limit(10).all()
    
    top_vulnerabilities = [
        {"cve_id": v[0], "count": v[1]}
        for v in top_vulns
    ]
    
    return DashboardStats(
        total_scans=total_scans,
        running_scans=running_scans,
        completed_scans=completed_scans,
        failed_scans=failed_scans,
        total_findings=total_findings,
        critical_findings=critical_findings,
        high_findings=high_findings,
        medium_findings=medium_findings,
        low_findings=low_findings,
        total_assets=total_assets,
        recent_scans=recent_scans_data,
        top_vulnerabilities=top_vulnerabilities,
    )


@router.get("/trends")
async def get_trends(days: int = 30, db: Session = Depends(get_db)):
    """Get trends over time"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Scans over time
    scans_by_day = db.query(
        func.date(Scan.created_at).label('date'),
        func.count(Scan.id).label('count')
    ).filter(
        Scan.created_at >= start_date
    ).group_by(
        func.date(Scan.created_at)
    ).all()
    
    # Findings over time
    findings_by_day = db.query(
        func.date(Finding.created_at).label('date'),
        func.count(Finding.id).label('count')
    ).filter(
        Finding.created_at >= start_date
    ).group_by(
        func.date(Finding.created_at)
    ).all()
    
    return {
        "scans": [{"date": str(s[0]), "count": s[1]} for s in scans_by_day],
        "findings": [{"date": str(f[0]), "count": f[1]} for f in findings_by_day],
    }
