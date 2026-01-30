"""
OWASP ZAP (Zed Attack Proxy) runner
ZAP is an open-source web application security scanner
"""

import subprocess
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class ZAPRunner(BaseToolRunner):
    """OWASP ZAP web security scanner runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "zap")
        self.output_dir = Path(f"/tmp/zap_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.zap_path = "/usr/share/zaproxy/zap.sh"
        self.api_key = None
        self.zap_port = 8090
        self.process = None

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate ZAP input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run ZAP scan

        Config options:
            - scan_type: baseline, full, api (default: baseline)
            - ajax_spider: Enable AJAX spider (default: False)
            - active_scan: Enable active scanning (default: True for full)
            - context_file: ZAP context file
            - report_format: html, xml, json, md (default: json)
            - api_definition: OpenAPI/Swagger definition URL
            - auth_config: Authentication configuration
            - minutes: Maximum scan duration in minutes
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid ZAP input - targets required")

        config = config or {}
        url = targets[0] if targets else config.get('url')
        scan_type = config.get('scan_type', 'baseline')
        ajax_spider = config.get('ajax_spider', False)
        report_format = config.get('report_format', 'json')
        api_definition = config.get('api_definition')
        minutes = config.get('minutes', 10)

        # Determine which script to use
        if scan_type == 'baseline':
            return self._run_baseline_scan(url, config)
        elif scan_type == 'full':
            return self._run_full_scan(url, config)
        elif scan_type == 'api':
            return self._run_api_scan(url, api_definition, config)
        else:
            return self._run_baseline_scan(url, config)

    def _run_baseline_scan(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run ZAP baseline scan (passive only)"""
        report_file = self.output_dir / f"zap_baseline_{self.scan_id}.json"
        minutes = config.get('minutes', 5)

        cmd = [
            'zap-baseline.py',
            '-t', url,
            '-J', str(report_file),
            '-m', str(minutes),
            '-I'  # Don't fail on warnings
        ]

        # AJAX spider
        if config.get('ajax_spider'):
            cmd.append('-j')

        logger.info(f"Running ZAP baseline scan: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self.process.communicate(timeout=minutes * 60 + 300)

            # Parse report
            findings = []
            if report_file.exists():
                with open(report_file, 'r') as f:
                    try:
                        report_data = json.load(f)
                        findings = self._parse_zap_json(report_data)
                    except json.JSONDecodeError:
                        pass

            return {
                "success": True,
                "scan_type": "baseline",
                "url": url,
                "findings": findings,
                "findings_count": len(findings),
                "report_file": str(report_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
            return {"error": "ZAP baseline scan timed out", "success": False}
        except Exception as e:
            logger.error(f"ZAP baseline scan error: {e}")
            return {"error": str(e), "success": False}

    def _run_full_scan(self, url: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run ZAP full scan (passive + active)"""
        report_file = self.output_dir / f"zap_full_{self.scan_id}.json"
        minutes = config.get('minutes', 60)

        cmd = [
            'zap-full-scan.py',
            '-t', url,
            '-J', str(report_file),
            '-m', str(minutes),
            '-I'
        ]

        # AJAX spider
        if config.get('ajax_spider'):
            cmd.append('-j')

        logger.info(f"Running ZAP full scan: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self.process.communicate(timeout=minutes * 60 + 600)

            # Parse report
            findings = []
            if report_file.exists():
                with open(report_file, 'r') as f:
                    try:
                        report_data = json.load(f)
                        findings = self._parse_zap_json(report_data)
                    except json.JSONDecodeError:
                        pass

            return {
                "success": True,
                "scan_type": "full",
                "url": url,
                "findings": findings,
                "findings_count": len(findings),
                "report_file": str(report_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
            return {"error": "ZAP full scan timed out", "success": False}
        except Exception as e:
            logger.error(f"ZAP full scan error: {e}")
            return {"error": str(e), "success": False}

    def _run_api_scan(self, url: str, api_definition: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run ZAP API scan"""
        if not api_definition:
            return {"error": "API definition URL required for API scan", "success": False}

        report_file = self.output_dir / f"zap_api_{self.scan_id}.json"
        minutes = config.get('minutes', 30)

        cmd = [
            'zap-api-scan.py',
            '-t', api_definition,
            '-f', 'openapi',
            '-J', str(report_file),
            '-I'
        ]

        logger.info(f"Running ZAP API scan: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self.process.communicate(timeout=minutes * 60 + 300)

            # Parse report
            findings = []
            if report_file.exists():
                with open(report_file, 'r') as f:
                    try:
                        report_data = json.load(f)
                        findings = self._parse_zap_json(report_data)
                    except json.JSONDecodeError:
                        pass

            return {
                "success": True,
                "scan_type": "api",
                "url": url,
                "api_definition": api_definition,
                "findings": findings,
                "findings_count": len(findings),
                "report_file": str(report_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
            return {"error": "ZAP API scan timed out", "success": False}
        except Exception as e:
            logger.error(f"ZAP API scan error: {e}")
            return {"error": str(e), "success": False}

    def _parse_zap_json(self, report_data: Dict) -> List[Dict]:
        """Parse ZAP JSON report format"""
        findings = []

        # Handle both traditional and new ZAP JSON formats
        if 'site' in report_data:
            for site in report_data.get('site', []):
                for alert in site.get('alerts', []):
                    finding = {
                        "name": alert.get('name'),
                        "risk": alert.get('riskdesc', '').split()[0] if alert.get('riskdesc') else 'Unknown',
                        "confidence": alert.get('confidence'),
                        "description": alert.get('desc'),
                        "solution": alert.get('solution'),
                        "reference": alert.get('reference'),
                        "cweid": alert.get('cweid'),
                        "wascid": alert.get('wascid'),
                        "instances": []
                    }

                    for instance in alert.get('instances', []):
                        finding["instances"].append({
                            "uri": instance.get('uri'),
                            "method": instance.get('method'),
                            "param": instance.get('param'),
                            "evidence": instance.get('evidence')
                        })

                    findings.append(finding)

        return findings

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse ZAP output"""
        return {"raw_output": output}

    def get_progress(self) -> int:
        """Get scan progress"""
        return 0

    def cleanup(self):
        """Cleanup ZAP process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
