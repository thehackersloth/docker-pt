"""
Competitive features to beat Vohani and Horizon
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding, FindingSeverity
from app.models.asset import Asset
import json

logger = logging.getLogger(__name__)


class CompetitiveFeatures:
    """Features to make platform competitive"""
    
    def __init__(self):
        self.features = {
            "open_source": True,
            "full_automation": True,
            "ai_integration": True,
            "continuous_learning": True,
            "methodology_based": True,
            "enterprise_ready": True,
            "multi_tenant": False,  # Can be added
            "api_first": True,
            "extensible": True
        }
    
    def get_competitive_advantages(self) -> Dict[str, Any]:
        """Get competitive advantages over Vohani/Horizon"""
        return {
            "open_source": {
                "advantage": "100% open source vs proprietary",
                "benefit": "Full transparency, no vendor lock-in, community-driven"
            },
            "full_automation": {
                "advantage": "Complete automation vs manual processes",
                "benefit": "Zero manual work, faster results, consistent methodology"
            },
            "ai_powered": {
                "advantage": "AI integration vs traditional analysis",
                "benefit": "Smarter findings, better recommendations, faster analysis"
            },
            "continuous_learning": {
                "advantage": "Learns over time vs static platform",
                "benefit": "Gets smarter with each scan, adapts to new techniques"
            },
            "methodology_based": {
                "advantage": "Offensive Security methodology vs generic",
                "benefit": "Industry-standard approach, proven techniques"
            },
            "self_hosted": {
                "advantage": "Self-hosted vs cloud-only",
                "benefit": "Data privacy, no external dependencies, full control"
            },
            "extensible": {
                "advantage": "Plugin system vs closed platform",
                "benefit": "Add custom tools, integrate anything, unlimited flexibility"
            },
            "cost_effective": {
                "advantage": "Free vs expensive licenses",
                "benefit": "No per-seat costs, no subscription fees, open source"
            }
        }
    
    def get_feature_comparison(self) -> Dict[str, Any]:
        """Compare features with competitors"""
        return {
            "our_platform": {
                "open_source": True,
                "automation": "Full",
                "ai_integration": "Yes (multiple providers)",
                "learning": "Continuous",
                "methodology": "Offensive Security",
                "hosting": "Self-hosted",
                "cost": "Free",
                "extensibility": "Unlimited",
                "api": "REST + WebSocket",
                "reporting": "Multi-format",
                "scheduling": "Yes",
                "email_reports": "Yes",
                "integrations": "SIEM, Ticketing, Webhooks",
                "authentication": "Multiple (OAuth, LDAP, JWT)",
                "analytics": "Advanced"
            },
            "vohani": {
                "open_source": False,
                "automation": "Partial",
                "ai_integration": "Limited",
                "learning": "No",
                "methodology": "Generic",
                "hosting": "Cloud",
                "cost": "$$$",
                "extensibility": "Limited",
                "api": "Limited",
                "reporting": "Basic",
                "scheduling": "Yes",
                "email_reports": "Yes",
                "integrations": "Limited",
                "authentication": "Basic",
                "analytics": "Basic"
            },
            "horizon": {
                "open_source": False,
                "automation": "Partial",
                "ai_integration": "No",
                "learning": "No",
                "methodology": "Generic",
                "hosting": "Cloud",
                "cost": "$$$",
                "extensibility": "Limited",
                "api": "Limited",
                "reporting": "Basic",
                "scheduling": "Yes",
                "email_reports": "Yes",
                "integrations": "Limited",
                "authentication": "Basic",
                "analytics": "Basic"
            }
        }
