"""
Evil-WinRM - Windows Remote Management (WinRM) shell runner
Used for post-exploitation on Windows systems
"""

import subprocess
import logging
import os
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class EvilWinRMRunner(BaseToolRunner):
    """Evil-WinRM Windows remote management runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "evil-winrm")
        self.output_dir = Path(f"/tmp/evilwinrm_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Evil-WinRM input"""
        config = config or {}
        if not targets:
            return False
        # Need either password, hash, or key
        if not config.get('password') and not config.get('hash') and not config.get('key_path'):
            return False
        if not config.get('username'):
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Evil-WinRM

        Config options:
            - username: Username (required)
            - password: Password
            - hash: NTLM hash (pass-the-hash)
            - key_path: Path to private key file
            - ssl: Use SSL (default: False)
            - command: Single command to execute
            - script: PowerShell script to execute
            - upload: File to upload (source, dest tuple)
            - download: File to download (source, dest tuple)
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid Evil-WinRM input - target, username, and authentication required")

        config = config or {}
        target = targets[0]
        username = config.get('username')
        password = config.get('password')
        hash_value = config.get('hash')
        key_path = config.get('key_path')
        ssl = config.get('ssl', False)
        command = config.get('command')
        script = config.get('script')
        upload = config.get('upload')
        download = config.get('download')

        # Build base command
        cmd = ['evil-winrm', '-i', target, '-u', username]

        # Authentication
        if password:
            cmd.extend(['-p', password])
        elif hash_value:
            cmd.extend(['-H', hash_value])
        elif key_path:
            cmd.extend(['-k', key_path])
            cmd.extend(['-c', config.get('cert_path', key_path.replace('.key', '.crt'))])

        # SSL
        if ssl:
            cmd.append('-S')

        # Execute command or get shell info
        if command:
            return self._execute_command(cmd, command, target, config)
        elif script:
            return self._execute_script(cmd, script, target, config)
        elif upload:
            return self._upload_file(cmd, upload, target, config)
        elif download:
            return self._download_file(cmd, download, target, config)
        else:
            # Just test connection
            return self._test_connection(cmd, target, config)

    def _execute_command(self, base_cmd: List[str], command: str, target: str, config: Dict) -> Dict[str, Any]:
        """Execute a single command"""
        # Create a script file with the command
        script_file = self.output_dir / "command.ps1"
        with open(script_file, 'w') as f:
            f.write(command)
            f.write('\nexit')

        cmd = base_cmd + ['-s', str(self.output_dir)]

        logger.info(f"Running Evil-WinRM command on {target}")

        try:
            # Use pexpect-like approach with subprocess
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Send command and exit
            input_commands = f"{command}\nexit\n"
            stdout, stderr = process.communicate(input=input_commands, timeout=120)

            return {
                "success": process.returncode == 0,
                "target": target,
                "command": command,
                "output": stdout,
                "error": stderr if process.returncode != 0 else None
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Evil-WinRM command timed out", "success": False}
        except Exception as e:
            logger.error(f"Evil-WinRM command error: {e}")
            return {"error": str(e), "success": False}

    def _execute_script(self, base_cmd: List[str], script: str, target: str, config: Dict) -> Dict[str, Any]:
        """Execute a PowerShell script"""
        # Save script to file
        script_file = self.output_dir / "script.ps1"
        with open(script_file, 'w') as f:
            f.write(script)

        cmd = base_cmd + ['-s', str(self.output_dir)]

        logger.info(f"Running Evil-WinRM script on {target}")

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Invoke script and exit
            input_commands = f"Invoke-Script script.ps1\nexit\n"
            stdout, stderr = process.communicate(input=input_commands, timeout=300)

            return {
                "success": process.returncode == 0,
                "target": target,
                "script_name": "script.ps1",
                "output": stdout,
                "error": stderr if process.returncode != 0 else None
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Evil-WinRM script timed out", "success": False}
        except Exception as e:
            logger.error(f"Evil-WinRM script error: {e}")
            return {"error": str(e), "success": False}

    def _upload_file(self, base_cmd: List[str], upload: tuple, target: str, config: Dict) -> Dict[str, Any]:
        """Upload a file to the target"""
        source, dest = upload
        cmd = base_cmd

        logger.info(f"Uploading {source} to {target}:{dest}")

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            input_commands = f"upload {source} {dest}\nexit\n"
            stdout, stderr = process.communicate(input=input_commands, timeout=300)

            return {
                "success": "Uploaded" in stdout or process.returncode == 0,
                "target": target,
                "action": "upload",
                "source": source,
                "destination": dest,
                "output": stdout
            }

        except Exception as e:
            logger.error(f"Evil-WinRM upload error: {e}")
            return {"error": str(e), "success": False}

    def _download_file(self, base_cmd: List[str], download: tuple, target: str, config: Dict) -> Dict[str, Any]:
        """Download a file from the target"""
        source, dest = download
        cmd = base_cmd

        logger.info(f"Downloading {target}:{source} to {dest}")

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            input_commands = f"download {source} {dest}\nexit\n"
            stdout, stderr = process.communicate(input=input_commands, timeout=300)

            return {
                "success": "Downloaded" in stdout or os.path.exists(dest),
                "target": target,
                "action": "download",
                "source": source,
                "destination": dest,
                "output": stdout
            }

        except Exception as e:
            logger.error(f"Evil-WinRM download error: {e}")
            return {"error": str(e), "success": False}

    def _test_connection(self, base_cmd: List[str], target: str, config: Dict) -> Dict[str, Any]:
        """Test WinRM connection"""
        logger.info(f"Testing Evil-WinRM connection to {target}")

        try:
            process = subprocess.Popen(
                base_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Quick test - get hostname and exit
            input_commands = "hostname\nwhoami\nexit\n"
            stdout, stderr = process.communicate(input=input_commands, timeout=30)

            connected = "Evil-WinRM" in stdout or process.returncode == 0

            return {
                "success": connected,
                "target": target,
                "connected": connected,
                "output": stdout,
                "error": stderr if not connected else None
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Evil-WinRM connection timed out", "success": False}
        except Exception as e:
            logger.error(f"Evil-WinRM connection error: {e}")
            return {"error": str(e), "success": False}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Evil-WinRM output"""
        return {"raw_output": output}
