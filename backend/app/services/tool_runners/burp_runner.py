"""
Burp Suite headless integration
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class BurpRunner(BaseToolRunner):
    """Burp Suite headless scanner runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "burp")
        self.burp_path = "/opt/burpsuite"
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Burp input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Burp Suite scan
        """
        config = config or {}
        url = targets[0] if targets else config.get('url')
        scan_type = config.get('scan_type', 'crawl_and_audit')
        config_file = config.get('config_file')
        
        if not url:
            raise ValueError("URL required for Burp Suite")
        
        # Burp Suite headless requires license and specific setup
        # For open-source alternative, we can use OWASP ZAP
        # This is a structure for when Burp Suite Pro is available
        
        cmd = ['java', '-jar', f'{self.burp_path}/burpsuite_pro.jar']
        
        # Headless mode
        cmd.extend(['--project-file', f'/tmp/burp_{self.scan_id}.burp'])
        cmd.extend(['--unpause-spider-and-scanner'])
        
        # Target URL
        cmd.extend(['--scan', url])
        
        # Config file if provided
        if config_file:
            cmd.extend(['--config-file', config_file])
        
        logger.info(f"Running Burp Suite: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Burp Suite failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Parse results from project file
            # Burp Suite stores results in the .burp file
            results = self.parse_output(stdout)
            
            return {
                "success": True,
                "url": url,
                "project_file": f'/tmp/burp_{self.scan_id}.burp',
                "output": results,
                "raw_output": stdout
            }
            
        except Exception as e:
            logger.error(f"Burp Suite execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Burp Suite output"""
        # Burp Suite output parsing would go here
        # For now, return raw output
        return {"raw_output": output}
