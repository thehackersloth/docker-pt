"""
Scan execution tasks
"""

from celery import Task
from datetime import datetime
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.services.scan_engine import ScanEngine
import logging

logger = logging.getLogger(__name__)


class ScanTask(Task):
    """Custom task class for scan execution"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure"""
        logger.error(f"Scan task {task_id} failed: {exc}")
        db = SessionLocal()
        try:
            scan_id = args[0] if args else kwargs.get('scan_id')
            if scan_id:
                scan = db.query(Scan).filter(Scan.id == scan_id).first()
                if scan:
                    scan.status = ScanStatus.FAILED
                    scan.error_message = str(exc)
                    db.commit()
        except Exception as e:
            logger.error(f"Error updating scan status: {e}")
        finally:
            db.close()


@celery_app.task(bind=True, base=ScanTask, name="execute_scan")
def execute_scan_task(self, scan_id: str):
    """
    Execute a scan task
    """
    logger.info(f"Starting scan execution: {scan_id}")
    
    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")
        
        # Update status
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.utcnow()
        db.commit()
        
        # Initialize scan engine
        scan_engine = ScanEngine(scan_id=scan_id)
        
        # Execute scan
        results = scan_engine.execute()
        
        # Update scan with results
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.utcnow()
        scan.results = results
        scan.progress_percent = 100
        
        # Send email if configured
        from app.tasks.email_tasks import send_scan_report_email
        if scan.schedule and scan.schedule.email_enabled:
            send_scan_report_email.delay(
                scan_id=str(scan.id),
                recipients=scan.schedule.email_recipients or [],
                report_formats=scan.schedule.report_formats or ["pdf"]
            )
        
        # Calculate duration
        if scan.started_at:
            duration = (scan.completed_at - scan.started_at).total_seconds()
            scan.duration_seconds = int(duration)
        
        db.commit()
        logger.info(f"Scan {scan_id} completed successfully")
        
        return {"scan_id": scan_id, "status": "completed", "results": results}
        
    except Exception as e:
        logger.error(f"Scan execution failed: {e}")
        if scan:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(bind=True, base=ScanTask, name="execute_full_pentest")
def execute_full_pentest_task(self, scan_id: str):
    """
    Execute a full penetration test - reconnaissance through exploitation
    """
    logger.info(f"Starting FULL PENTEST execution: {scan_id}")

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            raise ValueError(f"Scan {scan_id} not found")

        # Update status
        scan.status = ScanStatus.RUNNING
        scan.started_at = datetime.utcnow()
        db.commit()

        # Import and run full automation engine
        from app.services.full_pentest_engine import FullPentestEngine

        engine = FullPentestEngine(scan_id=scan_id)
        results = engine.execute_full_pentest()

        # Update scan with results
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.utcnow()
        scan.results = results
        scan.progress_percent = 100

        # Calculate duration
        if scan.started_at:
            duration = (scan.completed_at - scan.started_at).total_seconds()
            scan.duration_seconds = int(duration)

        db.commit()
        logger.info(f"Full pentest {scan_id} completed successfully")

        return {"scan_id": scan_id, "status": "completed", "results": results}

    except Exception as e:
        logger.error(f"Full pentest execution failed: {e}", exc_info=True)
        if scan:
            scan.status = ScanStatus.FAILED
            scan.error_message = str(e)
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task(name="cancel_scan")
def cancel_scan_task(scan_id: str):
    """
    Cancel a running scan
    """
    logger.info(f"Cancelling scan: {scan_id}")

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            scan.status = ScanStatus.CANCELLED
            db.commit()
            logger.info(f"Scan {scan_id} cancelled")
    except Exception as e:
        logger.error(f"Error cancelling scan: {e}")
    finally:
        db.close()
