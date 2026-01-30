"""
Nmap tool runner
"""

import subprocess
import xml.etree.ElementTree as ET
import json
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class NmapRunner(BaseToolRunner):
    """Nmap scanner runner"""
    
    def __init__(self, scan_id: str):
        super().__init__(scan_id, "nmap")
        self.process = None
    
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate nmap input"""
        if not targets:
            return False
        return True
    
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run nmap scan
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid nmap input")
        
        config = config or {}
        scan_type = config.get('scan_type', 'syn')  # syn, tcp, udp
        ports = config.get('ports', None)  # None = default, "1-1000", "80,443", etc.
        scripts = config.get('scripts', [])
        os_detection = config.get('os_detection', False)
        service_detection = config.get('service_detection', True)
        
        # Build nmap command
        cmd = ['nmap']
        
        # Scan type
        if scan_type == 'syn':
            cmd.append('-sS')
        elif scan_type == 'tcp':
            cmd.append('-sT')
        elif scan_type == 'udp':
            cmd.append('-sU')
        
        # Ports
        if ports:
            cmd.extend(['-p', ports])
        
        # OS detection
        if os_detection:
            cmd.append('-O')
        
        # Service detection
        if service_detection:
            cmd.append('-sV')
        
        # Scripts
        if scripts:
            cmd.extend(['--script', ','.join(scripts)])
        
        # Output format
        cmd.append('-oX')  # XML output
        cmd.append('-')  # stdout
        
        # Targets
        cmd.extend(targets)
        
        logger.info(f"Running nmap: {' '.join(cmd)}")

        # Store command in scan logs
        self._append_log(f"[NMAP] Executing: {' '.join(cmd)}\n")

        try:
            # Execute nmap
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self.process.communicate()

            # Log stderr (nmap status messages)
            if stderr:
                self._append_log(stderr)

            if self.process.returncode != 0:
                logger.error(f"Nmap failed: {stderr}")
                self._append_log(f"[NMAP] Failed: {stderr}\n")
                return {"error": stderr, "success": False}

            self._append_log(f"[NMAP] Scan completed successfully\n")

            # Parse XML output
            results = self.parse_output(stdout)
            results["success"] = True
            results["command"] = ' '.join(cmd)

            return results
            
        except Exception as e:
            logger.error(f"Nmap execution error: {e}")
            return {"error": str(e), "success": False}
    
    def parse_output(self, output: str) -> Dict[str, Any]:
        """
        Parse nmap XML output
        """
        try:
            root = ET.fromstring(output)
            results = {
                "hosts": [],
                "summary": {
                    "total_hosts": 0,
                    "up_hosts": 0,
                    "down_hosts": 0,
                    "total_ports": 0,
                    "open_ports": 0,
                    "closed_ports": 0,
                    "filtered_ports": 0,
                }
            }
            
            for host in root.findall('host'):
                host_data = {
                    "address": None,
                    "hostnames": [],
                    "status": None,
                    "ports": [],
                    "os": None,
                }
                
                # Address
                address = host.find('address')
                if address is not None:
                    host_data["address"] = address.get('addr')
                    host_data["address_type"] = address.get('addrtype')
                
                # Hostnames
                for hostname in host.findall('hostnames/hostname'):
                    host_data["hostnames"].append({
                        "name": hostname.get('name'),
                        "type": hostname.get('type')
                    })
                
                # Status
                status = host.find('status')
                if status is not None:
                    host_data["status"] = status.get('state')
                    if host_data["status"] == 'up':
                        results["summary"]["up_hosts"] += 1
                    else:
                        results["summary"]["down_hosts"] += 1
                
                # Ports
                ports = host.find('ports')
                if ports is not None:
                    for port in ports.findall('port'):
                        port_data = {
                            "port": port.get('portid'),
                            "protocol": port.get('protocol'),
                            "state": None,
                            "service": None,
                        }
                        
                        state = port.find('state')
                        if state is not None:
                            port_data["state"] = state.get('state')
                            if port_data["state"] == 'open':
                                results["summary"]["open_ports"] += 1
                            elif port_data["state"] == 'closed':
                                results["summary"]["closed_ports"] += 1
                            elif port_data["state"] == 'filtered':
                                results["summary"]["filtered_ports"] += 1
                        
                        service = port.find('service')
                        if service is not None:
                            port_data["service"] = {
                                "name": service.get('name'),
                                "product": service.get('product'),
                                "version": service.get('version'),
                                "extrainfo": service.get('extrainfo'),
                            }
                        
                        host_data["ports"].append(port_data)
                
                # OS detection
                os_match = host.find('os/osmatch')
                if os_match is not None:
                    host_data["os"] = {
                        "name": os_match.get('name'),
                        "accuracy": os_match.get('accuracy'),
                    }
                
                results["hosts"].append(host_data)
                results["summary"]["total_hosts"] += 1
                results["summary"]["total_ports"] += len(host_data["ports"])
            
            return results
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse nmap XML: {e}")
            return {"error": f"Parse error: {e}", "raw_output": output}
    
    def get_progress(self) -> int:
        """Get nmap progress"""
        if not self.process:
            return 0

        # Check if process is still running
        if self.process.poll() is not None:
            return 100  # Process completed

        # Try to read nmap stats file if available
        try:
            import os
            from pathlib import Path

            # Nmap writes stats to stderr when using --stats-every
            # For real-time progress, we would need to run with --stats-every
            # and parse the output

            # Check scan status via database
            from app.core.database import SessionLocal
            from app.models.scan import Scan

            db = SessionLocal()
            try:
                scan = db.query(Scan).filter(Scan.id == self.scan_id).first()
                if scan and scan.progress:
                    return scan.progress
            finally:
                db.close()

            # Estimate based on process runtime vs typical scan time
            # This is a rough estimate - nmap progress is hard to determine
            return 50  # Return 50% as default for running scans

        except Exception as e:
            logger.debug(f"Could not determine nmap progress: {e}")
            return 0

    def run_with_progress(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run nmap scan with progress updates"""
        if not self.validate_input(targets, config):
            raise ValueError("Invalid nmap input")

        config = config or {}
        scan_type = config.get('scan_type', 'syn')
        ports = config.get('ports', None)
        scripts = config.get('scripts', [])
        os_detection = config.get('os_detection', False)
        service_detection = config.get('service_detection', True)
        progress_callback = config.get('progress_callback', None)

        # Build nmap command with stats
        cmd = ['nmap', '--stats-every', '5s']

        if scan_type == 'syn':
            cmd.append('-sS')
        elif scan_type == 'tcp':
            cmd.append('-sT')
        elif scan_type == 'udp':
            cmd.append('-sU')

        if ports:
            cmd.extend(['-p', ports])
        if os_detection:
            cmd.append('-O')
        if service_detection:
            cmd.append('-sV')
        if scripts:
            cmd.extend(['--script', ','.join(scripts)])

        cmd.append('-oX')
        cmd.append('-')
        cmd.extend(targets)

        logger.info(f"Running nmap with progress: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Read output and track progress
            import re
            stdout_data = []
            progress_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*%')

            while True:
                line = self.process.stderr.readline()
                if not line and self.process.poll() is not None:
                    break

                # Parse progress from stats output
                match = progress_pattern.search(line)
                if match and progress_callback:
                    progress = float(match.group(1))
                    progress_callback(int(progress))

            stdout, _ = self.process.communicate()
            stdout_data.append(stdout)

            results = self.parse_output(''.join(stdout_data))
            results["success"] = True
            results["command"] = ' '.join(cmd)

            return results

        except Exception as e:
            logger.error(f"Nmap execution error: {e}")
            return {"error": str(e), "success": False}
    
    def cleanup(self):
        """Cleanup nmap process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
