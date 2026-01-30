"""
Hashcat GPU-accelerated password cracker runner
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class HashcatRunner(BaseToolRunner):
    """Hashcat password cracker runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "hashcat")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Hashcat input"""
        config = config or {}
        if not config.get('hash_file') and not config.get('hashes'):
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Hashcat
        """
        config = config or {}
        hash_file = config.get('hash_file')
        hashes = config.get('hashes')
        wordlist = config.get('wordlist', '/usr/share/wordlists/rockyou.txt')
        hash_type = config.get('hash_type')  # 0=MD5, 1000=NTLM, etc.
        attack_mode = config.get('attack_mode', 0)  # 0=straight, 1=combinator, 3=brute-force
        rules = config.get('rules')
        use_gpu = config.get('use_gpu', True)
        
        # Create hash file if hashes provided
        if hashes and not hash_file:
            hash_file = f"/tmp/hashcat_{self.scan_id}.hash"
            with open(hash_file, 'w') as f:
                if isinstance(hashes, list):
                    f.write('\n'.join(hashes))
                else:
                    f.write(hashes)
        
        if not hash_file:
            raise ValueError("Hash file or hashes required for Hashcat")
        if not hash_type:
            raise ValueError("Hash type required for Hashcat")
        
        cmd = ['hashcat']
        
        # Attack mode
        cmd.extend(['-a', str(attack_mode)])
        
        # Hash type
        cmd.extend(['-m', str(hash_type)])
        
        # Wordlist
        if wordlist:
            cmd.extend([hash_file, wordlist])
        
        # Rules
        if rules:
            cmd.extend(['-r', rules])
        
        # GPU
        if use_gpu:
            cmd.append('--force')  # Force GPU usage
        
        # Output file
        output_file = f"/tmp/hashcat_{self.scan_id}.out"
        cmd.extend(['-o', output_file])
        
        logger.info(f"Running Hashcat: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            # Hashcat returns 0 on success, 1 if no passwords found
            if process.returncode not in [0, 1]:
                logger.error(f"Hashcat failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Read output file
            cracked = []
            try:
                with open(output_file, 'r') as f:
                    for line in f:
                        if ':' in line:
                            parts = line.split(':')
                            if len(parts) >= 2:
                                cracked.append({
                                    "hash": parts[0],
                                    "password": parts[1].strip()
                                })
            except:
                pass
            
            return {
                "success": True,
                "hash_file": hash_file,
                "hash_type": hash_type,
                "cracked": cracked,
                "count": len(cracked),
                "raw_output": stdout
            }
            
        except Exception as e:
            logger.error(f"Hashcat execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Hashcat output"""
        return {"raw_output": output}
