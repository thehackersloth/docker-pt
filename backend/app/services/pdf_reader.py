"""
PDF reading service for methodology extraction
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)


class PDFReader:
    """Read and extract content from PDF files"""
    
    def __init__(self):
        self.data_dir = Path("/data")
        self.methodology_cache = {}
    
    def read_pdf(self, pdf_path: str) -> Optional[str]:
        """Read PDF and extract text"""
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                pass
            
            # Try pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() + "\n"
                    return text
            except ImportError:
                pass
            
            # Try pdfminer
            try:
                from pdfminer.high_level import extract_text
                return extract_text(pdf_path)
            except ImportError:
                pass
            
            logger.error("No PDF reading library available. Install PyPDF2, pdfplumber, or pdfminer")
            return None
            
        except Exception as e:
            logger.error(f"Failed to read PDF {pdf_path}: {e}")
            return None
    
    def extract_methodology(self, pdf_path: str) -> Dict[str, Any]:
        """Extract methodology from PDF"""
        text = self.read_pdf(pdf_path)
        if not text:
            return {}
        
        methodology = {
            "source": Path(pdf_path).name,
            "phases": [],
            "techniques": [],
            "tools": [],
            "workflows": []
        }
        
        # Extract phases (common pentest phases)
        phase_patterns = [
            r"(?i)(reconnaissance|recon|information gathering)",
            r"(?i)(scanning|enumeration)",
            r"(?i)(exploitation|exploit)",
            r"(?i)(post.?exploitation|post.?exploit|privilege escalation)",
            r"(?i)(pivoting|lateral movement)",
            r"(?i)(persistence|maintaining access)",
            r"(?i)(reporting|documentation)"
        ]
        
        for pattern in phase_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                context = text[max(0, match.start()-100):match.end()+100]
                methodology["phases"].append({
                    "phase": match.group(1),
                    "context": context.strip()
                })
        
        # Extract tools (common pentest tools)
        tool_patterns = [
            r"(?i)\b(nmap|masscan|rustscan)\b",
            r"(?i)\b(metasploit|msfconsole|msfvenom)\b",
            r"(?i)\b(bloodhound|crackmapexec|impacket)\b",
            r"(?i)\b(sqlmap|nikto|wpscan|zap)\b",
            r"(?i)\b(hydra|john|hashcat)\b",
            r"(?i)\b(burp|burpsuite)\b"
        ]
        
        for pattern in tool_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.group(1).lower() not in [t.lower() for t in methodology["tools"]]:
                    methodology["tools"].append(match.group(1))
        
        # Extract techniques (common attack techniques)
        technique_patterns = [
            r"(?i)(sql injection|sqli|xss|cross.?site scripting)",
            r"(?i)(buffer overflow|stack overflow|heap overflow)",
            r"(?i)(privilege escalation|privesc|escalation)",
            r"(?i)(kerberos|ntlm|pass the hash|pass the ticket)",
            r"(?i)(deserialization|insecure deserialization)",
            r"(?i)(race condition|time of check|time of use)",
            r"(?i)(command injection|code injection|rce)"
        ]
        
        for pattern in technique_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.group(1).lower() not in [t.lower() for t in methodology["techniques"]]:
                    methodology["techniques"].append(match.group(1))
        
        return methodology
    
    def load_methodologies(self) -> Dict[str, Dict[str, Any]]:
        """Load methodologies from all PDFs in data directory"""
        methodologies = {}
        
        pdf_files = list(self.data_dir.glob("*.pdf"))
        for pdf_file in pdf_files:
            logger.info(f"Loading methodology from {pdf_file.name}")
            methodology = self.extract_methodology(str(pdf_file))
            if methodology:
                methodologies[pdf_file.stem] = methodology
                self.methodology_cache[pdf_file.stem] = methodology
        
        return methodologies
    
    def get_phase_workflow(self, phase: str) -> Optional[List[Dict[str, Any]]]:
        """Get workflow for a specific phase"""
        workflows = []
        
        for methodology in self.methodology_cache.values():
            for phase_data in methodology.get("phases", []):
                if phase.lower() in phase_data["phase"].lower():
                    workflows.append({
                        "source": methodology["source"],
                        "phase": phase_data["phase"],
                        "context": phase_data["context"],
                        "tools": methodology.get("tools", []),
                        "techniques": methodology.get("techniques", [])
                    })
        
        return workflows
    
    def get_tool_usage(self, tool: str) -> Optional[List[Dict[str, Any]]]:
        """Get usage examples for a tool"""
        usages = []
        
        for methodology in self.methodology_cache.values():
            if tool.lower() in [t.lower() for t in methodology.get("tools", [])]:
                usages.append({
                    "source": methodology["source"],
                    "tool": tool,
                    "context": methodology.get("phases", [])
                })
        
        return usages
