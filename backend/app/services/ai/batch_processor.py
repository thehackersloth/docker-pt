"""
AI batch processing for efficiency
"""

import logging
from typing import List, Dict, Any
from app.services.ai_service import AIService
import asyncio

logger = logging.getLogger(__name__)


class AIBatchProcessor:
    """Batch process AI requests for efficiency"""
    
    def __init__(self):
        self.ai_service = AIService()
    
    def process_batch(
        self,
        prompts: List[str],
        batch_size: int = 10,
        provider: str = None
    ) -> List[Dict[str, Any]]:
        """Process multiple prompts in batches"""
        results = []
        
        for i in range(0, len(prompts), batch_size):
            batch = prompts[i:i + batch_size]
            batch_results = self._process_batch_sync(batch, provider)
            results.extend(batch_results)
        
        return results
    
    def _process_batch_sync(
        self,
        prompts: List[str],
        provider: str = None
    ) -> List[Dict[str, Any]]:
        """Process a batch of prompts synchronously"""
        results = []
        
        for prompt in prompts:
            try:
                result = self.ai_service.generate_text(prompt, provider=provider)
                results.append({
                    "success": result is not None,
                    "result": result,
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt
                })
            except Exception as e:
                logger.error(f"Batch processing failed for prompt: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt
                })
        
        return results
    
    async def process_batch_async(
        self,
        prompts: List[str],
        batch_size: int = 10,
        provider: str = None
    ) -> List[Dict[str, Any]]:
        """Process multiple prompts asynchronously"""
        tasks = []
        
        for prompt in prompts:
            task = self._process_single_async(prompt, provider)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            {
                "success": not isinstance(r, Exception) and r is not None,
                "result": r if not isinstance(r, Exception) else None,
                "error": str(r) if isinstance(r, Exception) else None
            }
            for r in results
        ]
    
    async def _process_single_async(self, prompt: str, provider: str = None):
        """Process a single prompt asynchronously"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.ai_service.generate_text,
            prompt,
            provider
        )
        return result
