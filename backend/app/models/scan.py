"""
Scan model
"""

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, JSON, Text, Integer
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.database import Base
import uuid


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class ScanType(str, enum.Enum):
    NETWORK = "network"
    WEB = "web"
    AD = "ad"
    FULL = "full"
    CUSTOM = "custom"


class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    scan_type = Column(Enum(ScanType), nullable=False)
    status = Column(Enum(ScanStatus), default=ScanStatus.PENDING, nullable=False, index=True)
    
    # Configuration
    targets = Column(JSON, nullable=False)  # List of targets
    scan_config = Column(JSON, nullable=True)  # Tool-specific configuration
    credentials_id = Column(String, ForeignKey("credentials.id"), nullable=True)
    
    # Execution
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    progress_percent = Column(Integer, default=0, nullable=False)
    
    # Results
    results = Column(JSON, nullable=True)  # Aggregated results
    findings_count = Column(Integer, default=0, nullable=False)
    critical_count = Column(Integer, default=0, nullable=False)
    high_count = Column(Integer, default=0, nullable=False)
    medium_count = Column(Integer, default=0, nullable=False)
    low_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Schedule relationship
    schedule_id = Column(String, ForeignKey("schedules.id"), nullable=True)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Live output logs
    output_log = Column(Text, nullable=True)

    # Relationships
    created_by_user = relationship("User", back_populates="scans", foreign_keys=[created_by])
    findings = relationship("Finding", back_populates="scan", cascade="all, delete-orphan")
    schedule = relationship("Schedule", back_populates="scans", foreign_keys=[schedule_id])
