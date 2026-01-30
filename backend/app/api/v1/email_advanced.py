"""
Advanced email features endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.services.email_advanced import AdvancedEmailService
from app.core.security import require_admin
from app.models.user import User

router = APIRouter()
email_service = AdvancedEmailService()


class ConditionalEmailRequest(BaseModel):
    scan_id: str
    recipients: List[str]
    conditions: Dict[str, Any]  # only_if_critical, min_findings, etc.
    report_formats: List[str] = ["pdf"]


class ScheduledEmailRequest(BaseModel):
    scan_id: str
    recipients: List[str]
    send_at: str  # ISO datetime
    report_formats: List[str] = ["pdf"]


class BatchEmailRequest(BaseModel):
    scan_ids: List[str]
    recipients: List[str]
    report_formats: List[str] = ["pdf"]


@router.post("/conditional")
async def send_conditional_email(
    request: ConditionalEmailRequest,
    current_user: User = Depends(require_admin)
):
    """Send email conditionally based on findings"""
    should_send = email_service.should_send_email(request.scan_id, request.conditions)
    
    if not should_send:
        return {
            "sent": False,
            "reason": "Conditions not met"
        }
    
    success = email_service.send_scan_report(
        request.scan_id,
        request.recipients,
        request.report_formats
    )
    
    return {
        "sent": True,
        "success": success
    }


@router.post("/schedule")
async def schedule_email(
    request: ScheduledEmailRequest,
    current_user: User = Depends(require_admin)
):
    """Schedule email to be sent at specific time"""
    try:
        send_at = datetime.fromisoformat(request.send_at.replace('Z', '+00:00'))
        success = email_service.schedule_email(
            request.scan_id,
            request.recipients,
            send_at,
            request.report_formats
        )
        return {
            "success": success,
            "scheduled_for": request.send_at
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {e}")


@router.post("/batch")
async def send_batch_emails(
    request: BatchEmailRequest,
    current_user: User = Depends(require_admin)
):
    """Send emails for multiple scans"""
    results = email_service.send_batch_emails(
        request.scan_ids,
        request.recipients,
        request.report_formats
    )
    return {
        "success": True,
        "results": results,
        "total": len(results),
        "successful": sum(1 for v in results.values() if v)
    }


@router.get("/analytics")
async def get_email_analytics(days: int = 30):
    """Get email delivery analytics"""
    analytics = email_service.get_email_analytics(days)
    return analytics
