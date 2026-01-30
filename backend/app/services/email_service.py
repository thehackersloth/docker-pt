"""
Email service
Handles email sending for reports and notifications
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email sending service"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_use_tls = settings.SMTP_USE_TLS
        self.email_from = settings.EMAIL_FROM
        self.email_from_name = settings.EMAIL_FROM_NAME
    
    def send_scan_report(
        self,
        scan_id: str,
        recipients: List[str],
        report_formats: List[str] = ["pdf"],
        subject: Optional[str] = None
    ) -> bool:
        """
        Send scan report via email
        """
        if not settings.SMTP_ENABLED:
            logger.warning("SMTP is disabled, cannot send email")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.email_from_name} <{self.email_from}>"
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject or f"Pentest Scan Report - {scan_id}"
            
            # Add body
            body = f"""
            Pentest scan {scan_id} has completed.

            Please find the report attached.

            This is an automated message from the Professional Pentesting Platform.
            """
            msg.attach(MIMEText(body, 'plain'))

            # Attach report files based on report_formats
            from pathlib import Path
            report_dir = Path(settings.REPORT_OUTPUT_DIR) / scan_id

            extension_map = {
                'pdf': '.pdf',
                'html': '.html',
                'json': '.json',
                'csv': '.csv',
                'word': '.docx'
            }

            for fmt in report_formats:
                ext = extension_map.get(fmt, f'.{fmt}')
                report_files = list(report_dir.glob(f'*{ext}'))

                for report_file in report_files:
                    if report_file.exists():
                        with open(report_file, 'rb') as f:
                            attachment = MIMEBase('application', 'octet-stream')
                            attachment.set_payload(f.read())
                            encoders.encode_base64(attachment)
                            attachment.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{report_file.name}"'
                            )
                            msg.attach(attachment)

            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.smtp_use_tls:
                server.starttls()
            
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully to {recipients}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Send a generic email
        """
        if not settings.SMTP_ENABLED:
            logger.warning("SMTP is disabled, cannot send email")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = f"{self.email_from_name} <{self.email_from}>"
            msg['To'] = ', '.join(to)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            # Add attachments if provided
            if attachments:
                from pathlib import Path
                for attachment_path in attachments:
                    file_path = Path(attachment_path)
                    if file_path.exists():
                        with open(file_path, 'rb') as f:
                            attachment = MIMEBase('application', 'octet-stream')
                            attachment.set_payload(f.read())
                            encoders.encode_base64(attachment)
                            attachment.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{file_path.name}"'
                            )
                            msg.attach(attachment)

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.smtp_use_tls:
                server.starttls()

            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            server.send_message(msg)
            server.quit()

            logger.info(f"Email sent successfully to {to}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_report(
        self,
        to_email: str,
        report_name: str,
        report_path: str
    ) -> dict:
        """
        Send a report via email
        """
        if not settings.SMTP_ENABLED:
            return {'success': False, 'error': 'SMTP is disabled'}

        try:
            subject = f"Pentest Report: {report_name}"
            body = f"""
Dear recipient,

Please find attached the pentest report: {report_name}

This is an automated message from the Professional Pentesting Platform.

Best regards,
Security Team
            """

            success = self.send_email(
                to=[to_email],
                subject=subject,
                body=body,
                attachments=[report_path] if report_path else None
            )

            return {'success': success}

        except Exception as e:
            logger.error(f"Failed to send report email: {e}")
            return {'success': False, 'error': str(e)}
