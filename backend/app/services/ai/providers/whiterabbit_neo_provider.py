"""
WhiteRabbit Neo AI provider
"""

import httpx
from typing import Optional
from app.core.config import settings
from app.services.ai.providers.base_provider import BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class WhiteRabbitNeoProvider(BaseAIProvider):
    """WhiteRabbit Neo local AI provider"""
    
    def __init__(self):
        super().__init__("whiterabbit_neo")
        self.base_url = settings.WHITERABBIT_NEO_BASE_URL
        self.default_model = settings.WHITERABBIT_NEO_MODEL
    
    def is_available(self) -> bool:
        """Check if WhiteRabbit Neo is available"""
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using WhiteRabbit Neo"""
        model = model or self.default_model
        
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                },
                timeout=120  # Longer timeout for local models
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response") or data.get("text")
        except Exception as e:
            logger.error(f"WhiteRabbit Neo generation failed: {e}")
            return None
