"""
Claude Code Bridge Provider
Connects to Claude Code running on host machine via HTTP bridge
"""

import requests
from typing import Optional
from app.core.config import settings
from app.services.ai.providers.base_provider import BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class ClaudeCodeBridgeProvider(BaseAIProvider):
    """Provider that connects to Claude Code bridge on host"""

    def __init__(self):
        super().__init__("claude_code_bridge")
        self.bridge_url = settings.CLAUDE_CODE_BRIDGE_URL
        self.timeout = 120  # Claude can take time for complex analysis

    def is_available(self) -> bool:
        """Check if bridge is available"""
        try:
            response = requests.get(
                f"{self.bridge_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text via Claude Code bridge"""
        try:
            response = requests.post(
                f"{self.bridge_url}/generate",
                json={
                    "prompt": prompt,
                    "model": model or "claude-sonnet-4-20250514",
                    "max_tokens": kwargs.get('max_tokens', 4096),
                    "context": kwargs.get('context', 'pentest_analysis')
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('response') or data.get('text')
            else:
                logger.error(f"Bridge returned {response.status_code}: {response.text}")
                return None

        except requests.exceptions.ConnectionError:
            logger.warning("Claude Code bridge not available - is it running on host?")
            return None
        except Exception as e:
            logger.error(f"Claude Code bridge request failed: {e}")
            return None

    def analyze_pentest_results(self, scan_data: dict) -> Optional[dict]:
        """Specialized method for pentest analysis"""
        try:
            response = requests.post(
                f"{self.bridge_url}/analyze/pentest",
                json=scan_data,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.error(f"Pentest analysis request failed: {e}")
            return None

    def suggest_exploits(self, service_info: dict) -> Optional[list]:
        """Get exploit suggestions for a service"""
        try:
            response = requests.post(
                f"{self.bridge_url}/suggest/exploits",
                json=service_info,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json().get('exploits', [])
            return None

        except Exception as e:
            logger.error(f"Exploit suggestion request failed: {e}")
            return None
