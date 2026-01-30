"""
WhatWeb - Web technology fingerprinting tool runner
Identifies websites including CMS, blogging platforms, analytics packages, JavaScript libraries, and more
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class WhatWebRunner(BaseToolRunner):
    """WhatWeb technology fingerprinting runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "whatweb")
        self.output_dir = Path(f"/tmp/whatweb_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate WhatWeb input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run WhatWeb

        Config options:
            - aggression: Aggression level 1-4 (default: 1)
                1: Stealthy - 1 request per target
                3: Aggressive - multiple requests and follow redirects
                4: Heavy - try all plugins
            - follow_redirects: Follow redirects (default: always)
            - max_redirects: Maximum redirects to follow (default: 10)
            - user_agent: Custom user agent
            - headers: Custom headers dict
            - proxy: Proxy URL
            - cookies: Cookies to send
            - plugins: Specific plugins to run
            - exclude_plugins: Plugins to exclude
            - timeout: Request timeout (default: 15)
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid WhatWeb input - URL required")

        config = config or {}
        aggression = config.get('aggression', 1)
        follow_redirects = config.get('follow_redirects', 'always')
        max_redirects = config.get('max_redirects', 10)
        user_agent = config.get('user_agent')
        headers = config.get('headers', {})
        proxy = config.get('proxy')
        cookies = config.get('cookies')
        plugins = config.get('plugins')
        exclude_plugins = config.get('exclude_plugins')
        timeout = config.get('timeout', 15)

        output_file = self.output_dir / f"results_{self.scan_id}.json"

        cmd = ['whatweb']

        # Aggression level
        cmd.extend(['-a', str(aggression)])

        # Follow redirects
        cmd.extend(['--follow-redirect', follow_redirects])
        cmd.extend(['--max-redirects', str(max_redirects)])

        # User agent
        if user_agent:
            cmd.extend(['-U', user_agent])

        # Headers
        for key, value in headers.items():
            cmd.extend(['-H', f'{key}: {value}'])

        # Proxy
        if proxy:
            cmd.extend(['--proxy', proxy])

        # Cookies
        if cookies:
            cmd.extend(['-c', cookies])

        # Plugins
        if plugins:
            cmd.extend(['-p', plugins])
        if exclude_plugins:
            cmd.extend(['--exclude-plugin', exclude_plugins])

        # Output format
        cmd.extend(['--log-json', str(output_file)])

        # Quiet mode
        cmd.append('-q')

        # Targets
        cmd.extend(targets)

        logger.info(f"Running WhatWeb: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=len(targets) * timeout + 60)

            # Parse JSON output
            results = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                results.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue

            # Process results
            processed = self._process_results(results)

            return {
                "success": True,
                "targets": targets,
                "results": processed,
                "summary": self._create_summary(processed),
                "output_file": str(output_file),
                "raw_output": stdout
            }

        except subprocess.TimeoutExpired:
            process.kill()
            return {"error": "WhatWeb timed out", "success": False}
        except Exception as e:
            logger.error(f"WhatWeb error: {e}")
            return {"error": str(e), "success": False}

    def _process_results(self, results: List[Dict]) -> List[Dict]:
        """Process WhatWeb results into a cleaner format"""
        processed = []

        for result in results:
            target = result.get('target', '')
            http_status = result.get('http_status', 0)
            plugins = result.get('plugins', {})

            entry = {
                "url": target,
                "status": http_status,
                "technologies": [],
                "headers": {},
                "meta_info": {}
            }

            for plugin_name, plugin_data in plugins.items():
                tech = {
                    "name": plugin_name,
                    "versions": [],
                    "details": []
                }

                if isinstance(plugin_data, dict):
                    # Extract version info
                    if 'version' in plugin_data:
                        versions = plugin_data['version']
                        if isinstance(versions, list):
                            tech["versions"] = versions
                        else:
                            tech["versions"] = [versions]

                    # Extract string info
                    if 'string' in plugin_data:
                        strings = plugin_data['string']
                        if isinstance(strings, list):
                            tech["details"] = strings
                        else:
                            tech["details"] = [strings]

                    # Extract headers
                    if plugin_name.lower() in ['httpserver', 'x-powered-by', 'x-aspnet-version']:
                        entry["headers"][plugin_name] = plugin_data

                    # Extract meta info
                    if plugin_name.lower() in ['title', 'metagenerator', 'email']:
                        entry["meta_info"][plugin_name] = plugin_data

                entry["technologies"].append(tech)

            processed.append(entry)

        return processed

    def _create_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Create a summary of technologies found"""
        tech_count = {}
        total_targets = len(results)

        for result in results:
            for tech in result.get('technologies', []):
                name = tech['name']
                if name not in tech_count:
                    tech_count[name] = 0
                tech_count[name] += 1

        # Sort by frequency
        sorted_tech = sorted(tech_count.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_targets": total_targets,
            "technologies_found": len(tech_count),
            "top_technologies": sorted_tech[:20]
        }

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse WhatWeb text output"""
        results = []
        for line in output.split('\n'):
            if line and 'http' in line.lower():
                results.append(line)
        return {"raw_results": results}
