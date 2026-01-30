"""
Audit logging system
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from app.core.database import SessionLocal
from sqlalchemy import Column, String, DateTime, JSON, Text
from app.core.database import Base
import uuid

logger = logging.getLogger(__name__)


class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True)
    username = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    status = Column(String, nullable=True)  # success, failure
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class AuditLogger:
    """Audit logging service"""
    
    @staticmethod
    def log(
        action: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ):
        """Log an audit event"""
        try:
            db = SessionLocal()
            audit_log = AuditLog(
                user_id=user_id,
                username=username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details,
                status=status
            )
            db.add(audit_log)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    @staticmethod
    def log_scan_created(scan_id: str, user_id: str, username: str, scan_name: str):
        """Log scan creation"""
        AuditLogger.log(
            action="scan_created",
            user_id=user_id,
            username=username,
            resource_type="scan",
            resource_id=scan_id,
            details={"scan_name": scan_name}
        )
    
    @staticmethod
    def log_scan_started(scan_id: str, user_id: Optional[str] = None):
        """Log scan start"""
        AuditLogger.log(
            action="scan_started",
            user_id=user_id,
            resource_type="scan",
            resource_id=scan_id
        )
    
    @staticmethod
    def log_login(username: str, ip_address: str, success: bool):
        """Log login attempt"""
        AuditLogger.log(
            action="login",
            username=username,
            ip_address=ip_address,
            status="success" if success else "failure"
        )
    
    @staticmethod
    def log_config_change(user_id: str, username: str, config_key: str, old_value: Any, new_value: Any):
        """Log configuration change"""
        AuditLogger.log(
            action="config_changed",
            user_id=user_id,
            username=username,
            resource_type="config",
            details={
                "key": config_key,
                "old_value": str(old_value),
                "new_value": str(new_value)
            }
        )
