"""
theHarvester - OSINT tool runner
Gathers emails, names, subdomains, IPs, and URLs using multiple public data sources
"""

import subprocess
import json
import xml.etree.ElementTree as ET
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class TheHarvesterRunner(BaseToolRunner):
    """theHarvester OSINT tool runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "theharvester")
        self.output_dir = Path(f"/tmp/theharvester_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate theHarvester input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run theHarvester

        Config options:
            - sources: Data sources to search (default: all)
                Available: anubis, baidu, bevigil, binaryedge, bing, bingapi,
                bufferoverun, censys, certspotter, crtsh, dnsdumpster,
                duckduckgo, fullhunt, github-code, hackertarget, hunter,
                intelx, netlas, onyphe, otx, pentesttools, projectdiscovery,
                rapiddns, rocketreach, securityTrails, shodan, sitedossier,
                sublist3r, threatcrowd, threatminer, urlscan, virustotal,
                yahoo, zoomeye
            - limit: Limit the number of results (default: 500)
            - start: Start with result number (default: 0)
            - dns_lookup: Perform DNS lookup (default: True)
            - dns_brute: Perform DNS brute force (default: False)
            - virtual_host: Verify virtual hosts (default: False)
            - screenshots: Take screenshots of subdomains (default: False)
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid theHarvester input - domain required")

        config = config or {}
        domain = targets[0]
        sources = config.get('sources', 'anubis,baidu,bing,certspotter,crtsh,dnsdumpster,duckduckgo,hackertarget,otx,rapiddns,sublist3r,threatminer,urlscan,yahoo')
        limit = config.get('limit', 500)
        start = config.get('start', 0)
        dns_lookup = config.get('dns_lookup', True)
        dns_brute = config.get('dns_brute', False)
        virtual_host = config.get('virtual_host', False)
        screenshots = config.get('screenshots', False)

        output_file = self.output_dir / f"results_{domain.replace('.', '_')}"

        cmd = ['theHarvester']

        # Domain
        cmd.extend(['-d', domain])

        # Sources
        cmd.extend(['-b', sources])

        # Limit
        cmd.extend(['-l', str(limit)])

        # Start
        if start > 0:
            cmd.extend(['-S', str(start)])

        # DNS lookup
        if dns_lookup:
            cmd.append('-n')

        # DNS brute force
        if dns_brute:
            cmd.append('-c')

        # Virtual host
        if virtual_host:
            cmd.append('-v')

        # Screenshots
        if screenshots:
            cmd.append('-r')

        # Output files (XML and JSON)
        cmd.extend(['-f', str(output_file)])

        logger.info(f"Running theHarvester: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=1800)  # 30 min timeout

            # Parse results from output files
            results = self._parse_results(output_file)

            return {
                "success": True,
                "domain": domain,
                "sources": sources,
                "results": results,
                "emails_count": len(results.get('emails', [])),
                "hosts_count": len(results.get('hosts', [])),
                "subdomains_count": len(results.get('subdomains', [])),
                "ips_count": len(results.get('ips', [])),
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "theHarvester execution timed out", "success": False}
        except Exception as e:
            logger.error(f"theHarvester execution error: {e}")
            return {"error": str(e), "success": False}

    def _parse_results(self, output_file: Path) -> Dict[str, Any]:
        """Parse theHarvester output files"""
        results = {
            "emails": [],
            "hosts": [],
            "subdomains": [],
            "ips": [],
            "urls": [],
            "asns": [],
            "interesting_urls": []
        }

        # Try JSON output first
        json_file = Path(f"{output_file}.json")
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)

                results["emails"] = data.get('emails', [])
                results["hosts"] = data.get('hosts', [])
                results["ips"] = data.get('ips', [])
                results["asns"] = data.get('asns', [])
                results["interesting_urls"] = data.get('interesting_urls', [])

                # Extract subdomains from hosts
                for host in results["hosts"]:
                    if isinstance(host, str) and '.' in host:
                        results["subdomains"].append(host.split(':')[0])
                    elif isinstance(host, dict):
                        hostname = host.get('host', host.get('hostname', ''))
                        if hostname:
                            results["subdomains"].append(hostname.split(':')[0])

                return results
            except json.JSONDecodeError:
                pass

        # Try XML output
        xml_file = Path(f"{output_file}.xml")
        if xml_file.exists():
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()

                for email in root.findall('.//email'):
                    if email.text:
                        results["emails"].append(email.text)

                for host in root.findall('.//host'):
                    if host.text:
                        results["hosts"].append(host.text)
                        results["subdomains"].append(host.text.split(':')[0])

                for ip in root.findall('.//ip'):
                    if ip.text:
                        results["ips"].append(ip.text)

            except ET.ParseError:
                pass

        # Deduplicate
        for key in results:
            results[key] = list(set(results[key]))

        return results

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse theHarvester stdout output"""
        results = {
            "emails": [],
            "hosts": [],
            "ips": []
        }

        section = None
        for line in output.split('\n'):
            line = line.strip()

            if '[*] Emails found:' in line:
                section = 'emails'
            elif '[*] Hosts found:' in line:
                section = 'hosts'
            elif '[*] IPs found:' in line:
                section = 'ips'
            elif line.startswith('[*]'):
                section = None
            elif line and section:
                if section == 'emails' and '@' in line:
                    results["emails"].append(line)
                elif section == 'hosts':
                    results["hosts"].append(line)
                elif section == 'ips':
                    results["ips"].append(line)

        return results
