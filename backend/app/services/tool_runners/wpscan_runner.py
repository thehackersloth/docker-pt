"""
WPScan WordPress security scanner runner
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class WPScanRunner(BaseToolRunner):
    """WPScan WordPress scanner runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "wpscan")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate WPScan input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run WPScan
        """
        config = config or {}
        url = targets[0] if targets else config.get('url')
        if not url:
            raise ValueError("URL required for WPScan")
        
        username = config.get('username')
        password = config.get('password')
        usernames = config.get('usernames')  # List of usernames
        passwords = config.get('passwords')  # List of passwords
        enumerate = config.get('enumerate', ['u', 'p', 't'])  # u=users, p=plugins, t=themes
        
        cmd = ['wpscan', '--url', url]
        
        # API token (optional but recommended)
        api_token = config.get('api_token')
        if api_token:
            cmd.extend(['--api-token', api_token])
        
        # Enumeration
        if enumerate:
            cmd.extend(['--enumerate', ','.join(enumerate)])
        
        # Username/password
        if username:
            cmd.extend(['--username', username])
        if password:
            cmd.extend(['--password', password])
        if usernames:
            cmd.extend(['--usernames', ','.join(usernames)])
        if passwords:
            cmd.extend(['--passwords', ','.join(passwords)])
        
        # Output format
        output_file = f"/tmp/wpscan_{self.scan_id}.json"
        cmd.extend(['--format', 'json', '--output', output_file])
        
        logger.info(f"Running WPScan: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"WPScan failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Read JSON output
            try:
                with open(output_file, 'r') as f:
                    output_data = json.load(f)
            except:
                output_data = {}
            
            return {
                "success": True,
                "url": url,
                "output": output_data,
                "raw_output": stdout
            }
            
        except Exception as e:
            logger.error(f"WPScan execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse WPScan output"""
        # WPScan outputs JSON, so this is mainly for raw text parsing
        return {"raw_output": output}
