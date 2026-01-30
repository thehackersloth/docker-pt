"""
Nikto web server scanner runner
"""

import subprocess
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class NiktoRunner(BaseToolRunner):
    """Nikto web scanner runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "nikto")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate nikto input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run nikto scan
        """
        config = config or {}
        port = config.get('port', 80)
        ssl = config.get('ssl', False)
        format_type = config.get('format', 'txt')
        
        results = []
        
        for target in targets:
            cmd = ['nikto', '-h', target]
            
            # Port
            if port:
                cmd.extend(['-p', str(port)])
            
            # SSL
            if ssl:
                cmd.append('-ssl')
            
            # Format
            if format_type == 'xml':
                cmd.append('-Format', 'xml')
            elif format_type == 'csv':
                cmd.append('-Format', 'csv')
            
            logger.info(f"Running nikto: {' '.join(cmd)}")
            
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Nikto failed for {target}: {stderr}")
                    results.append({
                        "target": target,
                        "success": False,
                        "error": stderr
                    })
                else:
                    parsed = self.parse_output(stdout)
                    results.append({
                        "target": target,
                        "success": True,
                        "output": parsed
                    })
                    
            except Exception as e:
                logger.error(f"Nikto execution error for {target}: {e}")
                results.append({
                    "target": target,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse nikto output"""
        findings = []
        lines = output.split('\n')
        
        for line in lines:
            if '+ ' in line and 'OSVDB' in line:
                # Parse finding
                parts = line.split('+ ')
                if len(parts) > 1:
                    finding = parts[1].strip()
                    findings.append(finding)
        
        return {
            "findings": findings,
            "raw_output": output
        }
