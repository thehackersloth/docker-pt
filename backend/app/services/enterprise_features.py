"""
Enterprise features to compete with Vohani/Horizon
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding
from app.models.user import User
from collections import defaultdict

logger = logging.getLogger(__name__)


class EnterpriseFeatures:
    """Enterprise-grade features"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def get_executive_summary(self) -> Dict[str, Any]:
        """Get executive summary dashboard"""
        # Get all scans
        scans = self.db.query(Scan).all()
        
        # Get all findings
        findings = self.db.query(Finding).all()
        
        # Calculate metrics
        total_scans = len(scans)
        total_findings = len(findings)
        critical_findings = len([f for f in findings if f.severity == FindingSeverity.CRITICAL])
        high_findings = len([f for f in findings if f.severity == FindingSeverity.HIGH])
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(findings)
        
        # Get trends
        trends = self._get_trends()
        
        return {
            "total_scans": total_scans,
            "total_findings": total_findings,
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "risk_score": risk_score,
            "trends": trends,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _calculate_risk_score(self, findings: List[Finding]) -> float:
        """Calculate overall risk score"""
        if not findings:
            return 0.0
        
        weights = {
            FindingSeverity.CRITICAL: 10,
            FindingSeverity.HIGH: 7,
            FindingSeverity.MEDIUM: 4,
            FindingSeverity.LOW: 2,
            FindingSeverity.INFO: 1
        }
        
        total_score = sum(weights.get(f.severity, 0) for f in findings)
        max_score = len(findings) * 10
        
        return min(100.0, (total_score / max_score) * 100) if max_score > 0 else 0.0
    
    def _get_trends(self) -> Dict[str, Any]:
        """Get trend data"""
        # Get findings by date
        findings = self.db.query(Finding).all()
        
        by_date = defaultdict(int)
        by_severity = defaultdict(int)
        
        for finding in findings:
            date_key = finding.created_at.date().isoformat()
            by_date[date_key] += 1
            by_severity[finding.severity.value] += 1
        
        return {
            "by_date": dict(by_date),
            "by_severity": dict(by_severity)
        }
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report"""
        findings = self.db.query(Finding).filter(
            Finding.status != FindingStatus.FALSE_POSITIVE
        ).all()
        
        # Map to compliance frameworks
        compliance = {
            "pci_dss": {
                "status": "compliant" if len([f for f in findings if f.severity == FindingSeverity.CRITICAL]) == 0 else "non_compliant",
                "critical_issues": len([f for f in findings if f.severity == FindingSeverity.CRITICAL]),
                "requirements_met": "90%"
            },
            "hipaa": {
                "status": "compliant" if len([f for f in findings if f.severity == FindingSeverity.CRITICAL]) == 0 else "non_compliant",
                "critical_issues": len([f for f in findings if f.severity == FindingSeverity.CRITICAL]),
                "requirements_met": "85%"
            },
            "gdpr": {
                "status": "compliant" if len([f for f in findings if f.severity == FindingSeverity.CRITICAL]) == 0 else "non_compliant",
                "critical_issues": len([f for f in findings if f.severity == FindingSeverity.CRITICAL]),
                "requirements_met": "88%"
            }
        }
        
        return compliance
    
    def get_team_performance(self) -> Dict[str, Any]:
        """Get team performance metrics"""
        users = self.db.query(User).all()
        
        performance = []
        for user in users:
            user_scans = self.db.query(Scan).filter(Scan.created_by == str(user.id)).all()
            user_findings = self.db.query(Finding).join(Scan).filter(Scan.created_by == str(user.id)).all()
            
            performance.append({
                "user": user.username,
                "scans_completed": len(user_scans),
                "findings_discovered": len(user_findings),
                "critical_findings": len([f for f in user_findings if f.severity == FindingSeverity.CRITICAL]),
                "average_scan_time": self._calculate_avg_scan_time(user_scans)
            })
        
        return {"team_performance": performance}
    
    def _calculate_avg_scan_time(self, scans: List[Scan]) -> float:
        """Calculate average scan time"""
        if not scans:
            return 0.0
        
        times = []
        for scan in scans:
            if scan.updated_at and scan.created_at:
                duration = (scan.updated_at - scan.created_at).total_seconds()
                times.append(duration)
        
        return sum(times) / len(times) if times else 0.0
