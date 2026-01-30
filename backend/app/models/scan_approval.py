"""
Scan approval workflow models
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid
import enum


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ScanApproval(Base):
    """Scan approval request"""
    __tablename__ = "scan_approvals"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    requested_by = Column(String, ForeignKey("users.id"), nullable=False)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, nullable=False)
    reason = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    approved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    scan = relationship("Scan", backref="approval")
    requester = relationship("User", foreign_keys=[requested_by], backref="requested_approvals")
    approver = relationship("User", foreign_keys=[approved_by], backref="approved_scans")
