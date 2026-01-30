"""
Enum4linux - SMB/Samba enumeration tool runner
Also supports enum4linux-ng (next generation)
"""

import subprocess
import re
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class Enum4linuxRunner(BaseToolRunner):
    """Enum4linux SMB enumeration runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "enum4linux")
        self.output_dir = Path(f"/tmp/enum4linux_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Enum4linux input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Enum4linux

        Config options:
            - use_ng: Use enum4linux-ng instead (default: True if available)
            - username: Username for authentication
            - password: Password for authentication
            - workgroup: Workgroup/domain name
            - all: Do all simple enumeration (default: True)
            - users: Enumerate users
            - shares: Enumerate shares
            - groups: Enumerate groups
            - password_policy: Get password policy
            - rid_range: RID range for user enumeration (default: 500-550,1000-1050)
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid Enum4linux input - target required")

        config = config or {}
        target = targets[0]
        use_ng = config.get('use_ng', True)

        # Try enum4linux-ng first if requested
        if use_ng:
            result = self._run_enum4linux_ng(target, config)
            if result.get('success'):
                return result
            # Fall back to classic enum4linux
            logger.info("Falling back to classic enum4linux")

        return self._run_enum4linux_classic(target, config)

    def _run_enum4linux_ng(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run enum4linux-ng"""
        username = config.get('username')
        password = config.get('password')
        output_file = self.output_dir / f"{target.replace('.', '_')}_ng.json"

        cmd = ['enum4linux-ng', '-A', target]

        # Credentials
        if username:
            cmd.extend(['-u', username])
        if password:
            cmd.extend(['-p', password])

        # Output
        cmd.extend(['-oJ', str(output_file)])

        logger.info(f"Running enum4linux-ng: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=600)

            # Parse JSON output
            results = {}
            if output_file.exists():
                import json
                with open(output_file, 'r') as f:
                    try:
                        results = json.load(f)
                    except:
                        pass

            return {
                "success": True,
                "tool": "enum4linux-ng",
                "target": target,
                "os_info": results.get('os_info', {}),
                "users": results.get('users', {}),
                "groups": results.get('groups', {}),
                "shares": results.get('shares', {}),
                "password_policy": results.get('policy', {}),
                "domain_info": results.get('domain', {}),
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except FileNotFoundError:
            return {"success": False, "error": "enum4linux-ng not found"}
        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "enum4linux-ng timed out", "success": False}
        except Exception as e:
            logger.error(f"enum4linux-ng error: {e}")
            return {"error": str(e), "success": False}

    def _run_enum4linux_classic(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run classic enum4linux"""
        username = config.get('username')
        password = config.get('password')
        workgroup = config.get('workgroup')
        do_all = config.get('all', True)
        enum_users = config.get('users', False)
        enum_shares = config.get('shares', False)
        enum_groups = config.get('groups', False)
        password_policy = config.get('password_policy', False)
        rid_range = config.get('rid_range', '500-550,1000-1050')

        cmd = ['enum4linux']

        # Credentials
        if username:
            cmd.extend(['-u', username])
        if password:
            cmd.extend(['-p', password])
        if workgroup:
            cmd.extend(['-w', workgroup])

        # Enumeration options
        if do_all:
            cmd.append('-a')
        else:
            if enum_users:
                cmd.append('-U')
            if enum_shares:
                cmd.append('-S')
            if enum_groups:
                cmd.append('-G')
            if password_policy:
                cmd.append('-P')

        # RID range
        cmd.extend(['-r', rid_range])

        # Target
        cmd.append(target)

        logger.info(f"Running enum4linux: {' '.join(cmd)}")

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
                "tool": "enum4linux",
                "target": target,
                **parsed,
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "enum4linux timed out", "success": False}
        except Exception as e:
            logger.error(f"enum4linux error: {e}")
            return {"error": str(e), "success": False}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse enum4linux output"""
        results = {
            "os_info": {},
            "users": [],
            "groups": [],
            "shares": [],
            "password_policy": {},
            "domain_info": {}
        }

        lines = output.split('\n')
        section = None

        for line in lines:
            line = line.strip()

            # Detect sections
            if 'OS information' in line:
                section = 'os'
            elif 'Users on' in line or 'user:[' in line.lower():
                section = 'users'
            elif 'Group' in line and 'on' in line:
                section = 'groups'
            elif 'Share Enumeration' in line:
                section = 'shares'
            elif 'Password Policy' in line:
                section = 'policy'
            elif 'Domain' in line and 'SID' in line:
                section = 'domain'

            # Parse content based on section
            if section == 'users':
                # user:[username] rid:[0x...]
                match = re.search(r'user:\[([^\]]+)\]', line)
                if match:
                    results["users"].append(match.group(1))

            elif section == 'groups':
                # group:[groupname] rid:[0x...]
                match = re.search(r'group:\[([^\]]+)\]', line)
                if match:
                    results["groups"].append(match.group(1))

            elif section == 'shares':
                # Share types: Disk, IPC, Printer, etc.
                if 'Disk' in line or 'IPC' in line or 'Printer' in line:
                    parts = line.split()
                    if parts:
                        results["shares"].append({
                            "name": parts[0],
                            "type": parts[1] if len(parts) > 1 else "Unknown"
                        })

            elif section == 'os':
                if 'OS=' in line or 'Server=' in line:
                    if 'OS=' in line:
                        match = re.search(r'OS=\[([^\]]*)\]', line)
                        if match:
                            results["os_info"]["os"] = match.group(1)
                    if 'Server=' in line:
                        match = re.search(r'Server=\[([^\]]*)\]', line)
                        if match:
                            results["os_info"]["server"] = match.group(1)

            elif section == 'policy':
                if 'Minimum password length' in line:
                    match = re.search(r':\s*(\d+)', line)
                    if match:
                        results["password_policy"]["min_length"] = int(match.group(1))
                elif 'Password history length' in line:
                    match = re.search(r':\s*(\d+)', line)
                    if match:
                        results["password_policy"]["history_length"] = int(match.group(1))
                elif 'Maximum password age' in line:
                    match = re.search(r':\s*(.+)', line)
                    if match:
                        results["password_policy"]["max_age"] = match.group(1).strip()
                elif 'Account lockout' in line:
                    match = re.search(r':\s*(.+)', line)
                    if match:
                        results["password_policy"]["lockout"] = match.group(1).strip()

            elif section == 'domain':
                if 'Domain SID' in line:
                    match = re.search(r'S-1-\d+-\d+-\d+-\d+-\d+', line)
                    if match:
                        results["domain_info"]["sid"] = match.group(0)
                if 'Domain Name:' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        results["domain_info"]["name"] = parts[1].strip()

        # Deduplicate
        results["users"] = list(set(results["users"]))
        results["groups"] = list(set(results["groups"]))

        return results
