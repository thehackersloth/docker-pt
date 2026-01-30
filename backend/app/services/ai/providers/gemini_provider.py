"""
Google Gemini provider (⚠️ Public API)
"""

import google.generativeai as genai
from typing import Optional
from app.core.config import settings
from app.services.ai.providers.base_provider import BaseAIProvider
import logging

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini cloud AI provider"""
    
    def __init__(self):
        super().__init__("gemini")
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.default_model = "gemini-pro"
    
    def is_available(self) -> bool:
        """Check if Gemini is available"""
        try:
            model = genai.GenerativeModel(self.default_model)
            model.generate_content("test")
            return True
        except Exception:
            return False
    
    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using Google Gemini"""
        model = model or self.default_model
        
        try:
            genai_model = genai.GenerativeModel(model)
            response = genai_model.generate_content(prompt, **kwargs)
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None
