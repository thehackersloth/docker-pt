"""
Medusa parallel brute-forcing runner
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class MedusaRunner(BaseToolRunner):
    """Medusa parallel brute-forcing runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "medusa")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Medusa input"""
        config = config or {}
        if not config.get('service'):
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Medusa
        """
        config = config or {}
        target = targets[0] if targets else config.get('target')
        service = config.get('service')
        username = config.get('username')
        userlist = config.get('userlist')
        password = config.get('password')
        passwordlist = config.get('passwordlist')
        threads = config.get('threads', 16)
        
        if not target:
            raise ValueError("Target required for Medusa")
        if not service:
            raise ValueError("Service required for Medusa")
        
        cmd = ['medusa', '-h', target, '-M', service]
        
        # Username
        if username:
            cmd.extend(['-u', username])
        elif userlist:
            cmd.extend(['-U', userlist])
        
        # Password
        if password:
            cmd.extend(['-p', password])
        elif passwordlist:
            cmd.extend(['-P', passwordlist])
        
        # Threads
        cmd.extend(['-t', str(threads)])
        
        # Output
        output_file = f"/tmp/medusa_{self.scan_id}.txt"
        cmd.extend(['-O', output_file])
        
        logger.info(f"Running Medusa: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Medusa failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Read output file
            output_content = ""
            try:
                with open(output_file, 'r') as f:
                    output_content = f.read()
            except:
                pass
            
            # Parse for credentials
            parsed = self.parse_output(output_content)
            
            return {
                "success": True,
                "target": target,
                "service": service,
                "output": parsed,
                "raw_output": stdout
            }
            
        except Exception as e:
            logger.error(f"Medusa execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Medusa output"""
        credentials = []
        
        for line in output.split('\n'):
            if 'SUCCESS' in line.upper():
                parts = line.split()
                cred = {}
                for i, part in enumerate(parts):
                    if 'host:' in part.lower() and i + 1 < len(parts):
                        cred['host'] = parts[i + 1]
                    elif 'user:' in part.lower() and i + 1 < len(parts):
                        cred['username'] = parts[i + 1]
                    elif 'password:' in part.lower() and i + 1 < len(parts):
                        cred['password'] = parts[i + 1]
                if cred:
                    credentials.append(cred)
        
        return {
            "credentials": credentials,
            "count": len(credentials),
            "raw_output": output
        }
