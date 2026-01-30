"""
Advanced email features (conditional sending, scheduling, analytics)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.services.email_service import EmailService
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding, FindingSeverity
from app.models.schedule import Schedule

logger = logging.getLogger(__name__)


class AdvancedEmailService(EmailService):
    """Advanced email features"""
    
    def should_send_email(self, scan_id: str, conditions: Dict[str, Any]) -> bool:
        """Determine if email should be sent based on conditions"""
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                return False
            
            findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
            
            # Check conditions
            if conditions.get("only_if_critical") and scan.critical_count == 0:
                return False
            
            if conditions.get("only_if_high_or_critical"):
                if scan.critical_count == 0 and scan.high_count == 0:
                    return False
            
            if conditions.get("min_findings"):
                if len(findings) < conditions["min_findings"]:
                    return False
            
            if conditions.get("severity_threshold"):
                threshold = FindingSeverity(conditions["severity_threshold"])
                if threshold == FindingSeverity.CRITICAL and scan.critical_count == 0:
                    return False
                elif threshold == FindingSeverity.HIGH and scan.critical_count == 0 and scan.high_count == 0:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking email conditions: {e}")
            return True  # Default to sending
        finally:
            db.close()
    
    def schedule_email(
        self,
        scan_id: str,
        recipients: List[str],
        send_at: datetime,
        report_formats: List[str] = ["pdf"]
    ) -> bool:
        """Schedule email to be sent at specific time"""
        # Store in database or task queue
        # For now, use Celery's ETA feature
        from app.tasks.email_tasks import send_scan_report_email
        
        # Calculate delay
        now = datetime.utcnow()
        delay_seconds = (send_at - now).total_seconds()
        
        if delay_seconds > 0:
            send_scan_report_email.apply_async(
                args=[scan_id, recipients, report_formats],
                countdown=int(delay_seconds)
            )
            return True
        
        return False
    
    def send_batch_emails(
        self,
        scan_ids: List[str],
        recipients: List[str],
        report_formats: List[str] = ["pdf"]
    ) -> Dict[str, bool]:
        """Send emails for multiple scans"""
        results = {}
        
        for scan_id in scan_ids:
            try:
                success = self.send_scan_report(scan_id, recipients, report_formats)
                results[scan_id] = success
            except Exception as e:
                logger.error(f"Failed to send email for scan {scan_id}: {e}")
                results[scan_id] = False
        
        return results
    
    def get_email_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get email delivery analytics"""
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Get reports with email tracking
            from app.models.report import Report
            reports = db.query(Report).filter(
                Report.email_sent == True,
                Report.email_sent_at >= cutoff_date
            ).all()
            
            total_sent = len(reports)
            successful = sum(1 for r in reports if r.email_sent)
            
            # Group by day
            by_day = {}
            for report in reports:
                day = report.email_sent_at.date()
                if day not in by_day:
                    by_day[day] = {"sent": 0, "successful": 0}
                by_day[day]["sent"] += 1
                if report.email_sent:
                    by_day[day]["successful"] += 1
            
            return {
                "total_sent": total_sent,
                "successful": successful,
                "failed": total_sent - successful,
                "success_rate": (successful / total_sent * 100) if total_sent > 0 else 0,
                "by_day": {str(k): v for k, v in by_day.items()}
            }
            
        except Exception as e:
            logger.error(f"Failed to get email analytics: {e}")
            return {"error": str(e)}
        finally:
            db.close()
