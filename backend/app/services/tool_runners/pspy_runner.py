"""
pspy - Linux process monitor runner
Monitors Linux processes without root permissions to detect cron jobs and scheduled tasks
"""

import subprocess
import logging
import os
import time
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class PspyRunner(BaseToolRunner):
    """pspy process monitor runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "pspy")
        self.output_dir = Path(f"/tmp/pspy_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pspy_path = "/opt/pspy"
        self.pspy_urls = {
            "64": "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy64",
            "32": "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy32",
            "64s": "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy64s",
            "32s": "https://github.com/DominicBreuker/pspy/releases/latest/download/pspy32s"
        }
        self.process = None

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate pspy input"""
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run pspy

        Config options:
            - mode: local or remote (default: local)
            - arch: 64, 32, 64s (small), 32s (small) (default: 64)
            - duration: How long to monitor in seconds (default: 300)
            - print_commands: Print commands (default: True)
            - filesystem_events: Monitor filesystem events (default: True)
            - dirs: Directories to watch (comma-separated)
            - remote_host: For remote execution
            - remote_user: SSH username
            - remote_password: SSH password or key path
        """
        config = config or {}
        mode = config.get('mode', 'local')

        if mode == 'remote':
            return self._run_remote(targets[0] if targets else None, config)
        else:
            return self._run_local(config)

    def _run_local(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run pspy locally"""
        arch = config.get('arch', '64')
        duration = config.get('duration', 300)
        print_commands = config.get('print_commands', True)
        filesystem_events = config.get('filesystem_events', True)
        dirs = config.get('dirs')

        output_file = self.output_dir / f"pspy_output_{self.scan_id}.txt"

        # Download if needed
        pspy_exe = Path(self.pspy_path) / f"pspy{arch}"
        if not pspy_exe.exists():
            self._download_pspy(arch)

        cmd = [str(pspy_exe)]

        # Options
        if print_commands:
            cmd.append('-p')
        if filesystem_events:
            cmd.append('-f')
        if dirs:
            cmd.extend(['-d', dirs])

        # Color output disabled for parsing
        cmd.append('-c')

        logger.info(f"Running pspy for {duration} seconds")

        try:
            with open(output_file, 'w') as f:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Run for specified duration
                time.sleep(duration)

                # Stop pspy
                self.process.terminate()
                self.process.wait(timeout=5)

            # Parse output
            findings = self._parse_output(output_file)

            return {
                "success": True,
                "mode": "local",
                "duration": duration,
                "findings": findings,
                "output_file": str(output_file),
                "summary": self._create_summary(findings)
            }

        except Exception as e:
            logger.error(f"pspy error: {e}")
            if self.process:
                self.process.kill()
            return {"error": str(e), "success": False}

    def _run_remote(self, host: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run pspy on remote host"""
        if not host:
            return {"error": "Host required for remote execution", "success": False}

        user = config.get('remote_user', 'root')
        password = config.get('remote_password')
        key_path = config.get('key_path')
        arch = config.get('arch', '64')
        duration = config.get('duration', 300)

        output_file = self.output_dir / f"pspy_remote_{host.replace('.', '_')}_{self.scan_id}.txt"

        # Build SSH command
        ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no']
        if key_path:
            ssh_cmd.extend(['-i', key_path])
        ssh_cmd.append(f'{user}@{host}')

        # Download and run pspy on remote
        pspy_url = self.pspy_urls.get(arch, self.pspy_urls['64'])
        remote_cmd = f"curl -sL {pspy_url} -o /tmp/pspy && chmod +x /tmp/pspy && timeout {duration} /tmp/pspy -p -f -c; rm /tmp/pspy"
        ssh_cmd.append(remote_cmd)

        logger.info(f"Running pspy on remote host: {host}")

        try:
            if password and not key_path:
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

                process.wait(timeout=duration + 60)

            findings = self._parse_output(output_file)

            return {
                "success": True,
                "mode": "remote",
                "host": host,
                "duration": duration,
                "findings": findings,
                "output_file": str(output_file),
                "summary": self._create_summary(findings)
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "pspy remote execution timed out", "success": False}
        except Exception as e:
            logger.error(f"pspy remote error: {e}")
            return {"error": str(e), "success": False}

    def _download_pspy(self, arch: str = '64') -> bool:
        """Download pspy binary"""
        try:
            os.makedirs(self.pspy_path, exist_ok=True)
            url = self.pspy_urls.get(arch, self.pspy_urls['64'])
            output = Path(self.pspy_path) / f"pspy{arch}"

            subprocess.run(['curl', '-sL', '-o', str(output), url], check=True)
            os.chmod(str(output), 0o755)
            return True
        except Exception as e:
            logger.error(f"Failed to download pspy: {e}")
            return False

    def _parse_output(self, output_file: Path) -> Dict[str, List]:
        """Parse pspy output"""
        findings = {
            "cron_jobs": [],
            "scheduled_tasks": [],
            "interesting_commands": [],
            "root_processes": [],
            "network_activity": [],
            "file_modifications": [],
            "scripts_executed": []
        }

        if not output_file.exists():
            return findings

        try:
            with open(output_file, 'r', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    # Look for cron/scheduled tasks
                    if 'cron' in line.lower() or '/etc/cron' in line:
                        findings["cron_jobs"].append(line)

                    # Root processes
                    if 'UID=0' in line or 'uid=0' in line:
                        findings["root_processes"].append(line)

                    # Interesting commands
                    interesting_patterns = [
                        'password', 'passwd', 'secret', 'key', 'token',
                        'backup', 'mysql', 'postgres', 'mongo', 'redis',
                        'curl', 'wget', 'nc ', 'netcat', 'ncat',
                        'python', 'perl', 'ruby', 'bash', 'sh ', '/bin/sh'
                    ]
                    if any(p in line.lower() for p in interesting_patterns):
                        findings["interesting_commands"].append(line)

                    # Scripts
                    if '.sh' in line or '.py' in line or '.pl' in line:
                        findings["scripts_executed"].append(line)

                    # File modifications
                    if 'CLOSE_WRITE' in line or 'CREATE' in line or 'MODIFY' in line:
                        findings["file_modifications"].append(line)

        except Exception as e:
            logger.error(f"Failed to parse pspy output: {e}")

        # Deduplicate and limit
        for key in findings:
            findings[key] = list(set(findings[key]))[:100]

        return findings

    def _create_summary(self, findings: Dict) -> Dict[str, Any]:
        """Create summary"""
        return {
            "cron_jobs_found": len(findings.get('cron_jobs', [])),
            "root_processes": len(findings.get('root_processes', [])),
            "interesting_commands": len(findings.get('interesting_commands', [])),
            "scripts_executed": len(findings.get('scripts_executed', []))
        }

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse pspy output"""
        return {"raw_output": output}

    def cleanup(self):
        """Cleanup pspy process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)
