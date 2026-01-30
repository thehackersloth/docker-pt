"""
Slack/Teams notifications
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.core.database import SessionLocal, get_db
from app.core.security import require_admin
from app.models.user import User
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class SlackConfig(BaseModel):
    webhook_url: str
    channel: Optional[str] = None
    enabled: bool = True


class TeamsConfig(BaseModel):
    webhook_url: str
    enabled: bool = True


class NotificationRequest(BaseModel):
    message: str
    title: Optional[str] = None
    severity: Optional[str] = "info"  # info, warning, error, success


@router.post("/slack/send")
async def send_slack_notification(
    request: NotificationRequest,
    config: SlackConfig,
    current_user: User = Depends(require_admin)
):
    """Send Slack notification"""
    if not config.enabled:
        raise HTTPException(status_code=400, detail="Slack notifications are disabled")
    
    # Format message
    color_map = {
        "info": "#36a64f",
        "warning": "#ff9900",
        "error": "#ff0000",
        "success": "#36a64f"
    }
    
    payload = {
        "text": request.title or "Pentest Platform Notification",
        "attachments": [{
            "color": color_map.get(request.severity, "#36a64f"),
            "text": request.message,
            "footer": "Pentest Platform",
            "ts": int(datetime.utcnow().timestamp())
        }]
    }
    
    if config.channel:
        payload["channel"] = config.channel
    
    try:
        response = httpx.post(
            config.webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "message": "Slack notification sent"}
    except Exception as e:
        logger.error(f"Slack notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/teams/send")
async def send_teams_notification(
    request: NotificationRequest,
    config: TeamsConfig,
    current_user: User = Depends(require_admin)
):
    """Send Microsoft Teams notification"""
    if not config.enabled:
        raise HTTPException(status_code=400, detail="Teams notifications are disabled")
    
    # Format message for Teams
    color_map = {
        "info": "0078D4",
        "warning": "FF8C00",
        "error": "DC3545",
        "success": "28A745"
    }
    
    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": request.title or "Pentest Platform Notification",
        "themeColor": color_map.get(request.severity, "0078D4"),
        "title": request.title or "Pentest Platform Notification",
        "text": request.message
    }
    
    try:
        response = httpx.post(
            config.webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "message": "Teams notification sent"}
    except Exception as e:
        logger.error(f"Teams notification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
