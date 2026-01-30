"""
Schedule model
"""

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Boolean, JSON, Text, Integer
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.database import Base
import uuid


class ScheduleType(str, enum.Enum):
    ONE_TIME = "one_time"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Schedule configuration
    schedule_type = Column(Enum(ScheduleType), nullable=False)
    schedule_expression = Column(String, nullable=False)  # Cron expression or datetime
    timezone = Column(String, default="UTC", nullable=False)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    
    # Scan configuration (stored as JSON to reference scan config)
    scan_config = Column(JSON, nullable=False)
    
    # Email configuration
    email_enabled = Column(Boolean, default=True, nullable=False)
    email_recipients = Column(JSON, nullable=True)  # List of email addresses
    report_formats = Column(JSON, nullable=True)  # ["pdf", "html", "json"]
    
    # Execution tracking
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True, index=True)
    run_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    scans = relationship("Scan", back_populates="schedule")
