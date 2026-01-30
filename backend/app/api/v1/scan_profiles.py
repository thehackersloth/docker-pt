"""
Scan profile templates API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

router = APIRouter()


class ScanProfile(BaseModel):
    id: str
    name: str
    description: str
    scan_type: str
    config: Dict[str, Any]


# Pre-defined scan profiles
SCAN_PROFILES = [
    {
        "id": "quick_network",
        "name": "Quick Network Scan",
        "description": "Fast port scan with service detection",
        "scan_type": "network",
        "config": {
            "tools": {
                "nmap": True,
                "masscan": False
            },
            "nmap": {
                "scan_type": "syn",
                "ports": "1-1000",
                "service_detection": True,
                "os_detection": False
            }
        }
    },
    {
        "id": "deep_network",
        "name": "Deep Network Scan",
        "description": "Comprehensive network scan with OS detection and scripts",
        "scan_type": "network",
        "config": {
            "tools": {
                "nmap": True,
                "masscan": True
            },
            "nmap": {
                "scan_type": "syn",
                "ports": "1-65535",
                "service_detection": True,
                "os_detection": True,
                "scripts": ["vuln", "discovery", "auth"]
            },
            "masscan": {
                "ports": "1-65535",
                "rate": "1000"
            }
        }
    },
    {
        "id": "web_application",
        "name": "Web Application Scan",
        "description": "Comprehensive web application security scan",
        "scan_type": "web",
        "config": {
            "tools": {
                "nikto": True,
                "sqlmap": True
            },
            "nikto": {
                "port": 80,
                "ssl": False
            },
            "sqlmap": {
                "level": 3,
                "risk": 2
            }
        }
    },
    {
        "id": "ad_audit",
        "name": "Active Directory Audit",
        "description": "Complete AD security assessment",
        "scan_type": "ad",
        "config": {
            "tools": {
                "bloodhound": True,
                "crackmapexec": True,
                "impacket": True
            },
            "bloodhound": {
                "collection_methods": ["DCOnly", "RPC", "DCOM"]
            },
            "crackmapexec": {
                "module": "smb"
            }
        }
    },
    {
        "id": "full_pentest",
        "name": "Full Pentest",
        "description": "Complete penetration test with all tools",
        "scan_type": "full",
        "config": {
            "tools": {
                "nmap": True,
                "masscan": True,
                "nikto": True,
                "sqlmap": True,
                "bloodhound": True,
                "crackmapexec": True
            }
        }
    },
    {
        "id": "wordpress_scan",
        "name": "WordPress Security Scan",
        "description": "WordPress-specific security scan",
        "scan_type": "web",
        "config": {
            "tools": {
                "wpscan": True,
                "nikto": True
            },
            "wpscan": {
                "enumerate": ["u", "p", "t"]
            }
        }
    }
]


@router.get("", response_model=List[ScanProfile])
async def list_scan_profiles():
    """List all available scan profiles"""
    return [ScanProfile(**profile) for profile in SCAN_PROFILES]


@router.get("/{profile_id}", response_model=ScanProfile)
async def get_scan_profile(profile_id: str):
    """Get a specific scan profile"""
    profile = next((p for p in SCAN_PROFILES if p["id"] == profile_id), None)
    if not profile:
        raise HTTPException(status_code=404, detail="Scan profile not found")
    return ScanProfile(**profile)
