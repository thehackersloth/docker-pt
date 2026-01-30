"""
testssl.sh - SSL/TLS testing tool runner
Comprehensive SSL/TLS scanner checking for vulnerabilities and misconfigurations
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class TestSSLRunner(BaseToolRunner):
    """testssl.sh SSL/TLS testing runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "testssl")
        self.output_dir = Path(f"/tmp/testssl_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate testssl input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run testssl.sh

        Config options:
            - full: Run all tests (default: True)
            - protocols: Test SSL/TLS protocols only
            - ciphers: Test ciphers only
            - vulnerabilities: Test vulnerabilities only
            - headers: Check HTTP headers
            - starttls: STARTTLS protocol (smtp, pop3, imap, ftp, xmpp, ldap, etc.)
            - port: Port to scan (default: 443)
            - sneaky: Be less verbose during scan
            - warnings: Show warnings (default: True)
            - quiet: Quiet mode
            - fast: Omit some checks for speed
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid testssl input - target required")

        config = config or {}
        results = []

        for target in targets:
            result = self._scan_target(target, config)
            results.append(result)

        if len(results) == 1:
            return results[0]

        return {
            "success": all(r.get('success') for r in results),
            "targets": targets,
            "results": results
        }

    def _scan_target(self, target: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Scan a single target"""
        full = config.get('full', True)
        protocols = config.get('protocols', False)
        ciphers = config.get('ciphers', False)
        vulnerabilities = config.get('vulnerabilities', False)
        headers = config.get('headers', False)
        starttls = config.get('starttls')
        port = config.get('port', 443)
        sneaky = config.get('sneaky', False)
        quiet = config.get('quiet', False)
        fast = config.get('fast', False)

        # Handle target format
        if ':' not in target:
            target = f"{target}:{port}"

        output_file = self.output_dir / f"{target.replace(':', '_').replace('.', '_')}.json"
        html_file = self.output_dir / f"{target.replace(':', '_').replace('.', '_')}.html"

        cmd = ['testssl.sh']

        # Output formats
        cmd.extend(['--jsonfile', str(output_file)])
        cmd.extend(['--htmlfile', str(html_file)])

        # Scan options
        if full:
            cmd.append('--full')
        else:
            if protocols:
                cmd.append('-p')
            if ciphers:
                cmd.append('-E')
            if vulnerabilities:
                cmd.append('-U')
            if headers:
                cmd.append('-H')

        # STARTTLS
        if starttls:
            cmd.extend(['-t', starttls])

        # Speed/verbosity options
        if sneaky:
            cmd.append('--sneaky')
        if quiet:
            cmd.append('--quiet')
        if fast:
            cmd.append('--fast')

        # Warnings
        cmd.append('--warnings')
        cmd.append('batch')

        # Target
        cmd.append(target)

        logger.info(f"Running testssl.sh: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=600)

            # Parse JSON output
            findings = []
            vulnerabilities_found = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    try:
                        data = json.load(f)
                        findings = data if isinstance(data, list) else data.get('scanResult', [])

                        # Extract vulnerabilities
                        for finding in findings:
                            severity = finding.get('severity', 'INFO')
                            if severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'WARN']:
                                vulnerabilities_found.append({
                                    "id": finding.get('id'),
                                    "severity": severity,
                                    "finding": finding.get('finding'),
                                    "cve": finding.get('cve'),
                                    "cwe": finding.get('cwe')
                                })
                    except json.JSONDecodeError:
                        pass

            # Categorize findings
            categorized = self._categorize_findings(findings)

            return {
                "success": True,
                "target": target,
                "findings": findings,
                "findings_count": len(findings),
                "vulnerabilities": vulnerabilities_found,
                "vulnerabilities_count": len(vulnerabilities_found),
                "categorized": categorized,
                "output_file": str(output_file),
                "html_file": str(html_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "testssl.sh timed out", "success": False, "target": target}
        except Exception as e:
            logger.error(f"testssl.sh error: {e}")
            return {"error": str(e), "success": False, "target": target}

    def _categorize_findings(self, findings: List[Dict]) -> Dict[str, List]:
        """Categorize findings by type"""
        categories = {
            "protocols": [],
            "ciphers": [],
            "vulnerabilities": [],
            "certificate": [],
            "headers": [],
            "other": []
        }

        for finding in findings:
            finding_id = finding.get('id', '')

            if any(x in finding_id.lower() for x in ['sslv', 'tlsv', 'protocol']):
                categories["protocols"].append(finding)
            elif any(x in finding_id.lower() for x in ['cipher', 'rc4', 'cbc', '3des', 'aes']):
                categories["ciphers"].append(finding)
            elif any(x in finding_id.lower() for x in ['cert', 'chain', 'trust', 'ocsp']):
                categories["certificate"].append(finding)
            elif any(x in finding_id.lower() for x in ['header', 'hsts', 'hpkp']):
                categories["headers"].append(finding)
            elif any(x in finding_id.lower() for x in ['heartbleed', 'ccs', 'robot', 'beast', 'poodle', 'sweet32', 'lucky', 'bleichenbacher', 'drown', 'logjam', 'freak', 'crime', 'breach']):
                categories["vulnerabilities"].append(finding)
            else:
                categories["other"].append(finding)

        return categories

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse testssl.sh text output"""
        results = {
            "protocols": {},
            "ciphers": [],
            "vulnerabilities": []
        }

        section = None
        for line in output.split('\n'):
            line = line.strip()

            if 'Testing protocols' in line:
                section = 'protocols'
            elif 'Testing ciphers' in line:
                section = 'ciphers'
            elif 'Testing vulnerabilities' in line:
                section = 'vulnerabilities'

            if section == 'vulnerabilities':
                if 'VULNERABLE' in line.upper():
                    results["vulnerabilities"].append(line)

        return results
