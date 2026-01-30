"""
GitHub Copilot API provider (⚠️ Public API)
"""

import httpx
from typing import Optional
from app.core.config import settings
from app.services.ai.providers.base_provider import BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class GitHubCopilotProvider(BaseAIProvider):
    """GitHub Copilot cloud AI provider"""
    
    def __init__(self):
        super().__init__("github_copilot")
        if not settings.GITHUB_COPILOT_KEY:
            raise ValueError("GitHub Copilot API key not configured")
        self.api_key = settings.GITHUB_COPILOT_KEY
        self.base_url = "https://api.githubcopilot.com"
    
    def is_available(self) -> bool:
        """Check if GitHub Copilot is available"""
        try:
            response = httpx.get(
                f"{self.base_url}/health",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using GitHub Copilot"""
        try:
            response = httpx.post(
                f"{self.base_url}/v1/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "max_tokens": kwargs.get("max_tokens", 1000),
                    "temperature": kwargs.get("temperature", 0.7),
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("text", "")
        except Exception as e:
            logger.error(f"GitHub Copilot generation failed: {e}")
            return None
