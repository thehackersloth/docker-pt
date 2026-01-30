"""
Finding model
"""

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.database import Base
import uuid


class FindingStatus(str, enum.Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"
    REMEDIATED = "remediated"
    IN_PROGRESS = "in_progress"


class FindingSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(Base):
    __tablename__ = "findings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False, index=True)
    
    # Finding details
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(Enum(FindingSeverity), nullable=False, index=True)
    status = Column(Enum(FindingStatus), default=FindingStatus.NEW, nullable=False, index=True)
    
    # Vulnerability information
    cve_id = Column(String, nullable=True, index=True)
    cvss_score = Column(String, nullable=True)
    cvss_vector = Column(String, nullable=True)
    exploit_available = Column(String, nullable=True)  # yes, no, unknown
    
    # Technical details
    target = Column(String, nullable=False, index=True)
    port = Column(String, nullable=True)
    protocol = Column(String, nullable=True)
    service = Column(String, nullable=True)
    tool_name = Column(String, nullable=False)
    tool_output = Column(JSON, nullable=True)
    
    # Evidence
    evidence = Column(JSON, nullable=True)  # Screenshots, pcaps, logs
    proof_of_concept = Column(Text, nullable=True)
    
    # Remediation
    remediation = Column(Text, nullable=True)
    remediation_priority = Column(String, nullable=True)
    
    # Assignment and tracking
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    tags = Column(JSON, nullable=True)  # List of tags
    comments = Column(JSON, nullable=True)  # List of comments
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    remediated_at = Column(DateTime, nullable=True)

    # Relationships
    scan = relationship("Scan", back_populates="findings")
    assigned_to_user = relationship("User", back_populates="findings", foreign_keys=[assigned_to])
