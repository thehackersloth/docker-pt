"""
Compliance mapping API - Map findings to compliance frameworks
PCI-DSS, HIPAA, NIST, SOC2, ISO27001, OWASP
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.core.database import get_db
from app.models.finding import Finding
from sqlalchemy.orm import Session

router = APIRouter()


# Compliance framework definitions
COMPLIANCE_FRAMEWORKS = {
    "PCI-DSS": {
        "name": "PCI-DSS v4.0",
        "description": "Payment Card Industry Data Security Standard",
        "requirements": {
            "1.1": "Install and maintain network security controls",
            "1.2": "Network security controls are configured and maintained",
            "2.1": "Secure configurations for system components",
            "2.2": "System components are securely configured",
            "3.1": "Account data storage is kept to minimum",
            "3.2": "Sensitive authentication data not stored after authorization",
            "4.1": "Strong cryptography for transmission of cardholder data",
            "5.1": "Anti-malware mechanisms are deployed",
            "5.2": "Malware is prevented or detected and addressed",
            "6.1": "Secure software development processes",
            "6.2": "Bespoke and custom software is developed securely",
            "6.3": "Security vulnerabilities are identified and addressed",
            "6.4": "Public-facing web applications are protected",
            "7.1": "Access to system components is limited",
            "7.2": "Access to system components is appropriately defined",
            "8.1": "User identification and related accounts managed",
            "8.2": "User authentication managed for users and administrators",
            "8.3": "Strong authentication for users and administrators",
            "9.1": "Physical access to cardholder data is restricted",
            "10.1": "Logging and monitoring mechanisms are in place",
            "10.2": "Audit logs implemented to support detection",
            "11.1": "Security of wireless access points",
            "11.2": "External and internal vulnerabilities identified",
            "11.3": "Penetration testing performed regularly",
            "12.1": "Information security policy established",
        }
    },
    "HIPAA": {
        "name": "HIPAA Security Rule",
        "description": "Health Insurance Portability and Accountability Act",
        "requirements": {
            "164.308(a)(1)": "Security Management Process",
            "164.308(a)(3)": "Workforce Security",
            "164.308(a)(4)": "Information Access Management",
            "164.308(a)(5)": "Security Awareness Training",
            "164.308(a)(6)": "Security Incident Procedures",
            "164.308(a)(7)": "Contingency Plan",
            "164.308(a)(8)": "Evaluation",
            "164.310(a)(1)": "Facility Access Controls",
            "164.310(b)": "Workstation Use",
            "164.310(c)": "Workstation Security",
            "164.310(d)(1)": "Device and Media Controls",
            "164.312(a)(1)": "Access Control",
            "164.312(b)": "Audit Controls",
            "164.312(c)(1)": "Integrity",
            "164.312(d)": "Person or Entity Authentication",
            "164.312(e)(1)": "Transmission Security",
        }
    },
    "NIST-CSF": {
        "name": "NIST Cybersecurity Framework",
        "description": "National Institute of Standards and Technology CSF",
        "requirements": {
            "ID.AM": "Asset Management",
            "ID.BE": "Business Environment",
            "ID.GV": "Governance",
            "ID.RA": "Risk Assessment",
            "ID.RM": "Risk Management Strategy",
            "ID.SC": "Supply Chain Risk Management",
            "PR.AC": "Identity Management and Access Control",
            "PR.AT": "Awareness and Training",
            "PR.DS": "Data Security",
            "PR.IP": "Information Protection Processes",
            "PR.MA": "Maintenance",
            "PR.PT": "Protective Technology",
            "DE.AE": "Anomalies and Events",
            "DE.CM": "Security Continuous Monitoring",
            "DE.DP": "Detection Processes",
            "RS.RP": "Response Planning",
            "RS.CO": "Communications",
            "RS.AN": "Analysis",
            "RS.MI": "Mitigation",
            "RS.IM": "Improvements",
            "RC.RP": "Recovery Planning",
            "RC.IM": "Improvements",
            "RC.CO": "Communications",
        }
    },
    "SOC2": {
        "name": "SOC 2 Type II",
        "description": "Service Organization Control 2",
        "requirements": {
            "CC1": "Control Environment",
            "CC2": "Communication and Information",
            "CC3": "Risk Assessment",
            "CC4": "Monitoring Activities",
            "CC5": "Control Activities",
            "CC6": "Logical and Physical Access",
            "CC7": "System Operations",
            "CC8": "Change Management",
            "CC9": "Risk Mitigation",
            "A1": "Availability",
            "C1": "Confidentiality",
            "PI1": "Processing Integrity",
            "P1": "Privacy",
        }
    },
    "ISO27001": {
        "name": "ISO/IEC 27001:2022",
        "description": "Information Security Management System",
        "requirements": {
            "A.5": "Organizational Controls",
            "A.6": "People Controls",
            "A.7": "Physical Controls",
            "A.8": "Technological Controls",
            "A.5.1": "Policies for information security",
            "A.5.7": "Threat intelligence",
            "A.5.23": "Information security for cloud services",
            "A.8.2": "Privileged access rights",
            "A.8.3": "Information access restriction",
            "A.8.5": "Secure authentication",
            "A.8.7": "Protection against malware",
            "A.8.8": "Management of technical vulnerabilities",
            "A.8.9": "Configuration management",
            "A.8.12": "Data leakage prevention",
            "A.8.15": "Logging",
            "A.8.16": "Monitoring activities",
            "A.8.20": "Networks security",
            "A.8.24": "Use of cryptography",
            "A.8.25": "Secure development life cycle",
            "A.8.28": "Secure coding",
        }
    },
    "OWASP": {
        "name": "OWASP Top 10 (2021)",
        "description": "Open Web Application Security Project Top 10",
        "requirements": {
            "A01": "Broken Access Control",
            "A02": "Cryptographic Failures",
            "A03": "Injection",
            "A04": "Insecure Design",
            "A05": "Security Misconfiguration",
            "A06": "Vulnerable and Outdated Components",
            "A07": "Identification and Authentication Failures",
            "A08": "Software and Data Integrity Failures",
            "A09": "Security Logging and Monitoring Failures",
            "A10": "Server-Side Request Forgery",
        }
    }
}

# Vulnerability to compliance mapping
VULN_COMPLIANCE_MAP = {
    # SQL Injection
    "sql injection": ["PCI-DSS:6.3", "OWASP:A03", "HIPAA:164.312(a)(1)", "ISO27001:A.8.28"],
    "sqli": ["PCI-DSS:6.3", "OWASP:A03", "HIPAA:164.312(a)(1)", "ISO27001:A.8.28"],

    # XSS
    "cross-site scripting": ["PCI-DSS:6.4", "OWASP:A03", "ISO27001:A.8.28"],
    "xss": ["PCI-DSS:6.4", "OWASP:A03", "ISO27001:A.8.28"],

    # Authentication
    "authentication": ["PCI-DSS:8.2", "OWASP:A07", "HIPAA:164.312(d)", "ISO27001:A.8.5"],
    "weak password": ["PCI-DSS:8.3", "OWASP:A07", "HIPAA:164.312(d)", "ISO27001:A.8.5"],
    "default credentials": ["PCI-DSS:2.1", "OWASP:A07", "ISO27001:A.8.5"],
    "brute force": ["PCI-DSS:8.3", "OWASP:A07", "ISO27001:A.8.5"],

    # Access Control
    "unauthorized access": ["PCI-DSS:7.1", "OWASP:A01", "HIPAA:164.312(a)(1)", "ISO27001:A.8.3"],
    "privilege escalation": ["PCI-DSS:7.2", "OWASP:A01", "HIPAA:164.312(a)(1)", "ISO27001:A.8.2"],
    "idor": ["OWASP:A01", "ISO27001:A.8.3"],

    # Cryptography
    "weak encryption": ["PCI-DSS:4.1", "OWASP:A02", "HIPAA:164.312(e)(1)", "ISO27001:A.8.24"],
    "ssl": ["PCI-DSS:4.1", "OWASP:A02", "HIPAA:164.312(e)(1)", "ISO27001:A.8.24"],
    "tls": ["PCI-DSS:4.1", "OWASP:A02", "HIPAA:164.312(e)(1)", "ISO27001:A.8.24"],
    "certificate": ["PCI-DSS:4.1", "OWASP:A02", "ISO27001:A.8.24"],

    # Configuration
    "misconfiguration": ["PCI-DSS:2.2", "OWASP:A05", "ISO27001:A.8.9"],
    "default configuration": ["PCI-DSS:2.2", "OWASP:A05", "ISO27001:A.8.9"],
    "information disclosure": ["PCI-DSS:3.1", "OWASP:A05", "ISO27001:A.8.12"],

    # Outdated Software
    "outdated": ["PCI-DSS:6.3", "OWASP:A06", "ISO27001:A.8.8"],
    "vulnerable version": ["PCI-DSS:6.3", "OWASP:A06", "ISO27001:A.8.8"],
    "cve": ["PCI-DSS:6.3", "OWASP:A06", "ISO27001:A.8.8"],

    # Logging
    "logging": ["PCI-DSS:10.1", "OWASP:A09", "HIPAA:164.312(b)", "ISO27001:A.8.15"],
    "audit": ["PCI-DSS:10.2", "OWASP:A09", "HIPAA:164.312(b)", "ISO27001:A.8.15"],

    # SSRF
    "ssrf": ["OWASP:A10", "ISO27001:A.8.28"],
    "server-side request": ["OWASP:A10", "ISO27001:A.8.28"],

    # Network
    "open port": ["PCI-DSS:1.2", "NIST-CSF:PR.PT", "ISO27001:A.8.20"],
    "firewall": ["PCI-DSS:1.1", "NIST-CSF:PR.PT", "ISO27001:A.8.20"],
    "network segmentation": ["PCI-DSS:1.2", "HIPAA:164.310(a)(1)", "ISO27001:A.8.20"],

    # Malware
    "malware": ["PCI-DSS:5.1", "NIST-CSF:DE.CM", "ISO27001:A.8.7"],
    "antivirus": ["PCI-DSS:5.2", "ISO27001:A.8.7"],
}


class ComplianceMapping(BaseModel):
    framework: str
    requirement_id: str
    requirement_name: str
    finding_count: int
    findings: List[str]


class ComplianceReport(BaseModel):
    framework: str
    framework_name: str
    description: str
    total_requirements: int
    affected_requirements: int
    compliance_score: float
    mappings: List[ComplianceMapping]


@router.get("/frameworks")
async def list_frameworks():
    """List available compliance frameworks"""
    return [
        {
            "id": key,
            "name": value["name"],
            "description": value["description"],
            "requirement_count": len(value["requirements"])
        }
        for key, value in COMPLIANCE_FRAMEWORKS.items()
    ]


@router.get("/frameworks/{framework_id}")
async def get_framework(framework_id: str):
    """Get details of a specific compliance framework"""
    if framework_id not in COMPLIANCE_FRAMEWORKS:
        raise HTTPException(status_code=404, detail="Framework not found")

    framework = COMPLIANCE_FRAMEWORKS[framework_id]
    return {
        "id": framework_id,
        "name": framework["name"],
        "description": framework["description"],
        "requirements": [
            {"id": k, "name": v}
            for k, v in framework["requirements"].items()
        ]
    }


@router.get("/map-finding/{finding_id}")
async def map_finding_to_compliance(finding_id: str, db: Session = Depends(get_db)):
    """Map a specific finding to compliance requirements"""
    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Find matching compliance requirements
    mappings = []
    search_text = f"{finding.title} {finding.description}".lower()

    for keyword, requirements in VULN_COMPLIANCE_MAP.items():
        if keyword in search_text:
            for req in requirements:
                framework, req_id = req.split(":")
                if framework in COMPLIANCE_FRAMEWORKS:
                    req_name = COMPLIANCE_FRAMEWORKS[framework]["requirements"].get(req_id, "Unknown")
                    mappings.append({
                        "framework": framework,
                        "framework_name": COMPLIANCE_FRAMEWORKS[framework]["name"],
                        "requirement_id": req_id,
                        "requirement_name": req_name,
                        "matched_keyword": keyword
                    })

    # Remove duplicates
    seen = set()
    unique_mappings = []
    for m in mappings:
        key = f"{m['framework']}:{m['requirement_id']}"
        if key not in seen:
            seen.add(key)
            unique_mappings.append(m)

    return {
        "finding_id": finding_id,
        "finding_title": finding.title,
        "compliance_mappings": unique_mappings
    }


@router.get("/report/{scan_id}")
async def generate_compliance_report(
    scan_id: str,
    framework: str = "PCI-DSS",
    db: Session = Depends(get_db)
):
    """Generate compliance report for a scan"""
    if framework not in COMPLIANCE_FRAMEWORKS:
        raise HTTPException(status_code=404, detail="Framework not found")

    findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()

    # Map findings to requirements
    requirement_findings: Dict[str, List[str]] = {}

    for finding in findings:
        search_text = f"{finding.title} {finding.description}".lower()

        for keyword, requirements in VULN_COMPLIANCE_MAP.items():
            if keyword in search_text:
                for req in requirements:
                    fw, req_id = req.split(":")
                    if fw == framework:
                        if req_id not in requirement_findings:
                            requirement_findings[req_id] = []
                        if str(finding.id) not in requirement_findings[req_id]:
                            requirement_findings[req_id].append(str(finding.id))

    fw_data = COMPLIANCE_FRAMEWORKS[framework]
    total_requirements = len(fw_data["requirements"])
    affected_requirements = len(requirement_findings)

    # Calculate compliance score (requirements without findings / total)
    compliant_requirements = total_requirements - affected_requirements
    compliance_score = (compliant_requirements / total_requirements * 100) if total_requirements > 0 else 100

    mappings = []
    for req_id, finding_ids in requirement_findings.items():
        mappings.append(ComplianceMapping(
            framework=framework,
            requirement_id=req_id,
            requirement_name=fw_data["requirements"].get(req_id, "Unknown"),
            finding_count=len(finding_ids),
            findings=finding_ids
        ))

    return ComplianceReport(
        framework=framework,
        framework_name=fw_data["name"],
        description=fw_data["description"],
        total_requirements=total_requirements,
        affected_requirements=affected_requirements,
        compliance_score=round(compliance_score, 1),
        mappings=sorted(mappings, key=lambda x: x.finding_count, reverse=True)
    )


@router.get("/report/{scan_id}/all")
async def generate_all_compliance_reports(scan_id: str, db: Session = Depends(get_db)):
    """Generate compliance reports for all frameworks"""
    reports = []
    for framework in COMPLIANCE_FRAMEWORKS.keys():
        report = await generate_compliance_report(scan_id, framework, db)
        reports.append(report)

    return {
        "scan_id": scan_id,
        "reports": reports,
        "summary": {
            fw: next((r.compliance_score for r in reports if r.framework == fw), 0)
            for fw in COMPLIANCE_FRAMEWORKS.keys()
        }
    }
