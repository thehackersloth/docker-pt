"""
Masscan tool runner (fast port scanning)
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class MasscanRunner(BaseToolRunner):
    """Masscan fast port scanner runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "masscan")
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate masscan input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run masscan scan
        """
        config = config or {}
        ports = config.get('ports', '1-65535')
        rate = config.get('rate', '1000')  # packets per second
        output_format = config.get('output_format', 'json')
        
        cmd = ['masscan']
        
        # Add targets
        cmd.extend(targets)
        
        # Ports
        cmd.extend(['-p', ports])
        
        # Rate
        cmd.extend(['--rate', str(rate)])
        
        # Output format
        if output_format == 'json':
            cmd.append('--json')
        elif output_format == 'xml':
            cmd.append('--xml')
        else:
            cmd.append('--json')
        
        # Output to stdout
        cmd.append('-')
        
        logger.info(f"Running masscan: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Masscan failed: {stderr}")
                return {"error": stderr, "success": False}
            
            # Parse JSON output (one JSON object per line)
            results = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            return {
                "success": True,
                "ports": ports,
                "rate": rate,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            logger.error(f"Masscan execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse masscan output"""
        results = []
        for line in output.strip().split('\n'):
            if line.strip():
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return {"results": results}
