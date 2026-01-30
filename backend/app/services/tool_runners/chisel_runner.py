"""
Chisel - TCP/UDP tunnel over HTTP runner
Used for pivoting and port forwarding through restricted networks
"""

import subprocess
import logging
import time
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class ChiselRunner(BaseToolRunner):
    """Chisel tunneling tool runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "chisel")
        self.process = None
        self.output_dir = Path(f"/tmp/chisel_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Chisel input"""
        config = config or {}
        mode = config.get('mode', 'server')
        if mode == 'client' and not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Chisel

        Config options:
            - mode: server or client (default: server)
            - port: Port for server to listen on (default: 8080)
            - reverse: Enable reverse port forwarding
            - socks: Enable SOCKS5 proxy
            - tunnels: List of tunnel definitions for client
                Format: "local_port:remote_host:remote_port" or "R:remote_port:local_host:local_port"
            - auth: Authentication credentials (user:pass)
            - fingerprint: Server fingerprint for client verification
            - keepalive: Keepalive interval (default: 25s)
            - max_retry: Max retry count for client
            - proxy: HTTP proxy for client
            - tls_skip_verify: Skip TLS verification
        """
        config = config or {}
        mode = config.get('mode', 'server')

        if mode == 'server':
            return self._run_server(config)
        else:
            return self._run_client(targets[0], config)

    def _run_server(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start Chisel server"""
        port = config.get('port', 8080)
        reverse = config.get('reverse', True)
        socks = config.get('socks', False)
        auth = config.get('auth')
        keepalive = config.get('keepalive', '25s')

        cmd = ['chisel', 'server']

        # Port
        cmd.extend(['--port', str(port)])

        # Reverse mode
        if reverse:
            cmd.append('--reverse')

        # SOCKS
        if socks:
            cmd.append('--socks5')

        # Auth
        if auth:
            cmd.extend(['--auth', auth])

        # Keepalive
        cmd.extend(['--keepalive', keepalive])

        logger.info(f"Starting Chisel server: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait briefly to check if it started
            time.sleep(2)

            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                return {
                    "success": False,
                    "error": stderr or "Server failed to start",
                    "output": stdout
                }

            return {
                "success": True,
                "mode": "server",
                "port": port,
                "reverse": reverse,
                "socks": socks,
                "process_id": self.process.pid,
                "message": f"Chisel server started on port {port}"
            }

        except Exception as e:
            logger.error(f"Chisel server error: {e}")
            return {"error": str(e), "success": False}

    def _run_client(self, server: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start Chisel client"""
        tunnels = config.get('tunnels', [])
        auth = config.get('auth')
        fingerprint = config.get('fingerprint')
        keepalive = config.get('keepalive', '25s')
        max_retry = config.get('max_retry', 10)
        proxy = config.get('proxy')
        tls_skip_verify = config.get('tls_skip_verify', False)

        if not tunnels:
            return {"error": "No tunnels specified", "success": False}

        cmd = ['chisel', 'client']

        # Auth
        if auth:
            cmd.extend(['--auth', auth])

        # Fingerprint
        if fingerprint:
            cmd.extend(['--fingerprint', fingerprint])

        # Keepalive
        cmd.extend(['--keepalive', keepalive])

        # Max retry
        cmd.extend(['--max-retry-count', str(max_retry)])

        # Proxy
        if proxy:
            cmd.extend(['--proxy', proxy])

        # TLS
        if tls_skip_verify:
            cmd.append('--tls-skip-verify')

        # Server
        cmd.append(server)

        # Tunnels
        cmd.extend(tunnels)

        logger.info(f"Starting Chisel client: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait briefly to check connection
            time.sleep(3)

            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                return {
                    "success": False,
                    "error": stderr or "Client failed to connect",
                    "output": stdout
                }

            return {
                "success": True,
                "mode": "client",
                "server": server,
                "tunnels": tunnels,
                "process_id": self.process.pid,
                "message": f"Chisel client connected to {server}"
            }

        except Exception as e:
            logger.error(f"Chisel client error: {e}")
            return {"error": str(e), "success": False}

    def stop(self) -> Dict[str, Any]:
        """Stop Chisel process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
            return {"success": True, "message": "Chisel stopped"}
        return {"success": False, "message": "No running process"}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Chisel output"""
        return {"raw_output": output}

    def cleanup(self):
        """Cleanup Chisel process"""
        self.stop()
