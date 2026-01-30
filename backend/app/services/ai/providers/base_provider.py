"""
Base AI provider class
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """Base class for all AI providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> Optional[str]:
        """Generate text using AI"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
