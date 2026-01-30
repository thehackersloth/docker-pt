"""
Pentesting methodology service based on Offensive Security materials
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.services.pdf_reader import PDFReader
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanType
from app.models.finding import Finding

logger = logging.getLogger(__name__)


class MethodologyService:
    """Service to apply pentesting methodologies"""
    
    def __init__(self):
        self.pdf_reader = PDFReader()
        self.methodologies = {}
        self._load_methodologies()
    
    def _load_methodologies(self):
        """Load methodologies from PDFs"""
        try:
            self.methodologies = self.pdf_reader.load_methodologies()
            logger.info(f"Loaded {len(self.methodologies)} methodologies")
        except Exception as e:
            logger.error(f"Failed to load methodologies: {e}")
    
    def get_scan_phases(self, scan_type: ScanType) -> List[Dict[str, Any]]:
        """Get recommended phases for scan type"""
        phases = []
        
        if scan_type == ScanType.NETWORK:
            phases = [
                {
                    "phase": "Reconnaissance",
                    "order": 1,
                    "description": "Information gathering and target identification",
                    "tools": ["nmap", "masscan", "theharvester"],
                    "techniques": ["port scanning", "service enumeration", "OS detection"]
                },
                {
                    "phase": "Vulnerability Scanning",
                    "order": 2,
                    "description": "Identify vulnerabilities in discovered services",
                    "tools": ["nmap", "nuclei", "openvas"],
                    "techniques": ["vulnerability scanning", "version detection"]
                },
                {
                    "phase": "Exploitation",
                    "order": 3,
                    "description": "Attempt to exploit identified vulnerabilities",
                    "tools": ["metasploit", "exploitdb"],
                    "techniques": ["exploit development", "payload generation"]
                }
            ]
        elif scan_type == ScanType.WEB:
            phases = [
                {
                    "phase": "Reconnaissance",
                    "order": 1,
                    "description": "Web application discovery and enumeration",
                    "tools": ["nikto", "whatweb", "wafw00f"],
                    "techniques": ["web enumeration", "technology detection"]
                },
                {
                    "phase": "Vulnerability Assessment",
                    "order": 2,
                    "description": "Identify web application vulnerabilities",
                    "tools": ["sqlmap", "zap", "burp"],
                    "techniques": ["sql injection", "xss", "csrf", "authentication bypass"]
                },
                {
                    "phase": "Exploitation",
                    "order": 3,
                    "description": "Exploit web vulnerabilities",
                    "tools": ["sqlmap", "metasploit"],
                    "techniques": ["sql injection", "command injection", "file upload"]
                }
            ]
        elif scan_type == ScanType.AD:
            phases = [
                {
                    "phase": "Reconnaissance",
                    "order": 1,
                    "description": "Active Directory enumeration",
                    "tools": ["bloodhound", "crackmapexec", "impacket"],
                    "techniques": ["domain enumeration", "user enumeration", "group enumeration"]
                },
                {
                    "phase": "Credential Harvesting",
                    "order": 2,
                    "description": "Collect credentials and hashes",
                    "tools": ["responder", "impacket", "mimikatz"],
                    "techniques": ["ntlm relay", "kerberoasting", "asreproasting"]
                },
                {
                    "phase": "Lateral Movement",
                    "order": 3,
                    "description": "Move through the network",
                    "tools": ["crackmapexec", "impacket", "bloodhound"],
                    "techniques": ["pass the hash", "pass the ticket", "dcom", "wmi"]
                },
                {
                    "phase": "Privilege Escalation",
                    "order": 4,
                    "description": "Escalate privileges to domain admin",
                    "tools": ["bloodhound", "impacket", "mimikatz"],
                    "techniques": ["dcsync", "golden ticket", "silver ticket"]
                }
            ]
        
        # Enhance with methodology from PDFs
        for phase in phases:
            phase_name = phase["phase"]
            workflows = self.pdf_reader.get_phase_workflow(phase_name)
            if workflows:
                phase["methodology_sources"] = [w["source"] for w in workflows]
                phase["additional_tools"] = []
                phase["additional_techniques"] = []
                for workflow in workflows:
                    phase["additional_tools"].extend(workflow.get("tools", []))
                    phase["additional_techniques"].extend(workflow.get("techniques", []))
        
        return phases
    
    def get_tool_command(self, tool: str, phase: str, target: str) -> Optional[str]:
        """Get recommended command for tool based on methodology"""
        commands = {
            "nmap": {
                "reconnaissance": f"nmap -sS -sV -O {target}",
                "vulnerability": f"nmap -sS -sV --script vuln {target}",
                "exploitation": f"nmap -sS -sV --script exploit {target}"
            },
            "sqlmap": {
                "vulnerability": f"sqlmap -u {target} --batch --crawl=2",
                "exploitation": f"sqlmap -u {target} --batch --dbs --tables --dump"
            },
            "bloodhound": {
                "reconnaissance": "bloodhound-python -d DOMAIN -u USER -p PASS -gc DC -c DCOnly",
                "analysis": "bloodhound --no-sandbox"
            },
            "crackmapexec": {
                "reconnaissance": f"crackmapexec smb {target}",
                "credential": f"crackmapexec smb {target} -u USER -p PASS -M lsassy"
            }
        }
        
        return commands.get(tool, {}).get(phase.lower(), None)
    
    def apply_methodology_to_scan(self, scan_id: str) -> Dict[str, Any]:
        """Apply methodology to a scan"""
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                return {"error": "Scan not found"}
            
            phases = self.get_scan_phases(scan.scan_type)
            
            return {
                "scan_id": scan_id,
                "scan_type": scan.scan_type.value,
                "recommended_phases": phases,
                "methodology_sources": list(self.methodologies.keys())
            }
        finally:
            db.close()
    
    def get_exploitation_workflow(self, finding: Finding) -> Optional[Dict[str, Any]]:
        """Get exploitation workflow for a finding"""
        # Match finding to methodology
        workflow = {
            "finding_id": str(finding.id),
            "title": finding.title,
            "severity": finding.severity.value,
            "recommended_tools": [],
            "recommended_techniques": [],
            "steps": []
        }
        
        # Search methodologies for relevant techniques
        for methodology in self.methodologies.values():
            for technique in methodology.get("techniques", []):
                if technique.lower() in finding.title.lower() or technique.lower() in (finding.description or "").lower():
                    workflow["recommended_techniques"].append(technique)
                    workflow["recommended_tools"].extend(methodology.get("tools", []))
        
        # Add exploitation steps based on severity
        if finding.severity.value in ["CRITICAL", "HIGH"]:
            workflow["steps"] = [
                "1. Verify the vulnerability",
                "2. Develop or locate exploit",
                "3. Test exploit in safe environment",
                "4. Execute exploit against target",
                "5. Establish persistence if successful",
                "6. Document findings and evidence"
            ]
        
        return workflow
