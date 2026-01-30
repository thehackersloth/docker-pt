"""
Authorization and disclaimer models
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid


class Authorization(Base):
    """Scan authorization/disclaimer acceptance"""
    __tablename__ = "authorizations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    username = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Authorization details
    target = Column(String, nullable=False)
    scope = Column(Text, nullable=True)
    authorized_by = Column(String, nullable=True)  # Person who authorized
    authorization_date = Column(DateTime, nullable=True)
    
    # Disclaimer acceptance
    disclaimer_accepted = Column(Boolean, default=False)
    disclaimer_text = Column(Text, nullable=True)
    disclaimer_version = Column(String, nullable=True)
    
    # Terms acceptance
    terms_accepted = Column(Boolean, default=False)
    terms_version = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    scan = relationship("Scan", backref="authorization")
    user = relationship("User", backref="authorizations")


class Disclaimer(Base):
    """Disclaimer templates"""
    __tablename__ = "disclaimers"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    version = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
