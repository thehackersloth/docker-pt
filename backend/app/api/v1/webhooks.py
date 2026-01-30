"""
Webhook notifications API - Slack, Discord, Teams, Generic webhooks
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.database import get_db
from app.models.finding import Finding, FindingSeverity
from app.models.scan import Scan
from sqlalchemy.orm import Session
import httpx
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory webhook storage (in production, use database)
WEBHOOKS: Dict[str, Dict] = {}


class WebhookConfig(BaseModel):
    name: str
    webhook_type: str  # slack, discord, teams, generic
    url: str
    enabled: bool = True
    events: List[str] = ["scan_completed", "critical_finding", "high_finding"]
    custom_headers: Optional[Dict[str, str]] = None


class WebhookResponse(BaseModel):
    id: str
    name: str
    webhook_type: str
    url: str
    enabled: bool
    events: List[str]
    created_at: str


# ============ Webhook Management ============

@router.post("", response_model=WebhookResponse)
async def create_webhook(config: WebhookConfig):
    """Create a new webhook configuration"""
    import uuid
    webhook_id = str(uuid.uuid4())

    WEBHOOKS[webhook_id] = {
        "id": webhook_id,
        "name": config.name,
        "webhook_type": config.webhook_type,
        "url": config.url,
        "enabled": config.enabled,
        "events": config.events,
        "custom_headers": config.custom_headers,
        "created_at": datetime.utcnow().isoformat()
    }

    return WebhookResponse(**WEBHOOKS[webhook_id])


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks():
    """List all webhook configurations"""
    return [WebhookResponse(**w) for w in WEBHOOKS.values()]


@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """Delete a webhook"""
    if webhook_id not in WEBHOOKS:
        raise HTTPException(status_code=404, detail="Webhook not found")
    del WEBHOOKS[webhook_id]
    return {"message": "Webhook deleted"}


@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    """Test a webhook with a sample message"""
    if webhook_id not in WEBHOOKS:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook = WEBHOOKS[webhook_id]

    test_payload = _format_message(
        webhook["webhook_type"],
        "Test Notification",
        "This is a test message from the Pentest Platform",
        "info",
        {"timestamp": datetime.utcnow().isoformat()}
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook["url"],
                json=test_payload,
                headers=webhook.get("custom_headers", {}),
                timeout=10.0
            )
            response.raise_for_status()
            return {"success": True, "status_code": response.status_code}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ Notification Sending ============

def _format_message(webhook_type: str, title: str, message: str, severity: str, fields: Dict = None) -> Dict:
    """Format message based on webhook type"""

    severity_colors = {
        "critical": "#dc3545",
        "high": "#fd7e14",
        "medium": "#ffc107",
        "low": "#28a745",
        "info": "#17a2b8"
    }
    color = severity_colors.get(severity.lower(), "#6c757d")

    if webhook_type == "slack":
        return {
            "attachments": [{
                "color": color,
                "title": title,
                "text": message,
                "fields": [
                    {"title": k, "value": str(v), "short": True}
                    for k, v in (fields or {}).items()
                ],
                "footer": "Pentest Platform",
                "ts": int(datetime.utcnow().timestamp())
            }]
        }

    elif webhook_type == "discord":
        return {
            "embeds": [{
                "title": title,
                "description": message,
                "color": int(color.replace("#", ""), 16),
                "fields": [
                    {"name": k, "value": str(v), "inline": True}
                    for k, v in (fields or {}).items()
                ],
                "footer": {"text": "Pentest Platform"},
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

    elif webhook_type == "teams":
        return {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color.replace("#", ""),
            "summary": title,
            "sections": [{
                "activityTitle": title,
                "text": message,
                "facts": [
                    {"name": k, "value": str(v)}
                    for k, v in (fields or {}).items()
                ]
            }]
        }

    else:  # generic
        return {
            "title": title,
            "message": message,
            "severity": severity,
            "fields": fields,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "pentest-platform"
        }


async def send_webhook_notification(event: str, title: str, message: str, severity: str, fields: Dict = None):
    """Send notification to all webhooks subscribed to this event"""
    for webhook in WEBHOOKS.values():
        if not webhook["enabled"]:
            continue
        if event not in webhook["events"]:
            continue

        payload = _format_message(webhook["webhook_type"], title, message, severity, fields)

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    webhook["url"],
                    json=payload,
                    headers=webhook.get("custom_headers", {}),
                    timeout=10.0
                )
        except Exception as e:
            logger.error(f"Failed to send webhook {webhook['name']}: {e}")


# ============ Event Triggers ============

@router.post("/notify/scan-completed")
async def notify_scan_completed(
    scan_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send notification when scan completes"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
    critical = sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)
    high = sum(1 for f in findings if f.severity == FindingSeverity.HIGH)

    severity = "critical" if critical > 0 else "high" if high > 0 else "info"

    background_tasks.add_task(
        send_webhook_notification,
        "scan_completed",
        f"Scan Completed: {scan.name}",
        f"Scan has finished with {len(findings)} findings",
        severity,
        {
            "Critical": critical,
            "High": high,
            "Total Findings": len(findings),
            "Targets": ", ".join(scan.targets[:3]) if scan.targets else "N/A"
        }
    )

    return {"message": "Notification queued"}


@router.post("/notify/finding")
async def notify_finding(
    finding_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send notification for a finding"""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    severity = finding.severity.value
    event = f"{severity}_finding"

    background_tasks.add_task(
        send_webhook_notification,
        event,
        f"{severity.upper()} Finding: {finding.title}",
        finding.description[:200] if finding.description else "No description",
        severity,
        {
            "Target": finding.target,
            "CVE": finding.cve_id or "N/A",
            "CVSS": finding.cvss_score or "N/A",
            "Tool": finding.tool or "N/A"
        }
    )

    return {"message": "Notification queued"}


