"""
Advanced analytics service
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.asset import Asset, AssetCriticality
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AdvancedAnalyticsService:
    """Advanced analytics and reporting service"""
    
    def __init__(self):
        self.severity_weights = {
            FindingSeverity.CRITICAL: 10,
            FindingSeverity.HIGH: 7,
            FindingSeverity.MEDIUM: 4,
            FindingSeverity.LOW: 2,
            FindingSeverity.INFO: 1
        }
    
    def calculate_risk_score(self, findings: List[Finding]) -> float:
        """Calculate overall risk score from findings"""
        if not findings:
            return 0.0
        
        total_score = 0.0
        for finding in findings:
            weight = self.severity_weights.get(finding.severity, 0)
            # Adjust for status
            if finding.status == FindingStatus.FIXED:
                weight *= 0.1
            elif finding.status == FindingStatus.FALSE_POSITIVE:
                weight = 0
            elif finding.status == FindingStatus.ACCEPTED:
                weight *= 0.5
            
            total_score += weight
        
        # Normalize to 0-100 scale
        max_possible = len(findings) * 10
        return min(100.0, (total_score / max_possible) * 100) if max_possible > 0 else 0.0
    
    def get_vulnerability_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get vulnerability trends over time"""
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get findings by date and severity
            findings = db.query(
                func.date(Finding.created_at).label('date'),
                Finding.severity,
                func.count(Finding.id).label('count')
            ).filter(
                Finding.created_at >= cutoff_date
            ).group_by(
                func.date(Finding.created_at),
                Finding.severity
            ).all()
            
            # Organize by date
            trends = defaultdict(lambda: defaultdict(int))
            for date, severity, count in findings:
                trends[date.isoformat()][severity.value] = count
            
            return {
                "period_days": days,
                "trends": dict(trends)
            }
        finally:
            db.close()
    
    def get_severity_distribution(self) -> Dict[str, int]:
        """Get distribution of findings by severity"""
        db = SessionLocal()
        try:
            findings = db.query(
                Finding.severity,
                func.count(Finding.id).label('count')
            ).filter(
                Finding.status != FindingStatus.FALSE_POSITIVE
            ).group_by(Finding.severity).all()
            
            distribution = {severity.value: 0 for severity in FindingSeverity}
            for severity, count in findings:
                distribution[severity.value] = count
            
            return distribution
        finally:
            db.close()
    
    def get_top_vulnerabilities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top vulnerabilities by occurrence"""
        db = SessionLocal()
        try:
            findings = db.query(
                Finding.title,
                Finding.cve_id,
                Finding.severity,
                func.count(Finding.id).label('count')
            ).filter(
                Finding.status != FindingStatus.FALSE_POSITIVE
            ).group_by(
                Finding.title,
                Finding.cve_id,
                Finding.severity
            ).order_by(
                func.count(Finding.id).desc()
            ).limit(limit).all()
            
            return [
                {
                    "title": title,
                    "cve_id": cve_id,
                    "severity": severity.value,
                    "count": count
                }
                for title, cve_id, severity, count in findings
            ]
        finally:
            db.close()
    
    def get_asset_risk_analysis(self) -> List[Dict[str, Any]]:
        """Get risk analysis by asset"""
        db = SessionLocal()
        try:
            # Get assets with their findings
            assets = db.query(Asset).all()
            
            asset_risks = []
            for asset in assets:
                findings = db.query(Finding).filter(
                    Finding.target == asset.ip_address
                ).all()
                
                risk_score = self.calculate_risk_score(findings)
                
                asset_risks.append({
                    "asset_id": str(asset.id),
                    "ip_address": asset.ip_address,
                    "hostname": asset.hostname,
                    "criticality": asset.criticality.value if asset.criticality else "unknown",
                    "risk_score": risk_score,
                    "finding_count": len(findings),
                    "critical_count": len([f for f in findings if f.severity == FindingSeverity.CRITICAL]),
                    "high_count": len([f for f in findings if f.severity == FindingSeverity.HIGH])
                })
            
            # Sort by risk score
            asset_risks.sort(key=lambda x: x['risk_score'], reverse=True)
            
            return asset_risks
        finally:
            db.close()
    
    def get_scan_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get scan statistics"""
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Total scans
            total_scans = db.query(func.count(Scan.id)).filter(
                Scan.created_at >= cutoff_date
            ).scalar()
            
            # Scans by status
            scans_by_status = db.query(
                Scan.status,
                func.count(Scan.id).label('count')
            ).filter(
                Scan.created_at >= cutoff_date
            ).group_by(Scan.status).all()
            
            # Scans by type
            scans_by_type = db.query(
                Scan.scan_type,
                func.count(Scan.id).label('count')
            ).filter(
                Scan.created_at >= cutoff_date
            ).group_by(Scan.scan_type).all()
            
            # Average scan duration
            completed_scans = db.query(Scan).filter(
                Scan.created_at >= cutoff_date,
                Scan.status == ScanStatus.COMPLETED
            ).all()
            
            avg_duration = 0
            if completed_scans:
                durations = []
                for scan in completed_scans:
                    if scan.updated_at and scan.created_at:
                        duration = (scan.updated_at - scan.created_at).total_seconds()
                        durations.append(duration)
                if durations:
                    avg_duration = sum(durations) / len(durations)
            
            return {
                "period_days": days,
                "total_scans": total_scans,
                "scans_by_status": {status.value: count for status, count in scans_by_status},
                "scans_by_type": {scan_type.value: count for scan_type, count in scans_by_type},
                "average_duration_seconds": avg_duration
            }
        finally:
            db.close()
    
    def get_compliance_score(self) -> Dict[str, Any]:
        """Calculate compliance score based on findings"""
        db = SessionLocal()
        try:
            # Get all active findings
            findings = db.query(Finding).filter(
                Finding.status.in_([
                    FindingStatus.OPEN,
                    FindingStatus.CONFIRMED
                ])
            ).all()
            
            total_findings = len(findings)
            critical_findings = len([f for f in findings if f.severity == FindingSeverity.CRITICAL])
            high_findings = len([f for f in findings if f.severity == FindingSeverity.HIGH])
            
            # Calculate compliance score (0-100)
            # Start at 100, deduct points for findings
            score = 100.0
            score -= critical_findings * 10  # -10 per critical
            score -= high_findings * 5  # -5 per high
            score -= (total_findings - critical_findings - high_findings) * 1  # -1 per other
            
            score = max(0.0, min(100.0, score))
            
            # Determine compliance level
            if score >= 90:
                level = "excellent"
            elif score >= 75:
                level = "good"
            elif score >= 50:
                level = "fair"
            else:
                level = "poor"
            
            return {
                "score": round(score, 2),
                "level": level,
                "total_findings": total_findings,
                "critical_findings": critical_findings,
                "high_findings": high_findings
            }
        finally:
            db.close()
    
    def get_executive_dashboard(self) -> Dict[str, Any]:
        """Get executive dashboard summary"""
        db = SessionLocal()
        try:
            # Overall risk score
            all_findings = db.query(Finding).filter(
                Finding.status != FindingStatus.FALSE_POSITIVE
            ).all()
            overall_risk = self.calculate_risk_score(all_findings)
            
            # Compliance score
            compliance = self.get_compliance_score()
            
            # Recent trends
            trends = self.get_vulnerability_trends(days=7)
            
            # Top vulnerabilities
            top_vulns = self.get_top_vulnerabilities(limit=5)
            
            # Asset risks
            asset_risks = self.get_asset_risk_analysis()
            top_risky_assets = asset_risks[:5]
            
            return {
                "overall_risk_score": round(overall_risk, 2),
                "compliance": compliance,
                "recent_trends": trends,
                "top_vulnerabilities": top_vulns,
                "top_risky_assets": top_risky_assets,
                "generated_at": datetime.utcnow().isoformat()
            }
        finally:
            db.close()
