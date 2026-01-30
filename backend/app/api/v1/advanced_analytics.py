"""
Advanced analytics endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.services.advanced_analytics import AdvancedAnalyticsService

router = APIRouter()
analytics_service = AdvancedAnalyticsService()


@router.get("/risk-score")
async def get_risk_score(
    scan_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: SessionLocal = Depends(get_db)
):
    """Get risk score for a scan or overall"""
    from app.models.finding import Finding
    from app.models.scan import Scan
    
    if scan_id:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
    else:
        findings = db.query(Finding).filter(
            Finding.status != FindingStatus.FALSE_POSITIVE
        ).all()
    
    risk_score = analytics_service.calculate_risk_score(findings)
    
    return {
        "risk_score": round(risk_score, 2),
        "finding_count": len(findings),
        "scan_id": scan_id
    }


@router.get("/trends")
async def get_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user)
):
    """Get vulnerability trends"""
    trends = analytics_service.get_vulnerability_trends(days=days)
    return trends


@router.get("/severity-distribution")
async def get_severity_distribution(
    current_user: User = Depends(get_current_user)
):
    """Get distribution of findings by severity"""
    distribution = analytics_service.get_severity_distribution()
    return {"distribution": distribution}


@router.get("/top-vulnerabilities")
async def get_top_vulnerabilities(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """Get top vulnerabilities by occurrence"""
    top_vulns = analytics_service.get_top_vulnerabilities(limit=limit)
    return {"vulnerabilities": top_vulns}


@router.get("/asset-risk")
async def get_asset_risk_analysis(
    current_user: User = Depends(require_admin)
):
    """Get risk analysis by asset"""
    asset_risks = analytics_service.get_asset_risk_analysis()
    return {"assets": asset_risks}


@router.get("/scan-statistics")
async def get_scan_statistics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user)
):
    """Get scan statistics"""
    stats = analytics_service.get_scan_statistics(days=days)
    return stats


@router.get("/compliance-score")
async def get_compliance_score(
    current_user: User = Depends(get_current_user)
):
    """Get compliance score"""
    compliance = analytics_service.get_compliance_score()
    return compliance


@router.get("/executive-dashboard")
async def get_executive_dashboard(
    current_user: User = Depends(require_admin)
):
    """Get executive dashboard summary"""
    dashboard = analytics_service.get_executive_dashboard()
    return dashboard


@router.get("/risk-timeline")
async def get_risk_timeline(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user)
):
    """Get risk score timeline"""
    db = SessionLocal()
    try:
        from app.models.finding import Finding, FindingStatus
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get findings by date
        findings_by_date = db.query(
            func.date(Finding.created_at).label('date'),
            Finding.severity
        ).filter(
            Finding.created_at >= cutoff_date,
            Finding.status != FindingStatus.FALSE_POSITIVE
        ).all()
        
        # Calculate risk score per day
        daily_risks = defaultdict(list)
        for date, severity in findings_by_date:
            daily_risks[date.isoformat()].append(severity)
        
        timeline = []
        for date_str, severities in sorted(daily_risks.items()):
            # Convert to Finding objects for risk calculation
            from app.models.finding import FindingSeverity
            findings = [
                type('Finding', (), {'severity': s, 'status': FindingStatus.OPEN})()
                for s in severities
            ]
            risk_score = analytics_service.calculate_risk_score(findings)
            timeline.append({
                "date": date_str,
                "risk_score": round(risk_score, 2),
                "finding_count": len(severities)
            })
        
        return {"timeline": timeline}
    finally:
        db.close()
