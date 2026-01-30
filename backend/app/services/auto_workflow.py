"""
Automatic workflow progression service
"""

import logging
from typing import Dict, Any, List
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.services.automation_engine import AutomationEngine

logger = logging.getLogger(__name__)


class AutoWorkflowService:
    """Automatic workflow progression"""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def auto_progress_scan(self, scan_id: str) -> Dict[str, Any]:
        """Automatically progress scan through phases"""
        scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            return {"error": "Scan not found"}
        
        # Check current phase completion
        findings = self.db.query(Finding).filter(Finding.scan_id == scan_id).all()
        
        # Auto-determine next phase
        next_phase = self._determine_next_phase(scan, findings)
        
        if next_phase:
            # Auto-execute next phase
            engine = AutomationEngine(scan_id)
            result = engine._automate_phase(next_phase)
            return {
                "phase_completed": next_phase['phase'],
                "results": result
            }
        
        return {"message": "All phases completed"}
    
    def _determine_next_phase(self, scan: Scan, findings: List[Finding]) -> Dict[str, Any]:
        """Determine next phase to execute"""
        from app.services.methodology_service import MethodologyService
        methodology = MethodologyService()
        phases = methodology.get_scan_phases(scan.scan_type)
        
        # Check which phases have findings
        phases_with_findings = set()
        for finding in findings:
            # Extract phase from finding description
            for phase in phases:
                if phase['phase'].lower() in (finding.description or '').lower():
                    phases_with_findings.add(phase['phase'])
        
        # Find first phase without findings
        for phase in phases:
            if phase['phase'] not in phases_with_findings:
                return phase
        
        return None
    
    def auto_chain_scans(self, initial_scan_id: str) -> List[str]:
        """Automatically chain scans based on findings"""
        scan = self.db.query(Scan).filter(Scan.id == initial_scan_id).first()
        if not scan:
            return []
        
        findings = self.db.query(Finding).filter(Finding.scan_id == initial_scan_id).all()
        
        chained_scans = []
        
        # Auto-create follow-up scans based on findings
        for finding in findings:
            if finding.severity == FindingSeverity.CRITICAL:
                # Create deep dive scan
                followup_scan = Scan(
                    name=f"Deep Dive: {finding.title}",
                    description=f"Automated follow-up scan for {finding.title}",
                    scan_type=scan.scan_type,
                    status=ScanStatus.PENDING,
                    targets=[finding.target] if finding.target else scan.targets,
                    created_by=scan.created_by
                )
                self.db.add(followup_scan)
                chained_scans.append(str(followup_scan.id))
        
        self.db.commit()
        return chained_scans
