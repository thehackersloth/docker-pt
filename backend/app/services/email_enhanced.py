"""
AI-enhanced email service
"""

import logging
from typing import List, Dict, Any
from app.services.email_service import EmailService
from app.services.ai_service import AIService
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding, FindingSeverity

logger = logging.getLogger(__name__)


class EnhancedEmailService(EmailService):
    """Email service with AI enhancement"""
    
    def __init__(self):
        super().__init__()
        self.ai_service = AIService()
    
    def generate_ai_summary(self, scan_id: str) -> str:
        """Generate AI-powered email summary"""
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                return "Scan not found"
            
            findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
            
            prompt = f"""
            Generate a concise email summary for a penetration test scan completion.
            
            Scan: {scan.name}
            Status: {scan.status.value}
            Total Findings: {len(findings)}
            Critical: {sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)}
            High: {sum(1 for f in findings if f.severity == FindingSeverity.HIGH)}
            Medium: {sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)}
            Low: {sum(1 for f in findings if f.severity == FindingSeverity.LOW)}
            
            Create a professional, concise email summary suitable for executives and technical teams.
            Highlight critical findings and immediate action items.
            """
            
            summary = self.ai_service.generate_text(prompt)
            return summary or "Scan completed. Please review the attached report for details."
            
        except Exception as e:
            logger.error(f"Failed to generate AI summary: {e}")
            return "Scan completed. Please review the attached report."
        finally:
            db.close()
    
    def send_enhanced_scan_report(
        self,
        scan_id: str,
        recipients: List[str],
        use_ai: bool = True
    ) -> bool:
        """Send AI-enhanced scan report email"""
        from app.core.config import settings

        if not settings.SMTP_ENABLED:
            logger.warning("SMTP is disabled, cannot send email")
            return False

        try:
            # Generate AI summary if enabled
            if use_ai:
                summary = self.generate_ai_summary(scan_id)
            else:
                summary = "Scan completed. Please review the attached report for details."

            # Get scan details for email
            db = SessionLocal()
            try:
                scan = db.query(Scan).filter(Scan.id == scan_id).first()
                scan_name = scan.name if scan else scan_id
                findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()

                critical_count = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
                high_count = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)
                medium_count = sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)
                low_count = sum(1 for f in findings if f.severity == FindingSeverity.LOW)
            finally:
                db.close()

            # Build enhanced email body
            body = f"""
Professional Pentesting Platform - Scan Report

Scan: {scan_name}
Scan ID: {scan_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY
{summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINDINGS OVERVIEW
  🔴 Critical: {critical_count}
  🟠 High: {high_count}
  🟡 Medium: {medium_count}
  🟢 Low: {low_count}
  ━━━━━━━━━━━━━━━━━
  Total: {len(findings)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please review the attached reports for detailed findings and remediation recommendations.

This is an automated message from the Professional Pentesting Platform.
            """

            # Send with attachments
            success = self.send_email(
                to=recipients,
                subject=f"[Pentest Report] {scan_name} - {critical_count} Critical, {high_count} High Findings",
                body=body
            )

            # Also send with report attachments
            if success:
                return self.send_scan_report(scan_id, recipients, ["pdf", "html"])

            return success

        except Exception as e:
            logger.error(f"Failed to send enhanced scan report: {e}")
            return False
