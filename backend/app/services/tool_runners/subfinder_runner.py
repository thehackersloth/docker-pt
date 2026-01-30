"""
Subfinder - Subdomain discovery tool runner
Fast passive subdomain enumeration tool
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class SubfinderRunner(BaseToolRunner):
    """Subfinder subdomain discovery runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "subfinder")
        self.output_dir = Path(f"/tmp/subfinder_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Subfinder input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Subfinder

        Config options:
            - all: Use all sources (default: True)
            - sources: Specific sources to use
            - exclude_sources: Sources to exclude
            - recursive: Enable recursive subdomain enumeration
            - timeout: Timeout in minutes (default: 10)
            - threads: Number of threads (default: 10)
            - rate_limit: Rate limit per minute
            - max_enumeration_time: Maximum enumeration time
            - resolver: Custom resolver file
            - config_file: Path to config file with API keys
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid Subfinder input - domain required")

        config = config or {}

        # Handle multiple domains
        if len(targets) > 1:
            return self._run_multiple(targets, config)
        else:
            return self._run_single(targets[0], config)

    def _run_single(self, domain: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Subfinder for a single domain"""
        use_all = config.get('all', True)
        sources = config.get('sources')
        exclude_sources = config.get('exclude_sources')
        recursive = config.get('recursive', False)
        timeout = config.get('timeout', 10)
        threads = config.get('threads', 10)
        rate_limit = config.get('rate_limit')
        resolver = config.get('resolver')
        config_file = config.get('config_file')

        output_file = self.output_dir / f"{domain.replace('.', '_')}.json"

        cmd = ['subfinder']

        # Domain
        cmd.extend(['-d', domain])

        # All sources
        if use_all:
            cmd.append('-all')

        # Specific sources
        if sources:
            cmd.extend(['-sources', sources])

        # Exclude sources
        if exclude_sources:
            cmd.extend(['-exclude-sources', exclude_sources])

        # Recursive
        if recursive:
            cmd.append('-recursive')

        # Timeout
        cmd.extend(['-timeout', str(timeout)])

        # Threads
        cmd.extend(['-t', str(threads)])

        # Rate limit
        if rate_limit:
            cmd.extend(['-rate-limit', str(rate_limit)])

        # Resolver
        if resolver:
            cmd.extend(['-r', resolver])

        # Config file
        if config_file:
            cmd.extend(['-config', config_file])

        # Output
        cmd.extend(['-json', '-o', str(output_file)])

        # Silent mode
        cmd.append('-silent')

        logger.info(f"Running Subfinder: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=timeout * 60 + 60)

            # Parse JSON output
            subdomains = []
            sources_found = set()

            if output_file.exists():
                with open(output_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                host = data.get('host')
                                if host:
                                    subdomains.append(host)
                                source = data.get('source')
                                if source:
                                    sources_found.add(source)
                            except json.JSONDecodeError:
                                # Might be plain text
                                if '.' in line:
                                    subdomains.append(line)

            # Deduplicate
            subdomains = list(set(subdomains))

            return {
                "success": True,
                "domain": domain,
                "subdomains": subdomains,
                "subdomains_count": len(subdomains),
                "sources_used": list(sources_found),
                "output_file": str(output_file),
                "command": ' '.join(cmd)
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Subfinder timed out", "success": False}
        except Exception as e:
            logger.error(f"Subfinder error: {e}")
            return {"error": str(e), "success": False}

    def _run_multiple(self, domains: List[str], config: Dict[str, Any]) -> Dict[str, Any]:
        """Run Subfinder for multiple domains"""
        # Create domains file
        domains_file = self.output_dir / "domains.txt"
        with open(domains_file, 'w') as f:
            f.write('\n'.join(domains))

        output_file = self.output_dir / "all_subdomains.json"
        timeout = config.get('timeout', 30)

        cmd = ['subfinder']
        cmd.extend(['-dL', str(domains_file)])
        cmd.append('-all')
        cmd.extend(['-json', '-o', str(output_file)])
        cmd.append('-silent')

        logger.info(f"Running Subfinder for {len(domains)} domains")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=timeout * 60)

            # Parse output
            results = {}
            for domain in domains:
                results[domain] = []

            if output_file.exists():
                with open(output_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                host = data.get('host', '')
                                # Find which domain this belongs to
                                for domain in domains:
                                    if host.endswith(domain):
                                        results[domain].append(host)
                                        break
                            except json.JSONDecodeError:
                                pass

            # Deduplicate
            for domain in results:
                results[domain] = list(set(results[domain]))

            total = sum(len(subs) for subs in results.values())

            return {
                "success": True,
                "domains": domains,
                "results": results,
                "total_subdomains": total,
                "output_file": str(output_file)
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "Subfinder timed out", "success": False}
        except Exception as e:
            logger.error(f"Subfinder error: {e}")
            return {"error": str(e), "success": False}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Subfinder output"""
        subdomains = []
        for line in output.split('\n'):
            line = line.strip()
            if line and '.' in line and not line.startswith('['):
                subdomains.append(line)
        return {"subdomains": list(set(subdomains))}
