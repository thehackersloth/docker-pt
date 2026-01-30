"""
Ligolo-ng - Tunneling/Pivoting tool runner
Advanced pivoting tool using TUN interfaces
"""

import subprocess
import logging
import time
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class LigoloRunner(BaseToolRunner):
    """Ligolo-ng tunneling tool runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "ligolo")
        self.process = None
        self.output_dir = Path(f"/tmp/ligolo_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Ligolo input"""
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Ligolo-ng

        Config options:
            - mode: proxy (server) or agent (client) (default: proxy)
            - port: Port for proxy to listen on (default: 11601)
            - laddr: Listen address for proxy (default: 0.0.0.0)
            - selfcert: Generate self-signed certificate
            - certfile: Path to certificate file
            - keyfile: Path to key file
            - connect: Server address for agent mode
            - ignore_cert: Ignore certificate validation (agent)
            - retry: Retry connection on failure (agent)
        """
        config = config or {}
        mode = config.get('mode', 'proxy')

        if mode == 'proxy':
            return self._run_proxy(config)
        else:
            return self._run_agent(config)

    def _run_proxy(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start Ligolo proxy (server)"""
        port = config.get('port', 11601)
        laddr = config.get('laddr', '0.0.0.0')
        selfcert = config.get('selfcert', True)
        certfile = config.get('certfile')
        keyfile = config.get('keyfile')

        cmd = ['ligolo-proxy']

        # Listen address
        cmd.extend(['-laddr', f'{laddr}:{port}'])

        # Certificates
        if selfcert:
            cmd.append('-selfcert')
        elif certfile and keyfile:
            cmd.extend(['-certfile', certfile])
            cmd.extend(['-keyfile', keyfile])

        logger.info(f"Starting Ligolo proxy: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait briefly to check startup
            time.sleep(2)

            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                return {
                    "success": False,
                    "error": stderr or "Proxy failed to start",
                    "output": stdout
                }

            return {
                "success": True,
                "mode": "proxy",
                "listen_address": f"{laddr}:{port}",
                "process_id": self.process.pid,
                "message": f"Ligolo proxy started on {laddr}:{port}",
                "next_steps": [
                    "Run agent on target: ligolo-agent -connect <your-ip>:11601 -ignore-cert",
                    "In proxy console: session, ifconfig, start"
                ]
            }

        except FileNotFoundError:
            return {"error": "ligolo-proxy not found", "success": False}
        except Exception as e:
            logger.error(f"Ligolo proxy error: {e}")
            return {"error": str(e), "success": False}

    def _run_agent(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start Ligolo agent (client)"""
        connect = config.get('connect')
        ignore_cert = config.get('ignore_cert', True)
        retry = config.get('retry', True)

        if not connect:
            return {"error": "Server address required for agent mode", "success": False}

        cmd = ['ligolo-agent']

        # Connect to server
        cmd.extend(['-connect', connect])

        # Certificate validation
        if ignore_cert:
            cmd.append('-ignore-cert')

        # Retry
        if retry:
            cmd.append('-retry')

        logger.info(f"Starting Ligolo agent: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait briefly
            time.sleep(3)

            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                return {
                    "success": False,
                    "error": stderr or "Agent failed to connect",
                    "output": stdout
                }

            return {
                "success": True,
                "mode": "agent",
                "server": connect,
                "process_id": self.process.pid,
                "message": f"Ligolo agent connecting to {connect}"
            }

        except FileNotFoundError:
            return {"error": "ligolo-agent not found", "success": False}
        except Exception as e:
            logger.error(f"Ligolo agent error: {e}")
            return {"error": str(e), "success": False}

    def setup_interface(self, interface_name: str = "ligolo") -> Dict[str, Any]:
        """Setup TUN interface for Ligolo"""
        try:
            # Create interface
            subprocess.run(['ip', 'tuntap', 'add', 'user', 'root', 'mode', 'tun', interface_name], check=True)
            subprocess.run(['ip', 'link', 'set', interface_name, 'up'], check=True)

            return {
                "success": True,
                "interface": interface_name,
                "message": f"Interface {interface_name} created and activated"
            }
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "success": False}
        except Exception as e:
            return {"error": str(e), "success": False}

    def add_route(self, network: str, interface_name: str = "ligolo") -> Dict[str, Any]:
        """Add route through Ligolo interface"""
        try:
            subprocess.run(['ip', 'route', 'add', network, 'dev', interface_name], check=True)
            return {
                "success": True,
                "network": network,
                "interface": interface_name,
                "message": f"Route to {network} added via {interface_name}"
            }
        except subprocess.CalledProcessError as e:
            return {"error": str(e), "success": False}

    def stop(self) -> Dict[str, Any]:
        """Stop Ligolo process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
            return {"success": True, "message": "Ligolo stopped"}
        return {"success": False, "message": "No running process"}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Ligolo output"""
        return {"raw_output": output}

    def cleanup(self):
        """Cleanup Ligolo process"""
        self.stop()
