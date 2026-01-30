"""
Scan execution engine
Orchestrates tool execution and result aggregation
"""

import logging
from typing import Dict, List, Any
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.services.tool_runners.nmap_runner import NmapRunner
from app.services.tool_runners.masscan_runner import MasscanRunner
from app.services.tool_runners.nikto_runner import NiktoRunner
from app.services.tool_runners.sqlmap_runner import SQLMapRunner
from app.services.tool_runners.bloodhound_runner import BloodHoundRunner
from app.services.tool_runners.crackmapexec_runner import CrackMapExecRunner
from app.services.result_aggregator import ResultAggregator
from datetime import datetime

logger = logging.getLogger(__name__)


class ScanEngine:
    """Main scan execution engine"""
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.db = SessionLocal()
        self.scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        self.result_aggregator = ResultAggregator(scan_id)
        
    def execute(self) -> Dict[str, Any]:
        """
        Execute the scan
        """
        logger.info(f"Executing scan {self.scan_id}")
        
        try:
            results = {}
            
            # Determine which tools to run based on scan type
            if self.scan.scan_type == "network":
                results.update(self._run_network_scan())
            elif self.scan.scan_type == "web":
                results.update(self._run_web_scan())
            elif self.scan.scan_type == "ad":
                results.update(self._run_ad_scan())
            elif self.scan.scan_type == "full":
                results.update(self._run_full_scan())
            
            # Aggregate results
            aggregated = self.result_aggregator.aggregate(results)
            
            # Update scan progress
            self._update_progress(100)
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Scan execution failed: {e}")
            raise
        finally:
            self.db.close()
    
    def _run_network_scan(self) -> Dict[str, Any]:
        """Run network scanning tools"""
        logger.info("Running network scan")
        results = {}
        config = self.scan.scan_config or {}
        tools_config = config.get('tools', {})
        
        # Run masscan (fast port scan)
        if tools_config.get('masscan', False):
            try:
                masscan_runner = MasscanRunner(self.scan_id)
                masscan_results = masscan_runner.run(self.scan.targets, config.get('masscan', {}))
                results['masscan'] = masscan_results
                self._update_progress(25)
            except Exception as e:
                logger.error(f"Masscan failed: {e}")
        
        # Run nmap
        if tools_config.get('nmap', True):
            try:
                nmap_runner = NmapRunner(self.scan_id)
                nmap_results = nmap_runner.run(self.scan.targets, config.get('nmap', {}))
                results['nmap'] = nmap_results
                self._update_progress(50)
            except Exception as e:
                logger.error(f"Nmap failed: {e}")
        
        return results
    
    def _run_web_scan(self) -> Dict[str, Any]:
        """Run web application scanning tools"""
        logger.info("Running web scan")
        results = {}
        config = self.scan.scan_config or {}
        tools_config = config.get('tools', {})
        
        # Run Nikto
        if tools_config.get('nikto', True):
            try:
                nikto_runner = NiktoRunner(self.scan_id)
                nikto_results = nikto_runner.run(self.scan.targets, config.get('nikto', {}))
                results['nikto'] = nikto_results
                self._update_progress(33)
            except Exception as e:
                logger.error(f"Nikto failed: {e}")
        
        # Run SQLMap
        if tools_config.get('sqlmap', False):
            try:
                sqlmap_runner = SQLMapRunner(self.scan_id)
                sqlmap_results = sqlmap_runner.run(self.scan.targets, config.get('sqlmap', {}))
                results['sqlmap'] = sqlmap_results
                self._update_progress(66)
            except Exception as e:
                logger.error(f"SQLMap failed: {e}")
        
        return results
    
    def _run_ad_scan(self) -> Dict[str, Any]:
        """Run Active Directory scanning tools"""
        logger.info("Running AD scan")
        results = {}
        
        config = self.scan.scan_config or {}
        ad_config = config.get('ad', {})
        
        # Run BloodHound collection
        if config.get('tools', {}).get('bloodhound', True) and ad_config.get('domain'):
            try:
                bloodhound_runner = BloodHoundRunner(self.scan_id)
                bloodhound_results = bloodhound_runner.run(
                    targets=[ad_config.get('dc_ip', '')],
                    config=ad_config
                )
                results['bloodhound'] = bloodhound_results
                self._update_progress(33)
            except Exception as e:
                logger.error(f"BloodHound failed: {e}")
        
        # Run CrackMapExec
        if config.get('tools', {}).get('crackmapexec', True):
            try:
                cme_runner = CrackMapExecRunner(self.scan_id)
                cme_results = cme_runner.run(
                    targets=self.scan.targets,
                    config=ad_config
                )
                results['crackmapexec'] = cme_results
                self._update_progress(66)
            except Exception as e:
                logger.error(f"CrackMapExec failed: {e}")
        
        return results
    
    def _run_full_scan(self) -> Dict[str, Any]:
        """Run full pentest scan"""
        logger.info("Running full scan")
        results = {}
        results.update(self._run_network_scan())
        results.update(self._run_web_scan())
        results.update(self._run_ad_scan())
        return results
    
    def _update_progress(self, percent: int):
        """Update scan progress"""
        self.scan.progress_percent = percent
        self.db.commit()
