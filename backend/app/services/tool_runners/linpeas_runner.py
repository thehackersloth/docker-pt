"""
LinPEAS - Linux Privilege Escalation Awesome Script runner
Comprehensive Linux enumeration script for privilege escalation
"""

import subprocess
import logging
import os
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class LinPEASRunner(BaseToolRunner):
    """LinPEAS privilege escalation enumeration runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "linpeas")
        self.output_dir = Path(f"/tmp/linpeas_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.linpeas_path = "/opt/linpeas/linpeas.sh"
        self.linpeas_url = "https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh"

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate LinPEAS input"""
        return True  # LinPEAS runs locally

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run LinPEAS

        Config options:
            - mode: local or remote (default: local)
            - level: Thoroughness level
                - 1: Only critical checks
                - 2: Important checks
                - 3: All checks (default)
            - options: Specific checks to run
                - a: All checks
                - s: Superfast & stealth
                - P: Password search
                - i: Interesting files
                - n: Network information
                - p: Processes/crons
                - t: Interesting dates
            - no_color: Disable colored output (better for parsing)
            - password: Search for specific password patterns
            - remote_host: For remote execution via SSH
            - remote_user: SSH username
            - remote_password: SSH password or key path
            - output_format: txt, html, json (default: txt)
        """
        config = config or {}
        mode = config.get('mode', 'local')

        if mode == 'remote':
            return self._run_remote(targets[0], config)
        else:
            return self._run_local(config)

    def _run_local(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run LinPEAS locally"""
        level = config.get('level', 3)
        options = config.get('options', 'a')
        no_color = config.get('no_color', True)
        password = config.get('password')

        output_file = self.output_dir / f"linpeas_output_{self.scan_id}.txt"

        # Check if linpeas exists, download if not
        if not os.path.exists(self.linpeas_path):
            self._download_linpeas()

        cmd = ['bash', self.linpeas_path]

        # Options
        if options:
            cmd.append(f'-{options}')

        # No color for easier parsing
        if no_color:
            cmd.extend(['-o', 'system_information,container,cloud,procs_crons_timers,network_information,users_information,software_information,interesting_files,interesting_perms,api_keys_regex'])

        # Password search
        if password:
            cmd.extend(['-P', password])

        logger.info(f"Running LinPEAS locally")

        try:
            with open(output_file, 'w') as f:
                process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={**os.environ, 'TERM': 'xterm'}
                )

                _, stderr = process.communicate(timeout=1800)  # 30 min timeout

            # Parse output
            findings = self._parse_output(output_file)

            return {
                "success": True,
                "mode": "local",
                "findings": findings,
                "critical_count": len(findings.get('critical', [])),
                "high_count": len(findings.get('high', [])),
                "output_file": str(output_file),
                "summary": self._create_summary(findings)
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "LinPEAS timed out", "success": False}
        except Exception as e:
            logger.error(f"LinPEAS error: {e}")
            return {"error": str(e), "success": False}

    def _run_remote(self, host: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run LinPEAS on remote host via SSH"""
        user = config.get('remote_user', 'root')
        password = config.get('remote_password')
        key_path = config.get('key_path')
        port = config.get('port', 22)

        output_file = self.output_dir / f"linpeas_remote_{host.replace('.', '_')}_{self.scan_id}.txt"

        # Build SSH command
        ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no']

        if key_path:
            ssh_cmd.extend(['-i', key_path])
        if port != 22:
            ssh_cmd.extend(['-p', str(port)])

        ssh_cmd.append(f'{user}@{host}')

        # Command to run on remote
        remote_cmd = f"curl -sL {self.linpeas_url} | bash -s -- -a"
        ssh_cmd.append(remote_cmd)

        logger.info(f"Running LinPEAS on remote host: {host}")

        try:
            if password and not key_path:
                # Use sshpass for password auth
                cmd = ['sshpass', '-p', password] + ssh_cmd
            else:
                cmd = ssh_cmd

            with open(output_file, 'w') as f:
                process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True
                )

                _, stderr = process.communicate(timeout=1800)

            findings = self._parse_output(output_file)

            return {
                "success": True,
                "mode": "remote",
                "host": host,
                "findings": findings,
                "output_file": str(output_file),
                "summary": self._create_summary(findings)
            }

        except Exception as e:
            logger.error(f"LinPEAS remote error: {e}")
            return {"error": str(e), "success": False}

    def _download_linpeas(self) -> bool:
        """Download latest LinPEAS"""
        try:
            os.makedirs(os.path.dirname(self.linpeas_path), exist_ok=True)
            subprocess.run(
                ['curl', '-sL', '-o', self.linpeas_path, self.linpeas_url],
                check=True
            )
            os.chmod(self.linpeas_path, 0o755)
            return True
        except Exception as e:
            logger.error(f"Failed to download LinPEAS: {e}")
            return False

    def _parse_output(self, output_file: Path) -> Dict[str, List]:
        """Parse LinPEAS output for findings"""
        findings = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
            "suid_binaries": [],
            "capabilities": [],
            "writable_files": [],
            "cron_jobs": [],
            "interesting_files": [],
            "credentials": [],
            "ssh_keys": [],
            "processes": []
        }

        if not output_file.exists():
            return findings

        try:
            with open(output_file, 'r', errors='ignore') as f:
                content = f.read()

            current_section = None
            lines = content.split('\n')

            for line in lines:
                line_stripped = line.strip()

                # Detect critical/high findings (usually marked with colors in original)
                if any(x in line.lower() for x in ['95%', '99%', 'critical', 'highly probable']):
                    findings["critical"].append(line_stripped)
                elif any(x in line.lower() for x in ['70%', '75%', 'high probability']):
                    findings["high"].append(line_stripped)

                # SUID binaries
                if 'suid' in line.lower() and ('/' in line or 'binary' in line.lower()):
                    findings["suid_binaries"].append(line_stripped)

                # Capabilities
                if 'cap_' in line.lower():
                    findings["capabilities"].append(line_stripped)

                # Writable files/directories
                if 'writable' in line.lower() and '/' in line:
                    findings["writable_files"].append(line_stripped)

                # Cron jobs
                if 'cron' in line.lower() and ('*' in line or '/' in line):
                    findings["cron_jobs"].append(line_stripped)

                # Credentials/passwords
                if any(x in line.lower() for x in ['password', 'passwd', 'credential', 'secret']):
                    if '=' in line or ':' in line:
                        findings["credentials"].append(line_stripped)

                # SSH keys
                if 'ssh' in line.lower() and ('rsa' in line.lower() or 'id_' in line.lower() or 'authorized' in line.lower()):
                    findings["ssh_keys"].append(line_stripped)

                # Interesting files
                if any(x in line.lower() for x in ['.bash_history', '.mysql_history', '.git', 'config', '.env']):
                    findings["interesting_files"].append(line_stripped)

        except Exception as e:
            logger.error(f"Failed to parse LinPEAS output: {e}")

        # Deduplicate
        for key in findings:
            findings[key] = list(set(findings[key]))[:50]  # Limit to 50 per category

        return findings

    def _create_summary(self, findings: Dict) -> Dict[str, Any]:
        """Create a summary of findings"""
        return {
            "critical_findings": len(findings.get('critical', [])),
            "high_findings": len(findings.get('high', [])),
            "suid_binaries": len(findings.get('suid_binaries', [])),
            "capabilities": len(findings.get('capabilities', [])),
            "writable_files": len(findings.get('writable_files', [])),
            "credentials_found": len(findings.get('credentials', [])),
            "ssh_keys_found": len(findings.get('ssh_keys', [])),
            "cron_jobs": len(findings.get('cron_jobs', []))
        }

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse LinPEAS text output"""
        return {"raw_output": output}
