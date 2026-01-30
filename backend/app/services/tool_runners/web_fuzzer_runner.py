"""
Web fuzzer runner (wfuzz, ffuf, gobuster)
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class WebFuzzerRunner(BaseToolRunner):
    """Web fuzzer runner"""
    
    def __init__(self, scan_id: str, tool: str = "ffuf"):
        super().__init__(scan_id, tool)
        self.tool = tool  # wfuzz, ffuf, gobuster
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate web fuzzer input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run web fuzzer
        """
        config = config or {}
        url = targets[0] if targets else config.get('url')
        wordlist = config.get('wordlist', '/usr/share/wordlists/dirb/common.txt')
        fuzz_type = config.get('fuzz_type', 'directory')  # directory, parameter, subdomain
        
        if not url:
            raise ValueError("URL required for web fuzzing")
        
        if self.tool == "ffuf":
            return self._run_ffuf(url, wordlist, fuzz_type, config)
        elif self.tool == "wfuzz":
            return self._run_wfuzz(url, wordlist, fuzz_type, config)
        elif self.tool == "gobuster":
            return self._run_gobuster(url, wordlist, fuzz_type, config)
        else:
            return {"error": f"Unknown tool: {self.tool}", "success": False}
    
    def _run_ffuf(self, url: str, wordlist: str, fuzz_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run ffuf"""
        if fuzz_type == "directory":
            fuzz_url = f"{url}/FUZZ"
        elif fuzz_type == "parameter":
            fuzz_url = f"{url}?FUZZ=test"
        else:
            fuzz_url = f"https://FUZZ.{url.replace('https://', '').replace('http://', '')}"
        
        cmd = ['ffuf', '-u', fuzz_url, '-w', wordlist, '-json']
        
        # Status codes to show
        status_codes = config.get('status_codes', '200,204,301,302,307,401,403')
        cmd.extend(['-mc', status_codes])
        
        # Threads
        threads = config.get('threads', 40)
        cmd.extend(['-t', str(threads)])
        
        logger.info(f"Running ffuf: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            # Parse JSON output
            try:
                output_data = json.loads(stdout)
            except:
                output_data = {}
            
            return {
                "success": True,
                "url": url,
                "fuzz_type": fuzz_type,
                "output": output_data,
                "raw_output": stdout
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_wfuzz(self, url: str, wordlist: str, fuzz_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run wfuzz"""
        if fuzz_type == "directory":
            fuzz_url = f"{url}/FUZZ"
        else:
            fuzz_url = f"{url}?FUZZ=test"
        
        cmd = ['wfuzz', '-c', '-z', 'file', wordlist, fuzz_url]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            return {
                "success": True,
                "url": url,
                "fuzz_type": fuzz_type,
                "output": stdout,
                "raw_output": stdout
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_gobuster(self, url: str, wordlist: str, fuzz_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run gobuster"""
        if fuzz_type == "directory":
            mode = "dir"
        elif fuzz_type == "subdomain":
            mode = "dns"
        else:
            mode = "dir"
        
        cmd = ['gobuster', mode, '-u', url, '-w', wordlist]
        
        # Threads
        threads = config.get('threads', 10)
        cmd.extend(['-t', str(threads)])
        
        # Output format
        cmd.extend(['-o', f'/tmp/gobuster_{self.scan_id}.txt'])
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            # Read output file
            output_content = ""
            try:
                with open(f'/tmp/gobuster_{self.scan_id}.txt', 'r') as f:
                    output_content = f.read()
            except:
                pass
            
            return {
                "success": True,
                "url": url,
                "fuzz_type": fuzz_type,
                "output": output_content,
                "raw_output": stdout
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse web fuzzer output"""
        return {"raw_output": output}
