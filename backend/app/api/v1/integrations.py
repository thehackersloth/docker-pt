"""
Integration endpoints (SIEM, ticketing, webhooks)
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.core.database import SessionLocal, get_db
from app.core.security import require_admin
from app.models.user import User
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class SIEMConfig(BaseModel):
    type: str  # splunk, elk, qradar
    endpoint: str
    api_key: Optional[str] = None
    enabled: bool = False


class TicketingConfig(BaseModel):
    type: str  # jira, servicenow, github
    endpoint: str
    api_key: Optional[str] = None
    project_key: Optional[str] = None
    enabled: bool = False


class WebhookConfig(BaseModel):
    url: str
    secret: Optional[str] = None
    events: List[str]  # scan_completed, finding_created, etc.
    enabled: bool = True


@router.post("/siem/send")
async def send_to_siem(
    finding_id: str,
    config: SIEMConfig,
    current_user: User = Depends(require_admin),
    db: SessionLocal = Depends(get_db)
):
    """Send finding to SIEM"""
    from app.models.finding import Finding
    
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    # Format finding for SIEM
    siem_data = {
        "timestamp": finding.created_at.isoformat(),
        "severity": finding.severity.value,
        "title": finding.title,
        "description": finding.description,
        "target": finding.target,
        "cve_id": finding.cve_id,
        "source": "pentest-platform"
    }
    
    try:
        if config.type == "splunk":
            # Splunk HEC format
            response = httpx.post(
                f"{config.endpoint}/services/collector/event",
                headers={
                    "Authorization": f"Splunk {config.api_key}",
                    "Content-Type": "application/json"
                },
                json={"event": siem_data},
                timeout=10
            )
        elif config.type == "elk":
            # Elasticsearch format
            response = httpx.post(
                f"{config.endpoint}/pentest-findings/_doc",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"
                },
                json=siem_data,
                timeout=10
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported SIEM type: {config.type}")
        
        response.raise_for_status()
        return {"success": True, "message": "Finding sent to SIEM"}
        
    except Exception as e:
        logger.error(f"SIEM integration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ticketing/create")
async def create_ticket(
    finding_id: str,
    config: TicketingConfig,
    current_user: User = Depends(require_admin),
    db: SessionLocal = Depends(get_db)
):
    """Create ticket in ticketing system"""
    from app.models.finding import Finding
    
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    
    try:
        if config.type == "jira":
            # Jira format
            ticket_data = {
                "fields": {
                    "project": {"key": config.project_key},
                    "summary": finding.title,
                    "description": finding.description,
                    "issuetype": {"name": "Bug"},
                    "priority": {"name": finding.severity.value.upper()}
                }
            }
            
            response = httpx.post(
                f"{config.endpoint}/rest/api/2/issue",
                headers={
                    "Authorization": f"Basic {config.api_key}",
                    "Content-Type": "application/json"
                },
                json=ticket_data,
                timeout=10
            )
        elif config.type == "github":
            # GitHub Issues format
            issue_data = {
                "title": finding.title,
                "body": finding.description,
                "labels": [finding.severity.value]
            }
            
            response = httpx.post(
                f"{config.endpoint}/repos/{config.project_key}/issues",
                headers={
                    "Authorization": f"token {config.api_key}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=issue_data,
                timeout=10
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported ticketing type: {config.type}")
        
        response.raise_for_status()
        return {"success": True, "ticket_id": response.json().get("id") or response.json().get("key")}
        
    except Exception as e:
        logger.error(f"Ticketing integration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/trigger")
async def trigger_webhook(
    event: str,
    data: Dict[str, Any],
    config: WebhookConfig,
    current_user: User = Depends(require_admin)
):
    """Trigger webhook"""
    if event not in config.events:
        raise HTTPException(status_code=400, detail=f"Event {event} not configured")
    
    try:
        headers = {"Content-Type": "application/json"}
        if config.secret:
            import hmac
            import hashlib
            signature = hmac.new(
                config.secret.encode(),
                str(data).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature
        
        response = httpx.post(
            config.url,
            headers=headers,
            json={"event": event, "data": data},
            timeout=10
        )
        
        response.raise_for_status()
        return {"success": True, "message": "Webhook triggered"}
        
    except Exception as e:
        logger.error(f"Webhook failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
