"""
Anthropic Claude provider (⚠️ Public API)
"""

from anthropic import Anthropic
from typing import Optional
from app.core.config import settings
from app.services.ai.providers.base_provider import BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude cloud AI provider"""
    
    def __init__(self):
        super().__init__("anthropic")
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("Anthropic API key not configured")
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.default_model = "claude-3-sonnet-20240229"
    
    def is_available(self) -> bool:
        """Check if Anthropic is available"""
        try:
            # Test with a simple message
            self.client.messages.create(
                model=self.default_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False
    
    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using Anthropic Claude"""
        model = model or self.default_model
        
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=kwargs.get('max_tokens', 4096),
                messages=[
                    {"role": "user", "content": prompt}
                ],
                **{k: v for k, v in kwargs.items() if k != 'max_tokens'}
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return None
