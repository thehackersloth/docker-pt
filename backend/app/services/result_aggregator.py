"""
Result aggregation service
Aggregates results from multiple tools and creates findings
"""

import logging
from typing import Dict, List, Any
from app.core.database import SessionLocal
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.asset import Asset, AssetType
from datetime import datetime

logger = logging.getLogger(__name__)


class ResultAggregator:
    """Aggregates scan results and creates findings"""
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.db = SessionLocal()
    
    def aggregate(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate results from all tools and create findings
        """
        logger.info(f"Aggregating results for scan {self.scan_id}")
        
        aggregated = {
            "tools": list(results.keys()),
            "findings": [],
            "assets": [],
            "summary": {
                "total_findings": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
            }
        }
        
        # Process each tool's results
        for tool_name, tool_results in results.items():
            if tool_name == "nmap":
                findings, assets = self._process_nmap_results(tool_results)
                aggregated["findings"].extend(findings)
                aggregated["assets"].extend(assets)
        
        # Update summary
        for finding in aggregated["findings"]:
            severity = finding.get("severity", "info")
            aggregated["summary"][severity] += 1
            aggregated["summary"]["total_findings"] += 1
        
        # Create findings in database
        self._create_findings(aggregated["findings"])
        
        # Create/update assets
        self._create_assets(aggregated["assets"])
        
        return aggregated
    
    def _process_nmap_results(self, nmap_results: Dict[str, Any]) -> tuple:
        """Process nmap results and create findings"""
        findings = []
        assets = []
        
        if not nmap_results.get("success"):
            return findings, assets
        
        for host in nmap_results.get("hosts", []):
            address = host.get("address")
            if not address:
                continue
            
            # Create/update asset
            hostnames = host.get("hostnames", [])
            asset_name = hostnames[0] if hostnames else address
            asset = {
                "name": asset_name,
                "identifier": address,
                "asset_type": AssetType.HOST,
                "properties": {
                    "hostnames": hostnames,
                    "os": host.get("os"),
                    "status": host.get("status"),
                }
            }
            assets.append(asset)
            
            # Create findings for open ports
            for port in host.get("ports", []):
                if port.get("state") == "open":
                    finding = {
                        "title": f"Open Port {port.get('port')}/{port.get('protocol')} on {address}",
                        "description": f"Port {port.get('port')}/{port.get('protocol')} is open on {address}",
                        "severity": FindingSeverity.INFO,
                        "target": address,
                        "port": port.get("port"),
                        "protocol": port.get("protocol"),
                        "service": port.get("service", {}).get("name"),
                        "tool_name": "nmap",
                        "tool_output": port,
                    }
                    findings.append(finding)
        
        return findings, assets
    
    def _create_findings(self, findings: List[Dict[str, Any]]):
        """Create finding records in database"""
        for finding_data in findings:
            finding = Finding(
                scan_id=self.scan_id,
                **finding_data
            )
            self.db.add(finding)
        
        self.db.commit()
    
    def _create_assets(self, assets: List[Dict[str, Any]]):
        """Create/update asset records"""
        for asset_data in assets:
            # Check if asset exists
            existing = self.db.query(Asset).filter(
                Asset.identifier == asset_data["identifier"]
            ).first()
            
            if existing:
                # Update existing asset
                existing.properties = asset_data.get("properties", {})
                existing.last_seen = datetime.utcnow()
            else:
                # Create new asset
                asset = Asset(**asset_data)
                self.db.add(asset)
        
        self.db.commit()
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db'):
            self.db.close()
