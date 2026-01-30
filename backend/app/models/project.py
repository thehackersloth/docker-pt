"""
Project/Client/Engagement management model
"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from app.core.database import Base
import uuid


class ProjectStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class EngagementType(str, enum.Enum):
    EXTERNAL_PENTEST = "external_pentest"
    INTERNAL_PENTEST = "internal_pentest"
    WEB_APP_PENTEST = "web_app_pentest"
    MOBILE_APP_PENTEST = "mobile_app_pentest"
    API_PENTEST = "api_pentest"
    WIRELESS_PENTEST = "wireless_pentest"
    SOCIAL_ENGINEERING = "social_engineering"
    RED_TEAM = "red_team"
    PURPLE_TEAM = "purple_team"
    VULNERABILITY_ASSESSMENT = "vulnerability_assessment"
    COMPLIANCE_AUDIT = "compliance_audit"


class Client(Base):
    """Client/Organization model"""
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    industry = Column(String, nullable=True)
    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="client")


class Project(Base):
    """Project/Engagement model"""
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=True)

    # Engagement details
    engagement_type = Column(Enum(EngagementType), nullable=False)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNING, nullable=False)
    description = Column(Text, nullable=True)

    # Scope
    scope = Column(JSON, nullable=True)  # List of in-scope targets
    out_of_scope = Column(JSON, nullable=True)  # List of excluded targets
    rules_of_engagement = Column(Text, nullable=True)

    # Timeline
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    report_due_date = Column(DateTime, nullable=True)

    # Team
    lead_tester = Column(String, nullable=True)
    team_members = Column(JSON, nullable=True)  # List of usernames

    # Authorization
    authorization_document = Column(String, nullable=True)  # File path
    emergency_contact = Column(String, nullable=True)

    # Compliance
    compliance_frameworks = Column(JSON, nullable=True)  # ['PCI-DSS', 'HIPAA', etc.]

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="projects")


class ProjectNote(Base):
    """Notes/comments for projects and findings"""
    __tablename__ = "project_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    finding_id = Column(String, nullable=True)  # Can be attached to a finding
    scan_id = Column(String, nullable=True)  # Can be attached to a scan

    # Note content
    title = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    note_type = Column(String, default="general")  # general, technical, methodology, todo

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, nullable=True)

    # Flags
    is_pinned = Column(Boolean, default=False)
    is_private = Column(Boolean, default=False)