# ============ CVSS Calculator ============

class CVSSInput(BaseModel):
    attack_vector: str  # N, A, L, P
    attack_complexity: str  # L, H
    privileges_required: str  # N, L, H
    user_interaction: str  # N, R
    scope: str  # U, C
    confidentiality: str  # N, L, H
    integrity: str  # N, L, H
    availability: str  # N, L, H


@router.post("/cvss/calculate")
async def calculate_cvss(cvss: CVSSInput):
    """Calculate CVSS v3.1 score"""

    # CVSS v3.1 weights
    AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
    AC = {"L": 0.77, "H": 0.44}
    PR_U = {"N": 0.85, "L": 0.62, "H": 0.27}  # Scope Unchanged
    PR_C = {"N": 0.85, "L": 0.68, "H": 0.50}  # Scope Changed
    UI = {"N": 0.85, "R": 0.62}
    CIA = {"N": 0, "L": 0.22, "H": 0.56}

    # Get values
    av = AV.get(cvss.attack_vector.upper(), 0.85)
    ac = AC.get(cvss.attack_complexity.upper(), 0.77)
    ui = UI.get(cvss.user_interaction.upper(), 0.85)

    scope_changed = cvss.scope.upper() == "C"
    pr = PR_C.get(cvss.privileges_required.upper(), 0.85) if scope_changed else PR_U.get(cvss.privileges_required.upper(), 0.85)

    c = CIA.get(cvss.confidentiality.upper(), 0)
    i = CIA.get(cvss.integrity.upper(), 0)
    a = CIA.get(cvss.availability.upper(), 0)

    # Calculate ISS (Impact Sub Score)
    iss = 1 - ((1 - c) * (1 - i) * (1 - a))

    # Calculate Impact
    if scope_changed:
        impact = 7.52 * (iss - 0.029) - 3.25 * pow(iss - 0.02, 15)
    else:
        impact = 6.42 * iss

    # Calculate Exploitability
    exploitability = 8.22 * av * ac * pr * ui

    # Calculate Base Score
    if impact <= 0:
        base_score = 0
    elif scope_changed:
        base_score = min(1.08 * (impact + exploitability), 10)
    else:
        base_score = min(impact + exploitability, 10)

    # Round up to 1 decimal place
    import math
    base_score = math.ceil(base_score * 10) / 10

    # Determine severity
    if base_score == 0:
        severity = "None"
    elif base_score < 4.0:
        severity = "Low"
    elif base_score < 7.0:
        severity = "Medium"
    elif base_score < 9.0:
        severity = "High"
    else:
        severity = "Critical"

    # Generate vector string
    vector = f"CVSS:3.1/AV:{cvss.attack_vector.upper()}/AC:{cvss.attack_complexity.upper()}/PR:{cvss.privileges_required.upper()}/UI:{cvss.user_interaction.upper()}/S:{cvss.scope.upper()}/C:{cvss.confidentiality.upper()}/I:{cvss.integrity.upper()}/A:{cvss.availability.upper()}"

    return {
        "score": base_score,
        "severity": severity,
        "vector": vector,
        "impact": round(impact, 2),
        "exploitability": round(exploitability, 2)
    }
