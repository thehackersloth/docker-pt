# Tool runners
"""
Tool Runner Factory and Registry

This module provides a centralized factory for instantiating tool runners
and a registry of all available pentesting tools for automated penetration testing.
"""

from typing import Dict, Type, Optional, List
import logging

from app.services.tool_runners.base_runner import BaseToolRunner

# Network Scanning
from app.services.tool_runners.nmap_runner import NmapRunner
from app.services.tool_runners.masscan_runner import MasscanRunner
from app.services.tool_runners.rustscan_runner import RustScanRunner

# Web Scanning
from app.services.tool_runners.nikto_runner import NiktoRunner
from app.services.tool_runners.wpscan_runner import WPScanRunner
from app.services.tool_runners.zap_runner import ZAPRunner
from app.services.tool_runners.burp_runner import BurpRunner
from app.services.tool_runners.whatweb_runner import WhatWebRunner

# Web Fuzzing
from app.services.tool_runners.web_fuzzer_runner import WebFuzzerRunner
from app.services.tool_runners.feroxbuster_runner import FeroxbusterRunner

# SQL Injection
from app.services.tool_runners.sqlmap_runner import SQLMapRunner

# Vulnerability Scanning
from app.services.tool_runners.nuclei_runner import NucleiRunner

# SSL/TLS Testing
from app.services.tool_runners.sslscan_runner import SSLScanRunner
from app.services.tool_runners.testssl_runner import TestSSLRunner

# Active Directory
from app.services.tool_runners.bloodhound_runner import BloodHoundRunner
from app.services.tool_runners.crackmapexec_runner import CrackMapExecRunner
from app.services.tool_runners.netexec_runner import NetExecRunner
from app.services.tool_runners.kerbrute_runner import KerbruteRunner
from app.services.tool_runners.enum4linux_runner import Enum4linuxRunner
from app.services.tool_runners.ldapsearch_runner import LdapSearchRunner
from app.services.tool_runners.smbmap_runner import SMBMapRunner

# Credential Attacks
from app.services.tool_runners.hydra_runner import HydraRunner
from app.services.tool_runners.medusa_runner import MedusaRunner
from app.services.tool_runners.john_runner import JohnRunner
from app.services.tool_runners.hashcat_runner import HashcatRunner
from app.services.tool_runners.secretsdump_runner import SecretsDumpRunner

# Post-Exploitation
from app.services.tool_runners.metasploit_runner import MetasploitRunner
from app.services.tool_runners.empire_runner import EmpireRunner
from app.services.tool_runners.impacket_runner import ImpacketRunner
from app.services.tool_runners.evilwinrm_runner import EvilWinRMRunner

# Network Poisoning
from app.services.tool_runners.responder_runner import ResponderRunner

# Recon/OSINT
from app.services.tool_runners.theharvester_runner import TheHarvesterRunner
from app.services.tool_runners.amass_runner import AmassRunner
from app.services.tool_runners.subfinder_runner import SubfinderRunner

# Pivoting
from app.services.tool_runners.chisel_runner import ChiselRunner
from app.services.tool_runners.ligolo_runner import LigoloRunner

# Privilege Escalation
from app.services.tool_runners.linpeas_runner import LinPEASRunner
from app.services.tool_runners.winpeas_runner import WinPEASRunner
from app.services.tool_runners.pspy_runner import PspyRunner
from app.services.tool_runners.linux_exploit_suggester_runner import LinuxExploitSuggesterRunner

logger = logging.getLogger(__name__)


