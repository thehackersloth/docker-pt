"""
CrackMapExec tool runner
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class CrackMapExecRunner(BaseToolRunner):
    """CrackMapExec runner for AD enumeration"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "crackmapexec")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate CrackMapExec input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run CrackMapExec
        """
        config = config or {}
        module = config.get('module', 'smb')  # smb, winrm, ssh, mssql, ldap
        username = config.get('username')
        password = config.get('password')
        domain = config.get('domain')
        
        cmd = ['crackmapexec', module]
        
        # Add targets
        cmd.extend(targets)
        
        # Add credentials if provided
        if username:
            cmd.extend(['-u', username])
        if password:
            cmd.extend(['-p', password])
        if domain:
            cmd.extend(['-d', domain])
        
        # Output format
        cmd.append('--json')
        
        logger.info(f"Running CrackMapExec: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"CrackMapExec failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Parse JSON output (one JSON object per line)
            results = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            return {
                "success": True,
                "module": module,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"CrackMapExec execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse CrackMapExec output"""
        # Already JSON, just return
        return {"raw_output": output}
