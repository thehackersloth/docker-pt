"""
Impacket tools runner
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class ImpacketRunner(BaseToolRunner):
    """Impacket suite runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "impacket")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Impacket input"""
        config = config or {}
        tool = config.get('tool')
        if not tool:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Impacket tool
        """
        config = config or {}
        tool = config.get('tool')  # GetNPUsers, GetUserSPNs, secretsdump, etc.
        domain = config.get('domain')
        username = config.get('username')
        password = config.get('password')
        target = targets[0] if targets else config.get('target')
        
        if not target:
            raise ValueError("Target required for Impacket")
        
        # Build command based on tool
        cmd = []
        
        if tool == "GetNPUsers":
            cmd = ['GetNPUsers.py', domain + '/' + username + ':' + password + '@' + target]
        elif tool == "GetUserSPNs":
            cmd = ['GetUserSPNs.py', domain + '/' + username + ':' + password + '@' + target]
        elif tool == "secretsdump":
            cmd = ['secretsdump.py', domain + '/' + username + ':' + password + '@' + target]
        elif tool == "psexec":
            cmd = ['psexec.py', domain + '/' + username + ':' + password + '@' + target]
        elif tool == "smbexec":
            cmd = ['smbexec.py', domain + '/' + username + ':' + password + '@' + target]
        else:
            raise ValueError(f"Unknown Impacket tool: {tool}")
        
        logger.info(f"Running Impacket {tool}: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Impacket {tool} failed: {stderr}")
                return {"error": stderr, "success": False}
            
            return {
                "success": True,
                "tool": tool,
                "target": target,
                "output": stdout,
                "stderr": stderr
            }
            
        except Exception as e:
            logger.error(f"Impacket execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Impacket output"""
        return {"raw_output": output}
