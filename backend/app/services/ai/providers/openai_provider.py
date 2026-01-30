"""
OpenAI provider (⚠️ Public API)
"""

from openai import OpenAI
from typing import Optional
from app.core.config import settings
from app.services.ai.providers.base_provider import BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """OpenAI cloud AI provider"""
    
    def __init__(self):
        super().__init__("openai")
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not configured")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.default_model = "gpt-4-turbo"
    
    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        try:
            self.client.models.list()
            return True
        except Exception:
            return False
    
    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using OpenAI"""
        model = model or self.default_model
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a security expert helping with penetration testing."},
                    {"role": "user", "content": prompt}
                ],
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return None
