"""
Credential model (encrypted storage)
"""

from sqlalchemy import Column, String, DateTime, Enum, Text, JSON, Integer
import enum
from datetime import datetime
from app.core.database import Base
import uuid


class CredentialType(str, enum.Enum):
    USERNAME_PASSWORD = "username_password"
    API_KEY = "api_key"
    TOKEN = "token"
    CERTIFICATE = "certificate"
    SSH_KEY = "ssh_key"
    CUSTOM = "custom"


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    credential_type = Column(Enum(CredentialType), nullable=False)
    
    # Encrypted credential data (never store plaintext)
    encrypted_data = Column(Text, nullable=False)  # AES-256 encrypted
    encryption_key_id = Column(String, nullable=False)  # Reference to key used
    
    # Metadata
    tags = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String, nullable=True)
