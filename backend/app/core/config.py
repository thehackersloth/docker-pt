"""
Application configuration
Loads from environment variables with defaults
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Professional Pentesting Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    TIMEZONE: str = "UTC"
    
    # Security
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600
    ALGORITHM: str = "HS256"  # Alias for JWT_ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "pentest"
    POSTGRES_USER: str = "pentest"
    POSTGRES_PASSWORD: str
    DATABASE_URL: Optional[str] = None
    
    # Neo4j
    NEO4J_HOST: str = "neo4j"
    NEO4J_PORT: int = 7687
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    
    # AI Configuration
    AI_ENABLED: bool = True
    AI_PRIVACY_MODE: str = "strict"  # strict, normal, permissive
    AI_LOCAL_ONLY: bool = False  # Allow cloud AI with API keys

    # Claude Code Bridge (connects to Claude Code on host)
    CLAUDE_CODE_BRIDGE_ENABLED: bool = True
    CLAUDE_CODE_BRIDGE_URL: str = "http://host.docker.internal:9999"
    
    # Cloud AI (⚠️ WARNING: Public APIs)
    OPENAI_ENABLED: bool = False
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_ENABLED: bool = False
    ANTHROPIC_API_KEY: Optional[str] = None
    GITHUB_COPILOT_ENABLED: bool = False
    GITHUB_COPILOT_KEY: Optional[str] = None
    GITHUB_COPILOT_BASE_URL: str = "https://api.githubcopilot.com"
    GEMINI_ENABLED: bool = False
    GEMINI_API_KEY: Optional[str] = None
    
    # Local AI (✅ Private)
    OLLAMA_ENABLED: bool = True
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama2:13b"
    LLAMA_CPP_ENABLED: bool = True
    LLAMA_CPP_MODEL_PATH: str = "/models/llama-2-7b.gguf"
    RAYSERVE_ENABLED: bool = True
    RAYSERVE_ENDPOINT: str = "http://rayserve:8000"
    WHITERABBIT_NEO_ENABLED: bool = True
    WHITERABBIT_NEO_BASE_URL: str = "http://whiterabbit-neo:8000"
    WHITERABBIT_NEO_MODEL: str = "whiterabbit-neo"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost", "http://localhost:80", "http://localhost:8888"]
    
    # Email
    SMTP_ENABLED: bool = True
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "noreply@example.com"
    EMAIL_FROM_NAME: str = "Pentest Platform"
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Scanning
    MAX_CONCURRENT_SCANS: int = 5
    MAX_SCAN_DURATION: int = 3600

    # Reports
    REPORT_OUTPUT_DIR: str = "/data/reports"
    
    # Logging
    LOG_AI_QUERIES: bool = True
    AUDIT_ENABLED: bool = True
    AUDIT_RETENTION_DAYS: int = 365
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Validate AI configuration
if settings.AI_ENABLED and settings.AI_LOCAL_ONLY:
    # Disable cloud AI if local-only mode
    settings.OPENAI_ENABLED = False
    settings.ANTHROPIC_ENABLED = False
    settings.GITHUB_COPILOT_ENABLED = False
    settings.GEMINI_ENABLED = False
