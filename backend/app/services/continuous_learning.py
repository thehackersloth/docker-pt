"""
Continuous learning service - learns from PDFs over time
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
from app.services.pdf_reader import PDFReader
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding
import hashlib

logger = logging.getLogger(__name__)


class ContinuousLearningService:
    """Continuous learning from PDFs and scan results"""
    
    def __init__(self):
        self.pdf_reader = PDFReader()
        self.learning_data_dir = Path("/data/learning")
        self.learning_data_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_base = self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load existing knowledge base"""
        kb_file = self.learning_data_dir / "knowledge_base.json"
        if kb_file.exists():
            try:
                with open(kb_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "techniques": {},
            "tools": {},
            "workflows": {},
            "patterns": {},
            "last_updated": None
        }
    
    def _save_knowledge_base(self):
        """Save knowledge base"""
        kb_file = self.learning_data_dir / "knowledge_base.json"
        self.knowledge_base["last_updated"] = datetime.utcnow().isoformat()
        with open(kb_file, 'w') as f:
            json.dump(self.knowledge_base, f, indent=2)
    
    def learn_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Learn from a PDF and update knowledge base"""
        try:
            # Extract methodology
            methodology = self.pdf_reader.extract_methodology(pdf_path)
            
            # Learn techniques
            for technique in methodology.get("techniques", []):
                if technique not in self.knowledge_base["techniques"]:
                    self.knowledge_base["techniques"][technique] = {
                        "count": 0,
                        "sources": [],
                        "contexts": [],
                        "first_seen": datetime.utcnow().isoformat()
                    }
                
                self.knowledge_base["techniques"][technique]["count"] += 1
                self.knowledge_base["techniques"][technique]["sources"].append(Path(pdf_path).name)
            
            # Learn tools
            for tool in methodology.get("tools", []):
                if tool not in self.knowledge_base["tools"]:
                    self.knowledge_base["tools"][tool] = {
                        "count": 0,
                        "sources": [],
                        "phases": [],
                        "first_seen": datetime.utcnow().isoformat()
                    }
                
                self.knowledge_base["tools"][tool]["count"] += 1
                self.knowledge_base["tools"][tool]["sources"].append(Path(pdf_path).name)
            
            # Learn workflows
            for phase in methodology.get("phases", []):
                phase_name = phase.get("phase", "")
                if phase_name:
                    if phase_name not in self.knowledge_base["workflows"]:
                        self.knowledge_base["workflows"][phase_name] = {
                            "count": 0,
                            "tools": [],
                            "techniques": [],
                            "sources": []
                        }
                    
                    self.knowledge_base["workflows"][phase_name]["count"] += 1
                    self.knowledge_base["workflows"][phase_name]["sources"].append(Path(pdf_path).name)
                    self.knowledge_base["workflows"][phase_name]["tools"].extend(methodology.get("tools", []))
                    self.knowledge_base["workflows"][phase_name]["techniques"].extend(methodology.get("techniques", []))
            
            # Save knowledge base
            self._save_knowledge_base()
            
            return {
                "learned": True,
                "techniques_added": len(methodology.get("techniques", [])),
                "tools_added": len(methodology.get("tools", [])),
                "phases_added": len(methodology.get("phases", []))
            }
            
        except Exception as e:
            logger.error(f"Learning from PDF failed: {e}")
            return {"learned": False, "error": str(e)}
    
    def learn_from_scan_results(self, scan_id: str) -> Dict[str, Any]:
        """Learn from scan results"""
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                return {"error": "Scan not found"}
            
            findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()
            
            # Learn patterns from findings
            for finding in findings:
                # Extract patterns
                if finding.cve_id:
                    if finding.cve_id not in self.knowledge_base["patterns"]:
                        self.knowledge_base["patterns"][finding.cve_id] = {
                            "count": 0,
                            "severity": finding.severity.value,
                            "tools": [],
                            "scans": []
                        }
                    
                    self.knowledge_base["patterns"][finding.cve_id]["count"] += 1
                    self.knowledge_base["patterns"][finding.cve_id]["scans"].append(scan_id)
            
            # Save knowledge base
            self._save_knowledge_base()
            
            return {
                "learned": True,
                "patterns_added": len([f for f in findings if f.cve_id])
            }
            
        finally:
            db.close()
    
    def get_learned_techniques(self) -> List[Dict[str, Any]]:
        """Get learned techniques"""
        techniques = []
        for name, data in self.knowledge_base["techniques"].items():
            techniques.append({
                "name": name,
                "count": data["count"],
                "sources": data["sources"],
                "first_seen": data.get("first_seen")
            })
        return sorted(techniques, key=lambda x: x["count"], reverse=True)
    
    def get_learned_tools(self) -> List[Dict[str, Any]]:
        """Get learned tools"""
        tools = []
        for name, data in self.knowledge_base["tools"].items():
            tools.append({
                "name": name,
                "count": data["count"],
                "sources": data["sources"],
                "phases": data.get("phases", []),
                "first_seen": data.get("first_seen")
            })
        return sorted(tools, key=lambda x: x["count"], reverse=True)
    
    def get_learned_workflows(self) -> List[Dict[str, Any]]:
        """Get learned workflows"""
        workflows = []
        for name, data in self.knowledge_base["workflows"].items():
            workflows.append({
                "phase": name,
                "count": data["count"],
                "tools": list(set(data.get("tools", []))),
                "techniques": list(set(data.get("techniques", []))),
                "sources": data.get("sources", [])
            })
        return sorted(workflows, key=lambda x: x["count"], reverse=True)
    
    def get_recommendations(self, context: str) -> List[str]:
        """Get recommendations based on learned knowledge"""
        recommendations = []
        
        # Search knowledge base for relevant techniques
        for technique, data in self.knowledge_base["techniques"].items():
            if context.lower() in technique.lower():
                recommendations.append(f"Consider using: {technique} (seen {data['count']} times)")
        
        # Search for relevant tools
        for tool, data in self.knowledge_base["tools"].items():
            if context.lower() in tool.lower():
                recommendations.append(f"Consider tool: {tool} (used {data['count']} times)")
        
        return recommendations[:5]  # Top 5 recommendations
