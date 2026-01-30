"""
Environment variable validation on startup
"""

import os
import logging
from typing import List, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Validate environment configuration on startup"""
    
    REQUIRED_VARS = [
        "SECRET_KEY",
        "ENCRYPTION_KEY",
        "JWT_SECRET",
        "POSTGRES_HOST",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    
    OPTIONAL_VARS = [
        "NEO4J_HOST",
        "NEO4J_PASSWORD",
        "REDIS_HOST",
        "SMTP_HOST",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    ]
    
    @staticmethod
    def validate() -> Tuple[bool, List[str]]:
        """Validate environment variables"""
        errors = []
        warnings = []
        
        # Check required variables
        for var in EnvironmentValidator.REQUIRED_VARS:
            value = getattr(settings, var, None)
            if not value or value in ["changeme", "supersecretkey", "superencryptionkey", "superjwtsecret"]:
                errors.append(f"{var} is not set or using default value (security risk!)")
        
        # Check optional but recommended variables
        for var in EnvironmentValidator.OPTIONAL_VARS:
            value = getattr(settings, var, None)
            if not value:
                warnings.append(f"{var} is not set (optional but recommended)")
        
        # Validate database connection
        try:
            from app.core.database import SessionLocal
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
        except Exception as e:
            errors.append(f"Database connection failed: {str(e)}")
        
        # Validate Redis connection
        try:
            import redis
            r = redis.Redis(
                host=getattr(settings, 'REDIS_HOST', 'localhost'),
                port=int(getattr(settings, 'REDIS_PORT', 6379)),
                decode_responses=True
            )
            r.ping()
        except Exception as e:
            warnings.append(f"Redis connection failed: {str(e)} (optional but recommended)")
        
        # Validate AI configuration
        if getattr(settings, 'AI_ENABLED', False):
            if getattr(settings, 'AI_LOCAL_ONLY', True):
                # Check local AI
                ollama_enabled = getattr(settings, 'OLLAMA_ENABLED', False)
                if not ollama_enabled:
                    warnings.append("AI_LOCAL_ONLY is true but no local AI provider is enabled")
            else:
                # Check cloud AI keys
                has_cloud_ai = any([
                    getattr(settings, 'OPENAI_API_KEY', None),
                    getattr(settings, 'ANTHROPIC_API_KEY', None),
                    getattr(settings, 'GEMINI_API_KEY', None),
                ])
                if not has_cloud_ai:
                    warnings.append("Cloud AI enabled but no API keys configured")
        
        # Log results
        if errors:
            logger.error("Environment validation failed:")
            for error in errors:
                logger.error(f"  ❌ {error}")
        
        if warnings:
            logger.warning("Environment validation warnings:")
            for warning in warnings:
                logger.warning(f"  ⚠️  {warning}")
        
        if not errors and not warnings:
            logger.info("✅ Environment validation passed")
        
        return len(errors) == 0, errors + warnings