# Tool categories for organization
TOOL_CATEGORIES = {
    "network_scanning": ["nmap", "masscan", "rustscan"],
    "web_scanning": ["nikto", "wpscan", "zap", "burp", "whatweb"],
    "web_fuzzing": ["ffuf", "wfuzz", "gobuster", "feroxbuster"],
    "sql_injection": ["sqlmap"],
    "vulnerability_scanning": ["nuclei", "nmap_vuln"],
    "ssl_tls": ["sslscan", "testssl", "sslyze"],
    "active_directory": ["bloodhound", "crackmapexec", "netexec", "kerbrute", "enum4linux", "ldapsearch", "smbmap"],
    "credential_attacks": ["hydra", "medusa", "john", "hashcat", "secretsdump"],
    "post_exploitation": ["metasploit", "empire", "impacket", "evilwinrm"],
    "network_poisoning": ["responder"],
    "recon_osint": ["theharvester", "amass", "subfinder"],
    "pivoting": ["chisel", "ligolo"],
    "privilege_escalation": ["linpeas", "winpeas", "pspy", "linux-exploit-suggester"],
}


# Tool registry - maps tool names to runner classes
TOOL_REGISTRY: Dict[str, Type[BaseToolRunner]] = {
    # Network Scanning
    "nmap": NmapRunner,
    "masscan": MasscanRunner,
    "rustscan": RustScanRunner,

    # Web Scanning
    "nikto": NiktoRunner,
    "wpscan": WPScanRunner,
    "zap": ZAPRunner,
    "owasp-zap": ZAPRunner,
    "burp": BurpRunner,
    "whatweb": WhatWebRunner,

    # Web Fuzzing
    "ffuf": WebFuzzerRunner,
    "wfuzz": WebFuzzerRunner,
    "gobuster": WebFuzzerRunner,
    "feroxbuster": FeroxbusterRunner,

    # SQL Injection
    "sqlmap": SQLMapRunner,

    # Vulnerability Scanning
    "nuclei": NucleiRunner,

    # SSL/TLS Testing
    "sslscan": SSLScanRunner,
    "testssl": TestSSLRunner,
    "sslyze": SSLScanRunner,

    # Active Directory
    "bloodhound": BloodHoundRunner,
    "crackmapexec": CrackMapExecRunner,
    "cme": CrackMapExecRunner,
    "netexec": NetExecRunner,
    "nxc": NetExecRunner,
    "kerbrute": KerbruteRunner,
    "enum4linux": Enum4linuxRunner,
    "enum4linux-ng": Enum4linuxRunner,
    "ldapsearch": LdapSearchRunner,
    "smbmap": SMBMapRunner,

    # Credential Attacks
    "hydra": HydraRunner,
    "medusa": MedusaRunner,
    "john": JohnRunner,
    "john-the-ripper": JohnRunner,
    "hashcat": HashcatRunner,
    "secretsdump": SecretsDumpRunner,

    # Post-Exploitation
    "metasploit": MetasploitRunner,
    "msfconsole": MetasploitRunner,
    "empire": EmpireRunner,
    "impacket": ImpacketRunner,
    "evilwinrm": EvilWinRMRunner,
    "evil-winrm": EvilWinRMRunner,

    # Network Poisoning
    "responder": ResponderRunner,

    # Recon/OSINT
    "theharvester": TheHarvesterRunner,
    "amass": AmassRunner,
    "subfinder": SubfinderRunner,

    # Pivoting
    "chisel": ChiselRunner,
    "ligolo": LigoloRunner,
    "ligolo-ng": LigoloRunner,

    # Privilege Escalation
    "linpeas": LinPEASRunner,
    "winpeas": WinPEASRunner,
    "pspy": PspyRunner,
    "linux-exploit-suggester": LinuxExploitSuggesterRunner,
    "les": LinuxExploitSuggesterRunner,
}


