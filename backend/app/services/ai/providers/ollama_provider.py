"""
Ollama AI provider
"""

import httpx
from typing import Optional
from app.core.config import settings
from app.services.ai.providers.base_provider import BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class OllamaProvider(BaseAIProvider):
    """Ollama local AI provider"""
    
    def __init__(self):
        super().__init__("ollama")
        self.base_url = settings.OLLAMA_BASE_URL
        self.default_model = settings.OLLAMA_MODEL
    
    def is_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using Ollama"""
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
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return None
