"""
Secretsdump - Impacket secretsdump.py runner
Dumps secrets from Windows machines (SAM, LSA, NTDS.dit)
"""

import subprocess
import re
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class SecretsDumpRunner(BaseToolRunner):
    """Secretsdump credential extraction runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "secretsdump")
        self.output_dir = Path(f"/tmp/secretsdump_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate secretsdump input"""
        config = config or {}
        if not targets:
            return False
        if not config.get('username'):
            return False
        if not config.get('password') and not config.get('hash'):
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run secretsdump.py

        Config options:
            - username: Username for authentication (required)
            - password: Password for authentication
            - hash: NTLM hash for pass-the-hash
            - domain: Domain name
            - just_dc: Only dump NTDS.dit (for DCs)
            - just_dc_ntlm: Only dump NTLM hashes from DC
            - just_dc_user: Dump specific user from DC
            - sam: Dump SAM database
            - lsa: Dump LSA secrets
            - ntds: Dump NTDS.dit
            - history: Include password history
            - outputfile: Output file path
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid secretsdump input - target, username, and credentials required")

        config = config or {}
        results = []

        for target in targets:
            result = self._dump_target(target, config)
            results.append(result)

        if len(results) == 1:
            return results[0]

        return {
            "success": any(r.get('success', False) for r in results),
            "targets": targets,
            "results": results
        }

    def _dump_target(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Dump secrets from a single target"""
        username = config.get('username')
        password = config.get('password')
        hash_value = config.get('hash')
        domain = config.get('domain', '')
        just_dc = config.get('just_dc', False)
        just_dc_ntlm = config.get('just_dc_ntlm', False)
        just_dc_user = config.get('just_dc_user')
        sam = config.get('sam', True)
        lsa = config.get('lsa', True)
        ntds = config.get('ntds', False)
        history = config.get('history', False)

        output_file = self.output_dir / f"secretsdump_{target.replace('.', '_')}_{self.scan_id}"

        # Build credentials string
        if domain:
            cred_string = f"{domain}/{username}"
        else:
            cred_string = username

        if hash_value:
            cred_string += f"@{target} -hashes :{hash_value}"
        else:
            cred_string += f":{password}@{target}"

        cmd = ['secretsdump.py', cred_string]

        # Options
        if just_dc:
            cmd.append('-just-dc')
        elif just_dc_ntlm:
            cmd.append('-just-dc-ntlm')
        elif just_dc_user:
            cmd.extend(['-just-dc-user', just_dc_user])
        else:
            if sam:
                cmd.append('-sam')
            if lsa:
                cmd.append('-lsa')
            if ntds:
                cmd.append('-ntds')

        if history:
            cmd.append('-history')

        # Output file
        cmd.extend(['-outputfile', str(output_file)])

        logger.info(f"Running secretsdump on {target}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=600)

            # Parse output files
            secrets = self._parse_output_files(output_file)

            return {
                "success": True,
                "target": target,
                "secrets": secrets,
                "sam_hashes": secrets.get('sam', []),
                "lsa_secrets": secrets.get('lsa', []),
                "ntds_hashes": secrets.get('ntds', []),
                "cached_credentials": secrets.get('cached', []),
                "domain_backup_keys": secrets.get('dpapi', []),
                "output_files": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Secretsdump timed out", "success": False, "target": target}
        except Exception as e:
            logger.error(f"Secretsdump error: {e}")
            return {"error": str(e), "success": False, "target": target}

    def _parse_output_files(self, output_base: Path) -> Dict[str, List]:
        """Parse secretsdump output files"""
        secrets = {
            "sam": [],
            "lsa": [],
            "ntds": [],
            "cached": [],
            "dpapi": []
        }

        # SAM hashes
        sam_file = Path(f"{output_base}.sam")
        if sam_file.exists():
            with open(sam_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        secrets["sam"].append(self._parse_hash_line(line))

        # LSA secrets
        lsa_file = Path(f"{output_base}.lsa")
        if lsa_file.exists():
            with open(lsa_file, 'r') as f:
                current_secret = None
                for line in f:
                    line = line.strip()
                    if line.startswith('[*]') or line.startswith('$'):
                        if current_secret:
                            secrets["lsa"].append(current_secret)
                        current_secret = {"name": line, "value": ""}
                    elif current_secret:
                        current_secret["value"] += line

        # NTDS hashes
        ntds_file = Path(f"{output_base}.ntds")
        if ntds_file.exists():
            with open(ntds_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        secrets["ntds"].append(self._parse_hash_line(line))

        # Cached credentials
        cached_file = Path(f"{output_base}.cached")
        if cached_file.exists():
            with open(cached_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ':' in line:
                        secrets["cached"].append(line)

        return secrets

    def _parse_hash_line(self, line: str) -> Dict[str, str]:
        """Parse a hash line in format user:rid:lmhash:nthash:::"""
        parts = line.split(':')
        if len(parts) >= 4:
            return {
                "username": parts[0],
                "rid": parts[1] if len(parts) > 1 else "",
                "lm_hash": parts[2] if len(parts) > 2 else "",
                "nt_hash": parts[3] if len(parts) > 3 else "",
                "full_line": line
            }
        return {"full_line": line}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse secretsdump stdout output"""
        secrets = {
            "sam": [],
            "lsa": [],
            "ntds": [],
            "cached": []
        }

        section = None
        for line in output.split('\n'):
            line = line.strip()

            if '[*] Dumping SAM' in line:
                section = 'sam'
            elif '[*] Dumping LSA' in line:
                section = 'lsa'
            elif '[*] Dumping NTDS' in line or '[*] Using the DRSUAPI' in line:
                section = 'ntds'
            elif '[*] Dumping cached' in line:
                section = 'cached'
            elif section and ':' in line and not line.startswith('['):
                secrets[section].append(line)

        return secrets
