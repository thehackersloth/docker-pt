"""
Evidence collection endpoints
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List
from app.services.evidence_collector import EvidenceCollector

router = APIRouter()


class EvidenceCollectionRequest(BaseModel):
    finding_id: str
    evidence_types: List[str]  # screenshot, pcap, logs


@router.post("/collect")
async def collect_evidence(request: EvidenceCollectionRequest, scan_id: str):
    """Collect evidence for a finding"""
    try:
        collector = EvidenceCollector(scan_id)
        results = collector.collect_finding_evidence(
            request.finding_id,
            request.evidence_types
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screenshot")
async def capture_screenshot(url: str, finding_id: str, scan_id: str):
    """Capture screenshot"""
    try:
        collector = EvidenceCollector(scan_id)
        screenshot = collector.capture_screenshot(url, finding_id)
        if not screenshot:
            raise HTTPException(status_code=500, detail="Screenshot capture failed")
        return {"success": True, "screenshot": screenshot}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pcap")
async def capture_pcap(interface: str, duration: int, finding_id: str, scan_id: str):
    """Capture network traffic"""
    try:
        collector = EvidenceCollector(scan_id)
        pcap = collector.capture_pcap(interface, duration, finding_id)
        if not pcap:
            raise HTTPException(status_code=500, detail="PCAP capture failed")
        return {"success": True, "pcap": pcap}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
