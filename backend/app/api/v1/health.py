"""
Health check endpoints
"""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "ai_enabled": settings.AI_ENABLED,
        "ai_local_only": settings.AI_LOCAL_ONLY
    }