class ToolRunnerFactory:
    """Factory for creating tool runner instances"""

    @staticmethod
    def get_runner(tool_name: str, scan_id: str, **kwargs) -> Optional[BaseToolRunner]:
        """
        Get a tool runner instance by name

        Args:
            tool_name: Name of the tool (e.g., 'nmap', 'sqlmap')
            scan_id: Unique identifier for this scan
            **kwargs: Additional arguments to pass to the runner

        Returns:
            BaseToolRunner instance or None if tool not found
        """
        tool_name_lower = tool_name.lower().replace('_', '-')

        if tool_name_lower not in TOOL_REGISTRY:
            logger.warning(f"Unknown tool: {tool_name}")
            return None

        runner_class = TOOL_REGISTRY[tool_name_lower]

        try:
            # Handle tools that need the tool name passed (like WebFuzzerRunner)
            if runner_class == WebFuzzerRunner:
                return runner_class(scan_id, tool=tool_name_lower)
            elif runner_class == SSLScanRunner:
                return runner_class(scan_id, tool=tool_name_lower)
            else:
                return runner_class(scan_id)
        except Exception as e:
            logger.error(f"Failed to instantiate runner for {tool_name}: {e}")
            return None

    @staticmethod
    def list_tools() -> List[str]:
        """List all available tool names"""
        return sorted(list(set(TOOL_REGISTRY.keys())))

    @staticmethod
    def get_tools_by_category(category: str) -> List[str]:
        """Get tools by category"""
        return TOOL_CATEGORIES.get(category, [])

    @staticmethod
    def list_categories() -> List[str]:
        """List all tool categories"""
        return list(TOOL_CATEGORIES.keys())

    @staticmethod
    def get_tool_info(tool_name: str) -> Optional[Dict]:
        """Get information about a tool"""
        tool_name_lower = tool_name.lower().replace('_', '-')

        if tool_name_lower not in TOOL_REGISTRY:
            return None

        # Find category
        category = None
        for cat, tools in TOOL_CATEGORIES.items():
            if tool_name_lower in tools:
                category = cat
                break

        return {
            "name": tool_name_lower,
            "category": category,
            "runner_class": TOOL_REGISTRY[tool_name_lower].__name__,
        }

    @staticmethod
    def get_all_tool_info() -> List[Dict]:
        """Get information about all tools"""
        tools = []
        seen = set()

        for tool_name, runner_class in TOOL_REGISTRY.items():
            class_name = runner_class.__name__
            if class_name in seen:
                continue
            seen.add(class_name)

            category = None
            for cat, cat_tools in TOOL_CATEGORIES.items():
                if tool_name in cat_tools:
                    category = cat
                    break

            tools.append({
                "name": tool_name,
                "category": category,
                "runner_class": class_name,
            })

        return tools


# Export all runners and factory
__all__ = [
    # Base
    "BaseToolRunner",
    "ToolRunnerFactory",
    "TOOL_REGISTRY",
    "TOOL_CATEGORIES",

    # Network Scanning
    "NmapRunner",
    "MasscanRunner",
    "RustScanRunner",

    # Web Scanning
    "NiktoRunner",
    "WPScanRunner",
    "ZAPRunner",
    "BurpRunner",
    "WhatWebRunner",

    # Web Fuzzing
    "WebFuzzerRunner",
    "FeroxbusterRunner",

    # SQL Injection
    "SQLMapRunner",

    # Vulnerability Scanning
    "NucleiRunner",

    # SSL/TLS
    "SSLScanRunner",
    "TestSSLRunner",

    # Active Directory
    "BloodHoundRunner",
    "CrackMapExecRunner",
    "NetExecRunner",
    "KerbruteRunner",
    "Enum4linuxRunner",
    "LdapSearchRunner",
    "SMBMapRunner",

    # Credential Attacks
    "HydraRunner",
    "MedusaRunner",
    "JohnRunner",
    "HashcatRunner",
    "SecretsDumpRunner",

    # Post-Exploitation
    "MetasploitRunner",
    "EmpireRunner",
    "ImpacketRunner",
    "EvilWinRMRunner",

    # Network Poisoning
    "ResponderRunner",

    # Recon/OSINT
    "TheHarvesterRunner",
    "AmassRunner",
    "SubfinderRunner",

    # Pivoting
    "ChiselRunner",
    "LigoloRunner",

    # Privilege Escalation
    "LinPEASRunner",
    "WinPEASRunner",
    "PspyRunner",
    "LinuxExploitSuggesterRunner",
]
