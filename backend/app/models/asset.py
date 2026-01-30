"""
Asset model
"""

from sqlalchemy import Column, String, DateTime, Enum, JSON, Text, Integer
import enum
from datetime import datetime
from app.core.database import Base
import uuid


class AssetType(str, enum.Enum):
    HOST = "host"
    DOMAIN = "domain"
    IP_RANGE = "ip_range"
    WEB_APPLICATION = "web_application"
    API = "api"
    CLOUD_RESOURCE = "cloud_resource"
    UNKNOWN = "unknown"


class AssetCriticality(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Asset identification
    name = Column(String, nullable=False, index=True)
    asset_type = Column(Enum(AssetType), nullable=False, index=True)
    identifier = Column(String, nullable=False, index=True)  # IP, domain, etc.
    
    # Asset details
    description = Column(Text, nullable=True)
    criticality = Column(Enum(AssetCriticality), default=AssetCriticality.UNKNOWN, nullable=False, index=True)
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Ownership and metadata
    owner = Column(String, nullable=True)
    department = Column(String, nullable=True)
    location = Column(String, nullable=True)
    
    # Discovery information
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    discovered_by = Column(String, nullable=True)  # Tool or user
    last_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Asset properties
    properties = Column(JSON, nullable=True)  # OS, services, etc.
    vulnerabilities_count = Column(Integer, default=0, nullable=False)
    findings_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)
