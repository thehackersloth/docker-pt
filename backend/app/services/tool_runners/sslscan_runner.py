"""
SSL/TLS scanner runner (sslscan, testssl.sh, sslyze)
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class SSLScanRunner(BaseToolRunner):
    """SSL/TLS scanner runner"""
    
    def __init__(self, scan_id: str, tool: str = "sslscan"):
        super().__init__(scan_id, tool)
        self.tool = tool  # sslscan, testssl.sh, sslyze
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate SSL scanner input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run SSL/TLS scanner
        """
        config = config or {}
        target = targets[0] if targets else config.get('target')
        port = config.get('port', 443)
        
        if not target:
            raise ValueError("Target required for SSL scan")
        
        results = []
        
        for target_host in targets:
            if self.tool == "sslscan":
                result = self._run_sslscan(target_host, port, config)
            elif self.tool == "testssl.sh":
                result = self._run_testssl(target_host, port, config)
            elif self.tool == "sslyze":
                result = self._run_sslyze(target_host, port, config)
            else:
                result = {"error": f"Unknown tool: {self.tool}", "success": False}
            
            results.append({
                "target": target_host,
                "port": port,
                **result
            })
        
        return {
            "success": True,
            "tool": self.tool,
            "results": results
        }
    
    def _run_sslscan(self, target: str, port: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run sslscan"""
        cmd = ['sslscan', f'{target}:{port}']
        
        if config.get('show_certificate'):
            cmd.append('--show-certificate')
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()
            
            return {
                "success": process.returncode == 0,
                "output": stdout,
                "error": stderr if process.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_testssl(self, target: str, port: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run testssl.sh"""
        cmd = ['testssl.sh', '--json', f'{target}:{port}']
        
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
                "success": process.returncode == 0,
                "output": output_data,
                "raw_output": stdout
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _run_sslyze(self, target: str, port: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run sslyze"""
        cmd = ['sslyze', f'{target}:{port}', '--json_out', '-']
        
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
                "success": process.returncode == 0,
                "output": output_data,
                "raw_output": stdout
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse SSL scanner output"""
        return {"raw_output": output}
