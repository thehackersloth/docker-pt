"""
RustScan - Fast port scanner runner
RustScan is a modern port scanner that can scan all 65k ports in seconds
"""

import subprocess
import json
import re
import logging
from typing import Dict, List, Any
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class RustScanRunner(BaseToolRunner):
    """RustScan fast port scanner runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "rustscan")
        self.process = None

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate RustScan input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run RustScan

        Config options:
            - batch_size: Number of ports to scan per batch (default: 4500)
            - timeout: Timeout in ms (default: 1500)
            - ulimit: Max file descriptors (default: 5000)
            - ports: Specific ports or range (default: all)
            - scan_order: random or serial (default: random)
            - greppable: Use greppable output (default: True)
            - nmap_flags: Additional nmap flags to run after discovery
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid RustScan input - targets required")

        config = config or {}
        batch_size = config.get('batch_size', 4500)
        timeout = config.get('timeout', 1500)
        ulimit = config.get('ulimit', 5000)
        ports = config.get('ports')
        scan_order = config.get('scan_order', 'random')
        greppable = config.get('greppable', True)
        nmap_flags = config.get('nmap_flags', '-sV -sC')

        cmd = ['rustscan']

        # Add targets
        cmd.extend(['-a', ','.join(targets)])

        # Batch size
        cmd.extend(['-b', str(batch_size)])

        # Timeout
        cmd.extend(['-t', str(timeout)])

        # Ulimit
        cmd.extend(['--ulimit', str(ulimit)])

        # Ports
        if ports:
            cmd.extend(['-p', ports])

        # Scan order
        if scan_order == 'serial':
            cmd.append('--scan-order')
            cmd.append('serial')

        # Greppable output
        if greppable:
            cmd.append('-g')

        # Nmap flags (passed after --)
        if nmap_flags:
            cmd.append('--')
            cmd.extend(nmap_flags.split())

        logger.info(f"Running RustScan: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self.process.communicate(timeout=600)

            if self.process.returncode != 0 and "No ports found" not in stderr:
                logger.error(f"RustScan failed: {stderr}")
                return {"error": stderr, "success": False}

            # Parse output
            parsed = self.parse_output(stdout)

            return {
                "success": True,
                "targets": targets,
                "command": ' '.join(cmd),
                "output": parsed,
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
            return {"error": "RustScan execution timed out", "success": False}
        except Exception as e:
            logger.error(f"RustScan execution error: {e}")
            return {"error": str(e), "success": False}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse RustScan output"""
        results = {
            "hosts": [],
            "open_ports": [],
            "summary": {
                "total_hosts": 0,
                "total_open_ports": 0
            }
        }

        current_host = None
        host_data = {}

        for line in output.split('\n'):
            line = line.strip()

            # Parse greppable format: IP -> [PORT1, PORT2, ...]
            if '->' in line and '[' in line:
                match = re.match(r'(.+?)\s*->\s*\[(.+?)\]', line)
                if match:
                    host = match.group(1).strip()
                    ports_str = match.group(2)
                    ports = [int(p.strip()) for p in ports_str.split(',') if p.strip().isdigit()]

                    host_entry = {
                        "address": host,
                        "ports": ports,
                        "port_count": len(ports)
                    }
                    results["hosts"].append(host_entry)
                    results["open_ports"].extend([{"host": host, "port": p} for p in ports])
                    results["summary"]["total_hosts"] += 1
                    results["summary"]["total_open_ports"] += len(ports)

            # Parse standard nmap output if present
            elif '/open/' in line or '/tcp' in line or '/udp' in line:
                parts = line.split()
                if len(parts) >= 2:
                    port_info = parts[0]
                    if '/' in port_info:
                        port_num = port_info.split('/')[0]
                        if port_num.isdigit():
                            results["open_ports"].append({
                                "port": int(port_num),
                                "info": line
                            })

        return results

    def get_progress(self) -> int:
        """Get scan progress"""
        return 0  # RustScan is typically very fast

    def cleanup(self):
        """Cleanup RustScan process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
