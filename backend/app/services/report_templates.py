"""
Report templates (OWASP, PTES, custom)
"""

from typing import Dict, Any
from enum import Enum


class ReportTemplate(str, Enum):
    OWASP = "owasp"
    PTES = "ptes"
    CUSTOM = "custom"
    EXECUTIVE = "executive"
    TECHNICAL = "technical"


class ReportTemplateGenerator:
    """Generate reports using standard templates"""
    
    @staticmethod
    def get_owasp_template() -> Dict[str, Any]:
        """OWASP Testing Guide template"""
        return {
            "sections": [
                {
                    "title": "Executive Summary",
                    "required": True,
                    "order": 1
                },
                {
                    "title": "Introduction",
                    "required": True,
                    "order": 2,
                    "subsections": [
                        "Scope",
                        "Objectives",
                        "Methodology"
                    ]
                },
                {
                    "title": "Information Gathering",
                    "required": True,
                    "order": 3
                },
                {
                    "title": "Configuration and Deployment Management Testing",
                    "required": True,
                    "order": 4
                },
                {
                    "title": "Identity Management Testing",
                    "required": True,
                    "order": 5
                },
                {
                    "title": "Authentication Testing",
                    "required": True,
                    "order": 6
                },
                {
                    "title": "Authorization Testing",
                    "required": True,
                    "order": 7
                },
                {
                    "title": "Session Management Testing",
                    "required": True,
                    "order": 8
                },
                {
                    "title": "Input Validation Testing",
                    "required": True,
                    "order": 9
                },
                {
                    "title": "Error Handling",
                    "required": True,
                    "order": 10
                },
                {
                    "title": "Cryptography",
                    "required": True,
                    "order": 11
                },
                {
                    "title": "Business Logic Testing",
                    "required": True,
                    "order": 12
                },
                {
                    "title": "Client Side Testing",
                    "required": True,
                    "order": 13
                },
                {
                    "title": "API Testing",
                    "required": True,
                    "order": 14
                },
                {
                    "title": "Findings",
                    "required": True,
                    "order": 15,
                    "format": "table",
                    "columns": ["ID", "Title", "Severity", "Description", "Impact", "Recommendation"]
                },
                {
                    "title": "Risk Assessment",
                    "required": True,
                    "order": 16
                },
                {
                    "title": "Remediation Recommendations",
                    "required": True,
                    "order": 17
                },
                {
                    "title": "Appendix",
                    "required": False,
                    "order": 18,
                    "subsections": [
                        "Tools Used",
                        "References",
                        "Glossary"
                    ]
                }
            ],
            "metadata": {
                "standard": "OWASP Testing Guide v4.2",
                "version": "1.0"
            }
        }
    
    @staticmethod
    def get_ptes_template() -> Dict[str, Any]:
        """PTES (Penetration Testing Execution Standard) template"""
        return {
            "sections": [
                {
                    "title": "Executive Summary",
                    "required": True,
                    "order": 1
                },
                {
                    "title": "Pre-Engagement Interactions",
                    "required": True,
                    "order": 2,
                    "subsections": [
                        "Rules of Engagement",
                        "Scope Definition",
                        "Communication Plan"
                    ]
                },
                {
                    "title": "Intelligence Gathering",
                    "required": True,
                    "order": 3,
                    "subsections": [
                        "Passive Information Gathering",
                        "Active Information Gathering",
                        "Vulnerability Identification"
                    ]
                },
                {
                    "title": "Threat Modeling",
                    "required": True,
                    "order": 4
                },
                {
                    "title": "Vulnerability Analysis",
                    "required": True,
                    "order": 5
                },
                {
                    "title": "Exploitation",
                    "required": True,
                    "order": 6,
                    "subsections": [
                        "Initial Exploitation",
                        "Post-Exploitation",
                        "Persistence"
                    ]
                },
                {
                    "title": "Post Exploitation",
                    "required": True,
                    "order": 7,
                    "subsections": [
                        "Lateral Movement",
                        "Privilege Escalation",
                        "Data Exfiltration"
                    ]
                },
                {
                    "title": "Reporting",
                    "required": True,
                    "order": 8,
                    "subsections": [
                        "Executive Summary",
                        "Technical Report",
                        "Risk Rating",
                        "Remediation Roadmap"
                    ]
                }
            ],
            "metadata": {
                "standard": "PTES v1.1",
                "version": "1.0"
            }
        }
    
    @staticmethod
    def get_custom_template() -> Dict[str, Any]:
        """Custom template (user-defined)"""
        return {
            "sections": [
                {
                    "title": "Executive Summary",
                    "required": True,
                    "order": 1
                },
                {
                    "title": "Methodology",
                    "required": True,
                    "order": 2
                },
                {
                    "title": "Findings",
                    "required": True,
                    "order": 3
                },
                {
                    "title": "Recommendations",
                    "required": True,
                    "order": 4
                }
            ],
            "metadata": {
                "standard": "Custom",
                "version": "1.0"
            }
        }
    
    @staticmethod
    def get_template(template_type: ReportTemplate) -> Dict[str, Any]:
        """Get template by type"""
        if template_type == ReportTemplate.OWASP:
            return ReportTemplateGenerator.get_owasp_template()
        elif template_type == ReportTemplate.PTES:
            return ReportTemplateGenerator.get_ptes_template()
        elif template_type == ReportTemplate.CUSTOM:
            return ReportTemplateGenerator.get_custom_template()
        else:
            return ReportTemplateGenerator.get_custom_template()
