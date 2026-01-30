"""
NetExec (nxc) - Network execution tool runner
The successor to CrackMapExec for AD/SMB/WinRM enumeration and exploitation
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class NetExecRunner(BaseToolRunner):
    """NetExec (nxc) network execution runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "netexec")
        self.output_dir = Path(f"/tmp/netexec_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate NetExec input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run NetExec

        Config options:
            - protocol: smb, ssh, winrm, ldap, mssql, rdp, ftp, wmi (default: smb)
            - username: Username for authentication
            - password: Password for authentication
            - hash: NTLM hash (pass-the-hash)
            - domain: Domain name
            - local_auth: Use local authentication
            - module: Module to run (e.g., lsassy, mimikatz, enum_av)
            - module_options: Options for the module
            - action: shares, sessions, disks, loggedon-users, users, groups, computers, pass-pol
            - spider: Spider shares for files
            - spider_folder: Folder to spider
            - pattern: File pattern to search
            - content: Search file contents
            - execute: Command to execute
            - execute_method: smbexec, wmiexec, atexec, mmcexec
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid NetExec input - target required")

        config = config or {}
        protocol = config.get('protocol', 'smb')
        username = config.get('username')
        password = config.get('password')
        hash_value = config.get('hash')
        domain = config.get('domain')
        local_auth = config.get('local_auth', False)
        module = config.get('module')
        module_options = config.get('module_options', {})
        action = config.get('action')
        spider = config.get('spider')
        pattern = config.get('pattern')
        content = config.get('content')
        execute = config.get('execute')
        execute_method = config.get('execute_method')

        # Build command
        cmd = ['nxc', protocol]

        # Targets
        cmd.extend(targets)

        # Credentials
        if username:
            cmd.extend(['-u', username])
        if password:
            cmd.extend(['-p', password])
        if hash_value:
            cmd.extend(['-H', hash_value])
        if domain:
            cmd.extend(['-d', domain])
        if local_auth:
            cmd.append('--local-auth')

        # Module
        if module:
            cmd.extend(['-M', module])
            for key, value in module_options.items():
                cmd.extend(['-o', f'{key}={value}'])

        # Actions
        if action:
            if action == 'shares':
                cmd.append('--shares')
            elif action == 'sessions':
                cmd.append('--sessions')
            elif action == 'disks':
                cmd.append('--disks')
            elif action == 'loggedon-users':
                cmd.append('--loggedon-users')
            elif action == 'users':
                cmd.append('--users')
            elif action == 'groups':
                cmd.append('--groups')
            elif action == 'computers':
                cmd.append('--computers')
            elif action == 'pass-pol':
                cmd.append('--pass-pol')

        # Spider
        if spider:
            cmd.extend(['--spider', spider])
            if pattern:
                cmd.extend(['--pattern', pattern])
            if content:
                cmd.extend(['--content', content])

        # Execute command
        if execute:
            cmd.extend(['-x', execute])
            if execute_method:
                cmd.extend(['--exec-method', execute_method])

        # Output format
        cmd.append('--log')
        output_file = self.output_dir / f"netexec_{protocol}_{self.scan_id}.log"
        cmd.append(str(output_file))

        logger.info(f"Running NetExec: {' '.join(cmd[:8])}...")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=600)

            # Parse output
            parsed = self.parse_output(stdout)

            return {
                "success": True,
                "protocol": protocol,
                "targets": targets,
                "results": parsed,
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "NetExec timed out", "success": False}
        except FileNotFoundError:
            # Fall back to crackmapexec if nxc not found
            logger.info("nxc not found, trying crackmapexec")
            return self._run_cme_fallback(targets, config)
        except Exception as e:
            logger.error(f"NetExec error: {e}")
            return {"error": str(e), "success": False}

    def _run_cme_fallback(self, targets: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to CrackMapExec if NetExec not available"""
        config = config or {}
        protocol = config.get('protocol', 'smb')

        cmd = ['crackmapexec', protocol]
        cmd.extend(targets)

        # Add credentials if provided
        if config.get('username'):
            cmd.extend(['-u', config['username']])
        if config.get('password'):
            cmd.extend(['-p', config['password']])
        if config.get('hash'):
            cmd.extend(['-H', config['hash']])
        if config.get('domain'):
            cmd.extend(['-d', config['domain']])

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=600)

            return {
                "success": True,
                "tool": "crackmapexec (fallback)",
                "protocol": protocol,
                "targets": targets,
                "results": self.parse_output(stdout),
                "raw_output": stdout
            }

        except Exception as e:
            return {"error": str(e), "success": False}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse NetExec/CME output"""
        results = {
            "hosts": [],
            "credentials": [],
            "shares": [],
            "users": [],
            "admin_access": []
        }

        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Parse host results
            if 'SMB' in line or 'WINRM' in line or 'SSH' in line:
                if '(Pwn3d!)' in line or 'Pwn3d!' in line:
                    results["admin_access"].append(line)
                elif '+' in line:
                    results["hosts"].append(line)

            # Parse shares
            if 'READ' in line or 'WRITE' in line:
                results["shares"].append(line)

            # Parse credentials
            if ':' in line and ('$' not in line or 'NTLM' in line):
                if any(x in line.lower() for x in ['password', 'hash', 'credential']):
                    results["credentials"].append(line)

        return results
