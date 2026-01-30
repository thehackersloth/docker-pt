"""
Responder tool runner (LLMNR/NBT-NS poisoning)
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class ResponderRunner(BaseToolRunner):
    """Responder LLMNR/NBT-NS poisoning runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "responder")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Responder input"""
        return True  # Responder doesn't need specific targets
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Responder
        """
        config = config or {}
        interface = config.get('interface', 'eth0')
        analyze = config.get('analyze', False)
        wpad = config.get('wpad', True)
        force_wpad_auth = config.get('force_wpad_auth', False)
        
        cmd = ['responder', '-I', interface]
        
        if analyze:
            cmd.append('-A')
        if wpad:
            cmd.append('-w')
        if force_wpad_auth:
            cmd.append('-f')
        
        # Output file
        output_file = f"/tmp/responder_{self.scan_id}.log"
        cmd.extend(['-o', output_file])
        
        logger.info(f"Running Responder: {' '.join(cmd)}")
        
        try:
            # Responder runs continuously, so we'll run it in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Let it run for a bit, then check output
            import time
            time.sleep(10)  # Run for 10 seconds
            
            # Check if still running
            if process.poll() is None:
                # Still running, get initial output
                stdout, stderr = process.communicate(timeout=1)
            else:
                stdout, stderr = process.communicate()
            
            # Read output file if it exists
            output_content = ""
            try:
                with open(output_file, 'r') as f:
                    output_content = f.read()
            except:
                pass
            
            return {
                "success": True,
                "interface": interface,
                "output_file": output_file,
                "output": output_content,
                "process_id": process.pid if process.poll() is None else None,
            }
            
        except Exception as e:
            logger.error(f"Responder execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Responder output"""
        credentials = []
        hashes = []
        
        for line in output.split('\n'):
            if 'NTLMv2' in line or 'NTLMv1' in line:
                hashes.append(line.strip())
            elif 'Username:' in line or 'Password:' in line:
                credentials.append(line.strip())
        
        return {
            "credentials": credentials,
            "hashes": hashes,
            "raw_output": output
        }
