"""
Report model
"""

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, JSON, Integer, Boolean
import enum
from datetime import datetime
from app.core.database import Base
import uuid


class ReportType(str, enum.Enum):
    EXECUTIVE = "executive"
    TECHNICAL = "technical"
    COMPLIANCE = "compliance"
    FULL = "full"
    CUSTOM = "custom"


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    WORD = "word"


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False, index=True)
    
    # Report details
    name = Column(String, nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    format = Column(Enum(ReportFormat), nullable=False)
    
    # Content
    content = Column(JSON, nullable=True)  # Report data
    file_path = Column(String, nullable=True)  # Path to generated file
    file_size = Column(Integer, nullable=True)  # File size in bytes
    
    # Generation
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    generated_by = Column(String, ForeignKey("users.id"), nullable=True)
    generation_time_seconds = Column(Integer, nullable=True)
    
    # Email delivery
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime, nullable=True)
    email_recipients = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    template_used = Column(String, nullable=True)
    ai_enhanced = Column(Boolean, default=False, nullable=False)
