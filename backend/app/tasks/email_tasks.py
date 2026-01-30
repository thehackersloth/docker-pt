"""
Email sending tasks
"""

from celery import Task
from app.core.celery_app import celery_app
from app.services.email_service import EmailService
import logging

logger = logging.getLogger(__name__)


@celery_app.task(name="send_scan_report_email")
def send_scan_report_email(scan_id: str, recipients: list, report_formats: list):
    """
    Send scan report via email
    """
    logger.info(f"Sending scan report email for scan {scan_id}")
    
    try:
        email_service = EmailService()
        result = email_service.send_scan_report(
            scan_id=scan_id,
            recipients=recipients,
            report_formats=report_formats
        )
        logger.info(f"Email sent successfully for scan {scan_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to send email for scan {scan_id}: {e}")
        raise
