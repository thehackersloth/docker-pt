"""
AI cost optimization service
"""

import logging
from typing import Dict, Any, Optional
from app.core.config import settings
from app.services.ai_service import AIService
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class AICostOptimizer:
    """AI cost optimization and tracking"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.usage_stats = defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0})
        self.cache = {}  # Simple cache (use Redis in production)
    
    def get_optimal_provider(self, task_type: str, prompt_length: int) -> Optional[str]:
        """Select optimal AI provider based on task and cost"""
        # If local-only mode, prefer local providers
        if settings.AI_LOCAL_ONLY:
            # Prefer WhiteRabbit Neo for security tasks
            if task_type in ["exploit", "module", "analysis"]:
                if settings.WHITERABBIT_NEO_ENABLED:
                    return "whiterabbit_neo"
            # Fallback to Ollama
            if settings.OLLAMA_ENABLED:
                return "ollama"
            return None
        
        # Cost-based selection for cloud providers
        # Estimate tokens
        estimated_tokens = prompt_length // 4  # Rough estimate
        
        # Cost per 1K tokens (approximate)
        costs = {
            "openai": {"gpt-4-turbo": 0.01, "gpt-3.5-turbo": 0.001},
            "anthropic": {"claude-3-opus": 0.015, "claude-3-sonnet": 0.003},
            "gemini": {"gemini-pro": 0.0005}
        }
        
        # For simple tasks, use cheaper models
        if task_type in ["analysis", "summary"] and estimated_tokens < 1000:
            if settings.GEMINI_ENABLED:
                return "gemini"
            if settings.OPENAI_ENABLED:
                return "openai"  # GPT-3.5 is cheap
        
        # For complex tasks, use better models
        if task_type in ["exploit", "module"]:
            if settings.ANTHROPIC_ENABLED:
                return "anthropic"  # Claude is good for code
            if settings.OPENAI_ENABLED:
                return "openai"
        
        # Default to first available
        return self.ai_service.get_provider()
    
    def track_usage(self, provider: str, tokens: int, cost: float):
        """Track AI usage and costs"""
        today = datetime.now().date()
        key = f"{provider}_{today}"
        self.usage_stats[key]["count"] += 1
        self.usage_stats[key]["tokens"] += tokens
        self.usage_stats[key]["cost"] += cost
    
    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics"""
        stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "by_provider": defaultdict(lambda: {"count": 0, "tokens": 0, "cost": 0.0})
        }
        
        cutoff_date = datetime.now().date() - timedelta(days=days)
        
        for key, data in self.usage_stats.items():
            provider, date_str = key.rsplit("_", 1)
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date >= cutoff_date:
                    stats["total_requests"] += data["count"]
                    stats["total_tokens"] += data["tokens"]
                    stats["total_cost"] += data["cost"]
                    stats["by_provider"][provider]["count"] += data["count"]
                    stats["by_provider"][provider]["tokens"] += data["tokens"]
                    stats["by_provider"][provider]["cost"] += data["cost"]
            except:
                pass
        
        return stats
    
    def get_cached_response(self, prompt_hash: str) -> Optional[str]:
        """Get cached AI response"""
        return self.cache.get(prompt_hash)
    
    def cache_response(self, prompt_hash: str, response: str):
        """Cache AI response"""
        # Simple cache with size limit
        if len(self.cache) > 1000:
            # Remove oldest entries
            keys_to_remove = list(self.cache.keys())[:100]
            for key in keys_to_remove:
                del self.cache[key]
        
        self.cache[prompt_hash] = response
    
    def get_fallback_provider(self, primary_provider: str) -> Optional[str]:
        """Get fallback provider if primary fails"""
        providers = ["whiterabbit_neo", "ollama", "openai", "anthropic", "gemini"]
        
        try:
            current_index = providers.index(primary_provider)
            for provider in providers[current_index + 1:]:
                if provider in self.ai_service.providers:
                    return provider
        except ValueError:
            pass
        
        return None
