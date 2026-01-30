"""
Data retention and deletion service
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.models.finding import Finding
from app.models.report import Report
from app.models.schedule import Schedule
from sqlalchemy.orm import Session
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataRetentionService:
    """Data retention and deletion service"""
    
    def __init__(self):
        self.retention_days = getattr(settings, 'DATA_RETENTION_DAYS', 90)
        self.audit_retention_days = getattr(settings, 'AUDIT_RETENTION_DAYS', 365)
    
    def delete_old_scans(self, days: Optional[int] = None) -> dict:
        """Delete scans older than retention period"""
        db = SessionLocal()
        try:
            retention_days = days or self.retention_days
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            # Find old scans
            old_scans = db.query(Scan).filter(
                Scan.created_at < cutoff_date,
                Scan.status == ScanStatus.COMPLETED
            ).all()
            
            deleted_count = 0
            for scan in old_scans:
                # Delete associated findings
                db.query(Finding).filter(Finding.scan_id == scan.id).delete()
                
                # Delete scan
                db.delete(scan)
                deleted_count += 1
            
            db.commit()
            
            return {
                "success": True,
                "deleted_scans": deleted_count,
                "cutoff_date": cutoff_date.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to delete old scans: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    def delete_old_reports(self, days: Optional[int] = None) -> dict:
        """Delete reports older than retention period"""
        db = SessionLocal()
        try:
            retention_days = days or self.retention_days
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            old_reports = db.query(Report).filter(
                Report.created_at < cutoff_date
            ).all()
            
            deleted_count = 0
            deleted_files = 0
            for report in old_reports:
                # Delete report file if exists
                if report.file_path:
                    from pathlib import Path
                    import os
                    file_path = Path(report.file_path)
                    if file_path.exists():
                        try:
                            os.remove(file_path)
                            deleted_files += 1
                            logger.info(f"Deleted report file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to delete file {file_path}: {e}")

                db.delete(report)
                deleted_count += 1
            
            db.commit()
            
            return {
                "success": True,
                "deleted_reports": deleted_count,
                "deleted_files": deleted_files,
                "cutoff_date": cutoff_date.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to delete old reports: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    def secure_delete_user_data(self, user_id: str) -> dict:
        """Securely delete all user data (GDPR right to deletion)"""
        db = SessionLocal()
        try:
            # Delete user's scans
            scans = db.query(Scan).filter(Scan.created_by == user_id).all()
            for scan in scans:
                db.query(Finding).filter(Finding.scan_id == scan.id).delete()
                db.delete(scan)
            
            # Delete user's reports
            db.query(Report).filter(Report.created_by == user_id).delete()
            
            # Delete user's schedules
            db.query(Schedule).filter(Schedule.created_by == user_id).delete()
            
            # Delete user's authorizations
            from app.models.authorization import Authorization
            db.query(Authorization).filter(Authorization.user_id == user_id).delete()
            
            # Delete user
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db.delete(user)
            
            db.commit()
            
            return {
                "success": True,
                "message": "All user data deleted"
            }
        except Exception as e:
            logger.error(f"Failed to delete user data: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()
    
    def export_user_data(self, user_id: str) -> dict:
        """Export all user data (GDPR data export)"""
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"error": "User not found"}
            
            # Get all user data
            scans = db.query(Scan).filter(Scan.created_by == user_id).all()
            findings = db.query(Finding).join(Scan).filter(Scan.created_by == user_id).all()
            reports = db.query(Report).filter(Report.created_by == user_id).all()
            schedules = db.query(Schedule).filter(Schedule.created_by == user_id).all()
            
            from app.models.authorization import Authorization
            authorizations = db.query(Authorization).filter(Authorization.user_id == user_id).all()
            
            return {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "created_at": user.created_at.isoformat()
                },
                "scans": [{
                    "id": str(s.id),
                    "name": s.name,
                    "status": s.status.value,
                    "created_at": s.created_at.isoformat()
                } for s in scans],
                "findings": [{
                    "id": str(f.id),
                    "title": f.title,
                    "severity": f.severity.value,
                    "created_at": f.created_at.isoformat()
                } for f in findings],
                "reports": [{
                    "id": str(r.id),
                    "type": r.report_type.value,
                    "created_at": r.created_at.isoformat()
                } for r in reports],
                "schedules": [{
                    "id": str(s.id),
                    "name": s.name,
                    "enabled": s.enabled,
                    "created_at": s.created_at.isoformat()
                } for s in schedules],
                "authorizations": [{
                    "id": str(a.id),
                    "target": a.target,
                    "created_at": a.created_at.isoformat()
                } for a in authorizations]
            }
        except Exception as e:
            logger.error(f"Failed to export user data: {e}")
            return {"error": str(e)}
        finally:
            db.close()
