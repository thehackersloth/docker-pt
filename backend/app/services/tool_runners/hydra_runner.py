"""
Hydra network login cracker runner
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class HydraRunner(BaseToolRunner):
    """Hydra network login cracker runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "hydra")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Hydra input"""
        config = config or {}
        if not config.get('service'):
            return False
        if not config.get('userlist') and not config.get('username'):
            return False
        if not config.get('passwordlist') and not config.get('password'):
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Hydra
        """
        config = config or {}
        target = targets[0] if targets else config.get('target')
        service = config.get('service')  # ssh, ftp, http, etc.
        username = config.get('username')
        userlist = config.get('userlist')
        password = config.get('password')
        passwordlist = config.get('passwordlist')
        port = config.get('port')
        
        if not target:
            raise ValueError("Target required for Hydra")
        if not service:
            raise ValueError("Service required for Hydra")
        
        cmd = ['hydra']
        
        # Target
        if port:
            cmd.extend(['-s', str(port)])
        
        # Username
        if username:
            cmd.extend(['-l', username])
        elif userlist:
            cmd.extend(['-L', userlist])
        
        # Password
        if password:
            cmd.extend(['-p', password])
        elif passwordlist:
            cmd.extend(['-P', passwordlist])
        
        # Service and target
        cmd.extend([target, service])
        
        logger.info(f"Running Hydra: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Hydra failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Parse output for found credentials
            parsed = self.parse_output(stdout)
            
            return {
                "success": True,
                "target": target,
                "service": service,
                "output": parsed,
                "raw_output": stdout
            }
            
        except Exception as e:
            logger.error(f"Hydra execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Hydra output"""
        credentials = []
        
        for line in output.split('\n'):
            if 'login:' in line.lower() and 'password:' in line.lower():
                # Extract credentials
                parts = line.split()
                cred = {}
                for i, part in enumerate(parts):
                    if 'login:' in part.lower():
                        if i + 1 < len(parts):
                            cred['username'] = parts[i + 1]
                    elif 'password:' in part.lower():
                        if i + 1 < len(parts):
                            cred['password'] = parts[i + 1]
                if cred:
                    credentials.append(cred)
        
        return {
            "credentials": credentials,
            "count": len(credentials),
            "raw_output": output
        }
