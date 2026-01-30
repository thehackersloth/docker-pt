"""
Vulnerability Database API - CVE/NVD lookup, Exploit-DB, vulnerability enrichment
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.database import get_db
from sqlalchemy.orm import Session
import httpx
import logging
import re

router = APIRouter()
logger = logging.getLogger(__name__)

# Cache for CVE lookups
CVE_CACHE: Dict[str, Dict] = {}


class CVEInfo(BaseModel):
    cve_id: str
    description: str
    severity: str
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    published_date: Optional[str] = None
    modified_date: Optional[str] = None
    references: List[str] = []
    cwe_ids: List[str] = []
    affected_products: List[str] = []
    exploits: List[Dict] = []


class VulnSearchResult(BaseModel):
    total: int
    results: List[CVEInfo]


@router.get("/cve/{cve_id}", response_model=CVEInfo)
async def lookup_cve(cve_id: str):
    """Look up CVE details from NVD"""
    # Validate CVE ID format
    if not re.match(r'^CVE-\d{4}-\d+$', cve_id.upper()):
        raise HTTPException(status_code=400, detail="Invalid CVE ID format")

    cve_id = cve_id.upper()

    # Check cache
    if cve_id in CVE_CACHE:
        cache_entry = CVE_CACHE[cve_id]
        # Cache for 24 hours
        if (datetime.utcnow() - cache_entry["cached_at"]).total_seconds() < 86400:
            return CVEInfo(**cache_entry["data"])

    try:
        # Query NVD API
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={"cveId": cve_id},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("vulnerabilities"):
                raise HTTPException(status_code=404, detail="CVE not found")

            vuln = data["vulnerabilities"][0]["cve"]

            # Parse CVE data
            description = ""
            for desc in vuln.get("descriptions", []):
                if desc.get("lang") == "en":
                    description = desc.get("value", "")
                    break

            # Get CVSS score
            cvss_score = None
            cvss_vector = None
            severity = "unknown"

            metrics = vuln.get("metrics", {})
            if "cvssMetricV31" in metrics:
                cvss_data = metrics["cvssMetricV31"][0]["cvssData"]
                cvss_score = cvss_data.get("baseScore")
                cvss_vector = cvss_data.get("vectorString")
                severity = cvss_data.get("baseSeverity", "").lower()
            elif "cvssMetricV30" in metrics:
                cvss_data = metrics["cvssMetricV30"][0]["cvssData"]
                cvss_score = cvss_data.get("baseScore")
                cvss_vector = cvss_data.get("vectorString")
                severity = cvss_data.get("baseSeverity", "").lower()
            elif "cvssMetricV2" in metrics:
                cvss_data = metrics["cvssMetricV2"][0]["cvssData"]
                cvss_score = cvss_data.get("baseScore")
                cvss_vector = cvss_data.get("vectorString")
                # Map CVSS v2 to severity
                if cvss_score:
                    if cvss_score >= 9.0:
                        severity = "critical"
                    elif cvss_score >= 7.0:
                        severity = "high"
                    elif cvss_score >= 4.0:
                        severity = "medium"
                    else:
                        severity = "low"

            # Get references
            references = [
                ref.get("url") for ref in vuln.get("references", [])
                if ref.get("url")
            ]

            # Get CWE IDs
            cwe_ids = []
            for weakness in vuln.get("weaknesses", []):
                for desc in weakness.get("description", []):
                    if desc.get("value", "").startswith("CWE-"):
                        cwe_ids.append(desc.get("value"))

            # Get affected products
            affected_products = []
            for config in vuln.get("configurations", []):
                for node in config.get("nodes", []):
                    for match in node.get("cpeMatch", []):
                        if match.get("vulnerable"):
                            cpe = match.get("criteria", "")
                            # Parse CPE to get product name
                            parts = cpe.split(":")
                            if len(parts) >= 5:
                                vendor = parts[3]
                                product = parts[4]
                                affected_products.append(f"{vendor}/{product}")

            cve_info = {
                "cve_id": cve_id,
                "description": description,
                "severity": severity,
                "cvss_score": cvss_score,
                "cvss_vector": cvss_vector,
                "published_date": vuln.get("published"),
                "modified_date": vuln.get("lastModified"),
                "references": references[:10],  # Limit references
                "cwe_ids": list(set(cwe_ids)),
                "affected_products": list(set(affected_products))[:20],
                "exploits": []
            }

            # Cache result
            CVE_CACHE[cve_id] = {
                "data": cve_info,
                "cached_at": datetime.utcnow()
            }

            # Try to find exploits
            exploits = await _search_exploits(cve_id)
            cve_info["exploits"] = exploits

            return CVEInfo(**cve_info)

    except httpx.HTTPError as e:
        logger.error(f"NVD API error: {e}")
        raise HTTPException(status_code=503, detail="NVD API unavailable")
    except Exception as e:
        logger.error(f"CVE lookup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=VulnSearchResult)
async def search_vulnerabilities(
    keyword: str = Query(..., min_length=3),
    severity: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """Search vulnerabilities by keyword"""
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "keywordSearch": keyword,
                "resultsPerPage": limit
            }

            if severity:
                severity_map = {
                    "critical": "CRITICAL",
                    "high": "HIGH",
                    "medium": "MEDIUM",
                    "low": "LOW"
                }
                if severity.lower() in severity_map:
                    params["cvssV3Severity"] = severity_map[severity.lower()]

            response = await client.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params=params,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for vuln_data in data.get("vulnerabilities", []):
                vuln = vuln_data["cve"]

                description = ""
                for desc in vuln.get("descriptions", []):
                    if desc.get("lang") == "en":
                        description = desc.get("value", "")[:300]
                        break

                cvss_score = None
                sev = "unknown"
                metrics = vuln.get("metrics", {})
                if "cvssMetricV31" in metrics:
                    cvss_score = metrics["cvssMetricV31"][0]["cvssData"].get("baseScore")
                    sev = metrics["cvssMetricV31"][0]["cvssData"].get("baseSeverity", "").lower()

                results.append(CVEInfo(
                    cve_id=vuln.get("id"),
                    description=description,
                    severity=sev,
                    cvss_score=cvss_score,
                    published_date=vuln.get("published"),
                    references=[],
                    cwe_ids=[],
                    affected_products=[],
                    exploits=[]
                ))

            return VulnSearchResult(
                total=data.get("totalResults", len(results)),
                results=results
            )

    except httpx.HTTPError as e:
        logger.error(f"NVD search error: {e}")
        raise HTTPException(status_code=503, detail="NVD API unavailable")


@router.get("/exploits/{cve_id}")
async def get_exploits(cve_id: str):
    """Search for public exploits for a CVE"""
    if not re.match(r'^CVE-\d{4}-\d+$', cve_id.upper()):
        raise HTTPException(status_code=400, detail="Invalid CVE ID format")

    exploits = await _search_exploits(cve_id.upper())
    return {"cve_id": cve_id.upper(), "exploits": exploits}


async def _search_exploits(cve_id: str) -> List[Dict]:
    """Search Exploit-DB and other sources for exploits"""
    exploits = []

    try:
        # Search GitHub for exploits
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/search/repositories",
                params={"q": f"{cve_id} exploit", "per_page": 5},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                for repo in data.get("items", []):
                    exploits.append({
                        "source": "GitHub",
                        "title": repo.get("full_name"),
                        "url": repo.get("html_url"),
                        "description": repo.get("description", "")[:200] if repo.get("description") else ""
                    })
    except Exception as e:
        logger.warning(f"GitHub exploit search failed: {e}")

    # Add known exploit database URLs
    exploits.append({
        "source": "Exploit-DB",
        "title": f"Search Exploit-DB for {cve_id}",
        "url": f"https://www.exploit-db.com/search?cve={cve_id}",
        "description": "Search Exploit-DB for public exploits"
    })

    exploits.append({
        "source": "PacketStorm",
        "title": f"Search PacketStorm for {cve_id}",
        "url": f"https://packetstormsecurity.com/search/?q={cve_id}",
        "description": "Search PacketStorm Security for exploits"
    })

    return exploits


@router.post("/enrich-finding/{finding_id}")
async def enrich_finding(finding_id: str, db: Session = Depends(get_db)):
    """Enrich a finding with CVE data"""
    from app.models.finding import Finding

    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    if not finding.cve_id:
        return {"message": "No CVE ID associated with this finding"}

    try:
        cve_info = await lookup_cve(finding.cve_id)

        # Update finding with enriched data
        if cve_info.cvss_score and not finding.cvss_score:
            finding.cvss_score = cve_info.cvss_score

        if cve_info.cwe_ids:
            finding.cwe_ids = cve_info.cwe_ids

        if cve_info.references:
            existing_refs = finding.references or []
            finding.references = list(set(existing_refs + cve_info.references))

        db.commit()

        return {
            "message": "Finding enriched",
            "cve_info": cve_info,
            "exploits_found": len(cve_info.exploits)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
