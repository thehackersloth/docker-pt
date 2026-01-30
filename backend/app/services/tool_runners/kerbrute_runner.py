"""
Kerbrute tool runner (Kerberos brute-forcing)
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class KerbruteRunner(BaseToolRunner):
    """Kerbrute Kerberos brute-forcing runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "kerbrute")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Kerbrute input"""
        config = config or {}
        if not config.get('domain'):
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Kerbrute
        """
        config = config or {}
        domain = config.get('domain')
        attack_type = config.get('attack_type', 'userenum')  # userenum, passwordspray, asreproast
        userlist = config.get('userlist', '/usr/share/wordlists/usernames.txt')
        password = config.get('password')  # For password spray
        passwordlist = config.get('passwordlist')  # For brute force
        
        cmd = ['kerbrute', attack_type]
        
        if domain:
            cmd.extend(['-d', domain])
        
        if attack_type == 'userenum':
            cmd.extend(['--userlist', userlist])
        elif attack_type == 'passwordspray':
            if not password:
                raise ValueError("Password required for password spray")
            cmd.extend(['--userlist', userlist, '--password', password])
        elif attack_type == 'asreproast':
            cmd.extend(['--userlist', userlist])
        
        # Output
        output_file = f"/tmp/kerbrute_{self.scan_id}.txt"
        cmd.extend(['-o', output_file])
        
        logger.info(f"Running Kerbrute: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Kerbrute failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Read output file
            output_content = ""
            try:
                with open(output_file, 'r') as f:
                    output_content = f.read()
            except:
                pass
            
            parsed = self.parse_output(output_content)
            
            return {
                "success": True,
                "attack_type": attack_type,
                "domain": domain,
                "output": parsed,
                "raw_output": stdout
            }
            
        except Exception as e:
            logger.error(f"Kerbrute execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Kerbrute output"""
        valid_users = []
        invalid_users = []
        asrep_hashes = []
        
        for line in output.split('\n'):
            if 'VALID' in line.upper() or 'FOUND' in line.upper():
                # Extract username
                parts = line.split()
                for part in parts:
                    if '@' in part:
                        valid_users.append(part)
            elif 'INVALID' in line.upper() or 'NOT FOUND' in line.upper():
                parts = line.split()
                for part in parts:
                    if '@' in part:
                        invalid_users.append(part)
            elif '$krb5asrep' in line:
                asrep_hashes.append(line.strip())
        
        return {
            "valid_users": valid_users,
            "invalid_users": invalid_users,
            "asrep_hashes": asrep_hashes,
            "raw_output": output
        }
