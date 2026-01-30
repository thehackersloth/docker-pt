"""
SQLMap SQL injection scanner runner
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class SQLMapRunner(BaseToolRunner):
    """SQLMap SQL injection scanner runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "sqlmap")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate sqlmap input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run sqlmap scan
        """
        config = config or {}
        url = targets[0] if targets else config.get('url')
        if not url:
            raise ValueError("URL required for SQLMap")
        
        data = config.get('data')  # POST data
        method = config.get('method', 'GET')
        level = config.get('level', 1)  # 1-5
        risk = config.get('risk', 1)  # 1-3
        batch = config.get('batch', True)  # Non-interactive
        
        cmd = ['sqlmap', '-u', url]
        
        # POST data
        if data:
            cmd.extend(['--data', data])
        
        # Method
        if method == 'POST':
            cmd.append('--method=POST')
        
        # Level and risk
        cmd.extend(['--level', str(level)])
        cmd.extend(['--risk', str(risk)])
        
        # Batch mode
        if batch:
            cmd.append('--batch')
        
        # Output format
        cmd.extend(['--output-dir', f'/tmp/sqlmap_{self.scan_id}'])
        
        logger.info(f"Running sqlmap: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"SQLMap failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Parse output
            parsed = self.parse_output(stdout)
            
            return {
                "success": True,
                "url": url,
                "output": parsed,
                "raw_output": stdout
            }
            
        except Exception as e:
            logger.error(f"SQLMap execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse sqlmap output"""
        findings = []
        vulnerable = False
        
        # Check for SQL injection findings
        if 'is vulnerable' in output.lower():
            vulnerable = True
        
        # Extract database information
        db_type = None
        if 'back-end DBMS:' in output:
            parts = output.split('back-end DBMS:')
            if len(parts) > 1:
                db_type = parts[1].split('\n')[0].strip()
        
        return {
            "vulnerable": vulnerable,
            "database_type": db_type,
            "raw_output": output
        }
