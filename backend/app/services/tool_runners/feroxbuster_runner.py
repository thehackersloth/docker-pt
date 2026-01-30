"""
Feroxbuster - Fast, recursive content discovery tool runner
Written in Rust for high performance
"""

import subprocess
import json
import logging
from typing import Dict, List, Any
from pathlib import Path
from app.services.tool_runners.base_runner import BaseToolRunner

logger = logging.getLogger(__name__)


class FeroxbusterRunner(BaseToolRunner):
    """Feroxbuster content discovery runner"""

    def __init__(self, scan_id: str):
        super().__init__(scan_id, "feroxbuster")
        self.output_dir = Path(f"/tmp/feroxbuster_{scan_id}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.process = None

    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate Feroxbuster input"""
        if not targets:
            return False
        return True

    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run Feroxbuster

        Config options:
            - wordlist: Wordlist to use (default: /usr/share/wordlists/dirb/common.txt)
            - extensions: File extensions to search for (e.g., php,html,js)
            - threads: Number of concurrent threads (default: 50)
            - depth: Maximum recursion depth (default: 4)
            - timeout: Request timeout in seconds (default: 7)
            - status_codes: Status codes to include (default: 200,204,301,302,307,308,401,403,405)
            - filter_status: Status codes to filter out
            - filter_size: Response size to filter
            - filter_words: Word count to filter
            - filter_lines: Line count to filter
            - headers: Custom headers dict
            - cookies: Cookies to include
            - user_agent: Custom user agent
            - proxy: Proxy URL
            - insecure: Disable certificate verification
            - follow_redirects: Follow redirects (default: True)
            - extract_links: Extract links from responses (default: True)
            - auto_tune: Automatically tune request rate
            - rate_limit: Requests per second limit
        """
        if not self.validate_input(targets, config):
            raise ValueError("Invalid Feroxbuster input - URL required")

        config = config or {}
        url = targets[0] if targets else config.get('url')
        wordlist = config.get('wordlist', '/usr/share/wordlists/dirb/common.txt')
        extensions = config.get('extensions')
        threads = config.get('threads', 50)
        depth = config.get('depth', 4)
        timeout = config.get('timeout', 7)
        status_codes = config.get('status_codes', '200,204,301,302,307,308,401,403,405')
        filter_status = config.get('filter_status')
        filter_size = config.get('filter_size')
        filter_words = config.get('filter_words')
        filter_lines = config.get('filter_lines')
        headers = config.get('headers', {})
        cookies = config.get('cookies')
        user_agent = config.get('user_agent')
        proxy = config.get('proxy')
        insecure = config.get('insecure', False)
        follow_redirects = config.get('follow_redirects', True)
        extract_links = config.get('extract_links', True)
        auto_tune = config.get('auto_tune', False)
        rate_limit = config.get('rate_limit')

        output_file = self.output_dir / f"results_{self.scan_id}.json"

        cmd = ['feroxbuster']

        # URL
        cmd.extend(['-u', url])

        # Wordlist
        cmd.extend(['-w', wordlist])

        # Extensions
        if extensions:
            cmd.extend(['-x', extensions])

        # Threads
        cmd.extend(['-t', str(threads)])

        # Depth
        cmd.extend(['-d', str(depth)])

        # Timeout
        cmd.extend(['--timeout', str(timeout)])

        # Status codes
        if status_codes:
            cmd.extend(['-s', status_codes])

        # Filters
        if filter_status:
            cmd.extend(['-C', filter_status])
        if filter_size:
            cmd.extend(['-S', str(filter_size)])
        if filter_words:
            cmd.extend(['-W', str(filter_words)])
        if filter_lines:
            cmd.extend(['-N', str(filter_lines)])

        # Headers
        for key, value in headers.items():
            cmd.extend(['-H', f'{key}: {value}'])

        # Cookies
        if cookies:
            cmd.extend(['-b', cookies])

        # User agent
        if user_agent:
            cmd.extend(['-a', user_agent])

        # Proxy
        if proxy:
            cmd.extend(['-p', proxy])

        # Insecure
        if insecure:
            cmd.append('-k')

        # Follow redirects
        if follow_redirects:
            cmd.append('-r')

        # Extract links
        if extract_links:
            cmd.append('-e')

        # Auto tune
        if auto_tune:
            cmd.append('--auto-tune')

        # Rate limit
        if rate_limit:
            cmd.extend(['-L', str(rate_limit)])

        # Output
        cmd.extend(['-o', str(output_file)])
        cmd.append('--json')

        # Quiet mode for cleaner output
        cmd.append('-q')

        logger.info(f"Running Feroxbuster: {' '.join(cmd)}")

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = self.process.communicate(timeout=3600)

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

            # Categorize results
            categorized = self._categorize_results(results)

            return {
                "success": True,
                "url": url,
                "results": results,
                "results_count": len(results),
                "categorized": categorized,
                "directories_found": len(categorized.get('directories', [])),
                "files_found": len(categorized.get('files', [])),
                "output_file": str(output_file),
                "command": ' '.join(cmd)
            }

        except subprocess.TimeoutExpired:
            if self.process:
                self.process.kill()
            return {"error": "Feroxbuster execution timed out", "success": False}
        except Exception as e:
            logger.error(f"Feroxbuster error: {e}")
            return {"error": str(e), "success": False}

    def _categorize_results(self, results: List[Dict]) -> Dict[str, List]:
        """Categorize discovered resources"""
        categorized = {
            "directories": [],
            "files": [],
            "redirects": [],
            "interesting": []
        }

        interesting_patterns = [
            'admin', 'login', 'upload', 'backup', 'config', 'api', 'debug',
            'console', 'phpmyadmin', 'wp-admin', 'dashboard', '.git', '.env',
            'robots.txt', 'sitemap.xml', '.htaccess', 'web.config'
        ]

        for result in results:
            url = result.get('url', '')
            status = result.get('status', 0)

            # Categorize by type
            if url.endswith('/'):
                categorized["directories"].append(result)
            elif '.' in url.split('/')[-1]:
                categorized["files"].append(result)
            elif status in [301, 302, 307, 308]:
                categorized["redirects"].append(result)
            else:
                categorized["directories"].append(result)

            # Check for interesting paths
            url_lower = url.lower()
            for pattern in interesting_patterns:
                if pattern in url_lower:
                    categorized["interesting"].append(result)
                    break

        return categorized

    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse Feroxbuster output"""
        results = []
        for line in output.split('\n'):
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return {"results": results}

    def get_progress(self) -> int:
        """Get scan progress"""
        return 0

    def cleanup(self):
        """Cleanup Feroxbuster process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
