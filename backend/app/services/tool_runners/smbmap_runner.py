"""
SMBMap - SMB share enumeration and access tool runner
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class SMBMapRunner(BaseToolRunner):
    """SMBMap share enumeration runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "smbmap")
        self.output_dir = Path(f"/tmp/smbmap_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate SMBMap input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run SMBMap

        Config options:
            - username: Username for authentication
            - password: Password for authentication
            - hash: NTLM hash (pass-the-hash)
            - domain: Domain name
            - port: SMB port (default: 445)
            - recurse: Recursively list dirs (default: False)
            - depth: Recursion depth (default: 5)
            - pattern: File pattern to search
            - exclude: Exclude pattern
            - download: Download matching files
            - upload: Upload a file (source, dest tuple)
            - execute: Execute a command
            - admin: Only show admin shares
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid SMBMap input - target required")

        config = config or {}
        results = []

        for target in targets:
            result = self._scan_target(target, config)
            results.append(result)

        if len(results) == 1:
            return results[0]

        return {
            "success": all(r.get('success', False) for r in results),
            "targets": targets,
            "results": results,
            "total_shares": sum(len(r.get('shares', [])) for r in results)
        }

    def _scan_target(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Scan a single target"""
        username = config.get('username', '')
        password = config.get('password', '')
        hash_value = config.get('hash')
        domain = config.get('domain', '.')
        port = config.get('port', 445)
        recurse = config.get('recurse', False)
        depth = config.get('depth', 5)
        pattern = config.get('pattern')
        admin_only = config.get('admin', False)

        output_file = self.output_dir / f"smbmap_{target.replace('.', '_')}_{self.scan_id}.txt"

        cmd = ['smbmap', '-H', target]

        # Port
        if port != 445:
            cmd.extend(['-P', str(port)])

        # Authentication
        if username:
            cmd.extend(['-u', username])
        if password:
            cmd.extend(['-p', password])
        if hash_value:
            cmd.extend(['-p', f'aad3b435b51404eeaad3b435b51404ee:{hash_value}'])
        if domain and domain != '.':
            cmd.extend(['-d', domain])

        # Options
        if recurse:
            cmd.extend(['-R', '--depth', str(depth)])
        if pattern:
            cmd.extend(['-A', pattern])
        if admin_only:
            cmd.append('-a')

        logger.info(f"Running SMBMap on {target}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=300)

            # Save output
            with open(output_file, 'w') as f:
                f.write(stdout)

            # Parse output
            parsed = self._parse_output(stdout)

            return {
                "success": True,
                "target": target,
                "shares": parsed.get('shares', []),
                "readable_shares": parsed.get('readable', []),
                "writable_shares": parsed.get('writable', []),
                "files_found": parsed.get('files', []),
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "SMBMap timed out", "success": False, "target": target}
        except Exception as e:
            logger.error(f"SMBMap error: {e}")
            return {"error": str(e), "success": False, "target": target}

    def _parse_output(self, output: str) -> Dict[str, Any]:
        """Parse SMBMap output"""
        results = {
            "shares": [],
            "readable": [],
            "writable": [],
            "files": []
        }

        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Parse share listings
            if 'READ' in line or 'WRITE' in line or 'NO ACCESS' in line:
                parts = line.split()
                if len(parts) >= 2:
                    share = {
                        "name": parts[0],
                        "permissions": [],
                        "comment": ""
                    }

                    if 'READ' in line:
                        share["permissions"].append("READ")
                        results["readable"].append(parts[0])
                    if 'WRITE' in line:
                        share["permissions"].append("WRITE")
                        results["writable"].append(parts[0])
                    if 'NO ACCESS' in line:
                        share["permissions"].append("NO ACCESS")

                    results["shares"].append(share)

            # Parse file listings (when using -R)
            if line.startswith('dr-') or line.startswith('-r-') or line.startswith('./'):
                results["files"].append(line)

        return results

    def download_file(self, target: str, share: str, remote_path: str, local_path: str, config: Dict) -> Dict[str, Any]:
        """Download a file from SMB share"""
        username = config.get('username', '')
        password = config.get('password', '')
        domain = config.get('domain', '.')

        cmd = [
            'smbmap', '-H', target,
            '-u', username, '-p', password, '-d', domain,
            '--download', f'{share}/{remote_path}'
        ]

        try:
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            return {
                "success": process.returncode == 0,
                "target": target,
                "share": share,
                "file": remote_path,
                "output": process.stdout
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    def upload_file(self, target: str, share: str, local_path: str, remote_path: str, config: Dict) -> Dict[str, Any]:
        """Upload a file to SMB share"""
        username = config.get('username', '')
        password = config.get('password', '')
        domain = config.get('domain', '.')

        cmd = [
            'smbmap', '-H', target,
            '-u', username, '-p', password, '-d', domain,
            '--upload', local_path,
            f'{share}/{remote_path}'
        ]

        try:
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            return {
                "success": process.returncode == 0,
                "target": target,
                "share": share,
                "file": remote_path,
                "output": process.stdout
            }
        except Exception as e:
            return {"error": str(e), "success": False}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse output"""
        return self._parse_output(output)
