"""
John the Ripper password cracker runner
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class JohnRunner(BaseToolRunner):
    """John the Ripper password cracker runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "john")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate John input"""
        config = config or {}
        if not config.get('hash_file') and not config.get('hashes'):
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run John the Ripper
        """
        config = config or {}
        hash_file = config.get('hash_file')
        hashes = config.get('hashes')  # Direct hash input
        wordlist = config.get('wordlist', '/usr/share/wordlists/rockyou.txt')
        format_type = config.get('format')  # nt, md5, sha256, etc.
        rules = config.get('rules')  # Wordlist mangling rules
        
        # Create hash file if hashes provided directly
        if hashes and not hash_file:
            hash_file = f"/tmp/john_{self.scan_id}.hash"
            with open(hash_file, 'w') as f:
                if isinstance(hashes, list):
                    f.write('\n'.join(hashes))
                else:
                    f.write(hashes)
        
        if not hash_file:
            raise ValueError("Hash file or hashes required for John")
        
        cmd = ['john']
        
        # Wordlist
        if wordlist:
            cmd.extend(['--wordlist', wordlist])
        
        # Format
        if format_type:
            cmd.extend(['--format', format_type])
        
        # Rules
        if rules:
            cmd.extend(['--rules', rules])
        
        # Hash file
        cmd.append(hash_file)
        
        logger.info(f"Running John: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            # John returns 0 even if no passwords found
            # Check output for cracked passwords
            
            # Show cracked passwords
            show_cmd = ['john', '--show', hash_file]
            if format_type:
                show_cmd.extend(['--format', format_type])
            
            show_process = subprocess.Popen(
                show_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            show_stdout, show_stderr = show_process.communicate()
            
            parsed = self.parse_output(show_stdout)
            
            return {
                "success": True,
                "hash_file": hash_file,
                "output": parsed,
                "raw_output": stdout,
                "cracked_output": show_stdout
            }
            
        except Exception as e:
            logger.error(f"John execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse John output"""
        cracked = []
        
        for line in output.split('\n'):
            if ':' in line and len(line.split(':')) >= 2:
                parts = line.split(':')
                if len(parts) >= 2:
                    cracked.append({
                        "username": parts[0],
                        "password": parts[1] if len(parts) > 1 else "",
                        "hash": parts[2] if len(parts) > 2 else ""
                    })
        
        return {
            "cracked_passwords": cracked,
            "count": len(cracked),
            "raw_output": output
        }
