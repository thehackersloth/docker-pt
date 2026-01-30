"""
Empire/Starkiller post-exploitation framework runner
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class EmpireRunner(BaseToolRunner):
    """Empire post-exploitation framework runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "empire")
        self.empire_path = "/opt/Empire"
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Empire input"""
        config = config or {}
        action = config.get('action')
        if not action:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Empire operation
        """
        config = config or {}
        action = config.get('action')  # stager, listener, module
        
        if action == "stager":
            return self._generate_stager(config)
        elif action == "listener":
            return self._manage_listener(config)
        elif action == "module":
            return self._execute_module(config)
        else:
            return {"error": f"Unknown action: {action}", "success": False}
    
    def _generate_stager(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Empire stager"""
        stager_type = config.get('stager_type', 'multi/launcher')
        listener = config.get('listener')
        output_path = config.get('output_path', f'/tmp/empire_stager_{self.scan_id}')
        
        # Use Empire REST API if available
        # For now, use command line
        cmd = ['empire', 'stager', 'generate', stager_type]
        
        if listener:
            cmd.extend(['--listener', listener])
        
        cmd.extend(['--output', output_path])
        
        logger.info(f"Generating Empire stager: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.empire_path
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                return {"error": stderr, "success": False}
            
            return {
                "success": True,
                "stager_type": stager_type,
                "output_path": output_path,
                "output": stdout
            }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def _manage_listener(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Manage Empire listener"""
        operation = config.get('operation', 'start')  # start, stop, list
        listener_type = config.get('listener_type', 'http')
        host = config.get('host', '0.0.0.0')
        port = config.get('port', 8080)
        
        if operation == "start":
            cmd = ['empire', 'listener', 'start', listener_type]
            cmd.extend(['--host', host, '--port', str(port)])
        elif operation == "stop":
            cmd = ['empire', 'listener', 'stop', config.get('listener_id', '')]
        else:
            cmd = ['empire', 'listener', 'list']
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.empire_path
            )
            stdout, stderr = process.communicate()
            
            return {
                "success": process.returncode == 0,
                "operation": operation,
                "output": stdout
            }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def _execute_module(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Empire post-exploitation module"""
        module = config.get('module')
        agent = config.get('agent')
        options = config.get('options', {})
        
        if not module or not agent:
            return {"error": "Module and agent required", "success": False}
        
        cmd = ['empire', 'module', 'execute', module, '--agent', agent]
        
        for key, value in options.items():
            cmd.extend(['--option', f'{key}={value}'])
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.empire_path
            )
            stdout, stderr = process.communicate()
            
            return {
                "success": process.returncode == 0,
                "module": module,
                "agent": agent,
                "output": stdout
            }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Empire output"""
        return {"raw_output": output}
