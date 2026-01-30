"""
Amass - In-depth attack surface mapping and asset discovery runner
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class AmassRunner(BaseToolRunner):
    """Amass subdomain enumeration and attack surface mapping runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "amass")
        self.output_dir = Path(f"/tmp/amass_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Amass input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Amass

        Config options:
            - mode: enum, intel, db (default: enum)
            - passive: Passive enumeration only (default: False)
            - active: Active enumeration (default: True)
            - brute: Brute force subdomains (default: False)
            - wordlist: Custom wordlist for brute force
            - config_file: Amass config file path
            - timeout: Timeout in minutes (default: 30)
            - max_dns_queries: Max concurrent DNS queries
            - resolvers: Custom DNS resolvers file
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid Amass input - domain required")

        config = config or {}
        domain = targets[0]
        mode = config.get('mode', 'enum')

        if mode == 'enum':
            return self._run_enum(domain, config)
        elif mode == 'intel':
            return self._run_intel(domain, config)
        elif mode == 'db':
            return self._run_db(domain, config)
        else:
            return self._run_enum(domain, config)

    def _run_enum(self, domain: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Amass enum subcommand"""
        passive = config.get('passive', False)
        active = config.get('active', True)
        brute = config.get('brute', False)
        wordlist = config.get('wordlist')
        config_file = config.get('config_file')
        timeout = config.get('timeout', 30)
        max_dns_queries = config.get('max_dns_queries')
        resolvers = config.get('resolvers')

        output_file = self.output_dir / f"{domain.replace('.', '_')}_enum.json"

        cmd = ['amass', 'enum']

        # Domain
        cmd.extend(['-d', domain])

        # Mode flags
        if passive:
            cmd.append('-passive')
        if active:
            cmd.append('-active')
        if brute:
            cmd.append('-brute')

        # Wordlist
        if wordlist and brute:
            cmd.extend(['-w', wordlist])

        # Config file
        if config_file:
            cmd.extend(['-config', config_file])

        # Timeout
        cmd.extend(['-timeout', str(timeout)])

        # Max DNS queries
        if max_dns_queries:
            cmd.extend(['-max-dns-queries', str(max_dns_queries)])

        # Resolvers
        if resolvers:
            cmd.extend(['-rf', resolvers])

        # Output
        cmd.extend(['-json', str(output_file)])

        logger.info(f"Running Amass enum: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=timeout * 60 + 300)

            # Parse JSON output
            results = self._parse_json_output(output_file)

            return {
                "success": True,
                "mode": "enum",
                "domain": domain,
                "subdomains": results.get('subdomains', []),
                "subdomains_count": len(results.get('subdomains', [])),
                "addresses": results.get('addresses', []),
                "sources": results.get('sources', []),
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Amass enum timed out", "success": False}
        except Exception as e:
            logger.error(f"Amass enum error: {e}")
            return {"error": str(e), "success": False}

    def _run_intel(self, domain: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Amass intel subcommand for discovering root domains"""
        output_file = self.output_dir / f"{domain.replace('.', '_')}_intel.json"
        timeout = config.get('timeout', 15)
        whois = config.get('whois', True)
        org = config.get('org')
        asn = config.get('asn')

        cmd = ['amass', 'intel']

        # Domain or org
        if org:
            cmd.extend(['-org', org])
        elif asn:
            cmd.extend(['-asn', str(asn)])
        else:
            cmd.extend(['-d', domain])

        # Whois
        if whois:
            cmd.append('-whois')

        # Output
        cmd.extend(['-json', str(output_file)])

        logger.info(f"Running Amass intel: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=timeout * 60)

            # Parse output
            results = self._parse_json_output(output_file)

            return {
                "success": True,
                "mode": "intel",
                "domain": domain,
                "results": results,
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Amass intel timed out", "success": False}
        except Exception as e:
            logger.error(f"Amass intel error: {e}")
            return {"error": str(e), "success": False}

    def _run_db(self, domain: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Query the Amass database"""
        cmd = ['amass', 'db', '-show', '-d', domain]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=60)

            # Parse output
            subdomains = []
            for line in stdout.split('\n'):
                line = line.strip()
                if line and domain in line:
                    subdomains.append(line)

            return {
                "success": True,
                "mode": "db",
                "domain": domain,
                "subdomains": subdomains,
                "subdomains_count": len(subdomains),
                "raw_output": stdout
            }

        except Exception as e:
            logger.error(f"Amass db error: {e}")
            return {"error": str(e), "success": False}

    def _parse_json_output(self, output_file: Path) -> Dict[str, Any]:
        """Parse Amass JSON output"""
        results = {
            "subdomains": [],
            "addresses": [],
            "sources": set()
        }

        if not output_file.exists():
            return results

        try:
            with open(output_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        name = data.get('name')
                        if name:
                            results["subdomains"].append(name)

                        for addr in data.get('addresses', []):
                            results["addresses"].append({
                                "ip": addr.get('ip'),
                                "cidr": addr.get('cidr'),
                                "asn": addr.get('asn'),
                                "desc": addr.get('desc')
                            })

                        sources = data.get('sources', [])
                        for source in sources:
                            results["sources"].add(source)
                    except json.JSONDecodeError:
                        continue

            results["sources"] = list(results["sources"])
            results["subdomains"] = list(set(results["subdomains"]))

        except Exception as e:
            logger.error(f"Failed to parse Amass output: {e}")

        return results

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Amass stdout output"""
        subdomains = []
        for line in output.split('\n'):
            line = line.strip()
            if line and not line.startswith('['):
                subdomains.append(line)
        return {"subdomains": subdomains}
