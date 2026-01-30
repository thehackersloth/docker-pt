"""
Nuclei - Fast vulnerability scanner runner
Nuclei is used to send requests across targets based on a template
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class NucleiRunner(BaseToolRunner):
    """Nuclei vulnerability scanner runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "nuclei")
        self.output_dir = Path(f"/tmp/nuclei_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.process = None

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Nuclei input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Nuclei scan

        Config options:
            - templates: Specific template(s) or directory
            - severity: Filter by severity (critical,high,medium,low,info)
            - tags: Filter templates by tags
            - exclude_tags: Exclude templates by tags
            - rate_limit: Rate limit (requests per second)
            - concurrency: Number of concurrent templates (default: 25)
            - bulk_size: Number of hosts analyzed in parallel (default: 25)
            - timeout: Timeout for each request (default: 10)
            - retries: Number of retries (default: 1)
            - automatic_scan: Use automatic web scan (default: False)
            - new_templates: Only run new templates
            - headless: Enable headless browser templates
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid Nuclei input - targets required")

        config = config or {}
        templates = config.get('templates')
        severity = config.get('severity')
        tags = config.get('tags')
        exclude_tags = config.get('exclude_tags')
        rate_limit = config.get('rate_limit', 150)
        concurrency = config.get('concurrency', 25)
        bulk_size = config.get('bulk_size', 25)
        timeout = config.get('timeout', 10)
        retries = config.get('retries', 1)
        automatic_scan = config.get('automatic_scan', False)
        new_templates = config.get('new_templates', False)
        headless = config.get('headless', False)

        # Create targets file
        targets_file = self.output_dir / "targets.txt"
        with open(targets_file, 'w') as f:
            f.write('\n'.join(targets))

        output_file = self.output_dir / "results.json"

        cmd = ['nuclei']

        # Targets
        cmd.extend(['-l', str(targets_file)])

        # Output
        cmd.extend(['-jsonl', '-o', str(output_file)])

        # Templates
        if templates:
            if isinstance(templates, list):
                for t in templates:
                    cmd.extend(['-t', t])
            else:
                cmd.extend(['-t', templates])

        # Severity filter
        if severity:
            cmd.extend(['-severity', severity])

        # Tags
        if tags:
            cmd.extend(['-tags', tags])

        # Exclude tags
        if exclude_tags:
            cmd.extend(['-exclude-tags', exclude_tags])

        # Rate limiting
        cmd.extend(['-rate-limit', str(rate_limit)])

        # Concurrency
        cmd.extend(['-concurrency', str(concurrency)])
        cmd.extend(['-bulk-size', str(bulk_size)])

        # Timeout and retries
        cmd.extend(['-timeout', str(timeout)])
        cmd.extend(['-retries', str(retries)])

        # Automatic scan
        if automatic_scan:
            cmd.append('-automatic-scan')

        # New templates only
        if new_templates:
            cmd.append('-new-templates')

        # Headless
        if headless:
            cmd.append('-headless')

        # Silent mode for cleaner output
        cmd.append('-silent')

        logger.info(f"Running Nuclei: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self.process.communicate(timeout=3600)  # 1 hour timeout

            # Parse JSON lines output
            findings = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                findings.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            # Categorize findings by severity
            severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0,
                "unknown": 0
            }

            for finding in findings:
                sev = finding.get('info', {}).get('severity', 'unknown').lower()
                if sev in severity_counts:
                    severity_counts[sev] += 1
                else:
                    severity_counts['unknown'] += 1

            return {
                "success": True,
                "targets": targets,
                "findings": findings,
                "findings_count": len(findings),
                "severity_counts": severity_counts,
                "output_file": str(output_file),
                "command": ' '.join(cmd)
            }

        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
            return {"error": "Nuclei execution timed out", "success": False}
        except Exception as e:
            logger.error(f"Nuclei execution error: {e}")
            return {"error": str(e), "success": False}

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Nuclei output"""
        findings = []
        for line in output.split('\n'):
            line = line.strip()
            if line:
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return {"findings": findings}

    def update_templates(self) -> Dict[str, Any]:
        """Update Nuclei templates"""
        try:
            cmd = ['nuclei', '-update-templates']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate()

            return {
                "success": process.returncode == 0,
                "output": stdout,
                "error": stderr if process.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_progress(self) -> int:
        """Get scan progress"""
        return 0

    def cleanup(self):
        """Cleanup Nuclei process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
