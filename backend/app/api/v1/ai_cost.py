"""
AI cost tracking and optimization endpoints
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.services.ai.cost_optimizer import AICostOptimizer

router = APIRouter()
cost_optimizer = AICostOptimizer()


class CostStatsResponse(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost: float
    by_provider: Dict[str, Dict[str, Any]]


@router.get("/stats", response_model=CostStatsResponse)
async def get_cost_stats(days: int = 30):
    """Get AI usage and cost statistics"""
    stats = cost_optimizer.get_usage_stats(days)
    return CostStatsResponse(
        total_requests=stats["total_requests"],
        total_tokens=stats["total_tokens"],
        total_cost=stats["total_cost"],
        by_provider=dict(stats["by_provider"])
    )


@router.get("/optimal-provider")
async def get_optimal_provider(task_type: str, prompt_length: int = 100):
    """Get optimal AI provider for a task"""
    provider = cost_optimizer.get_optimal_provider(task_type, prompt_length)
    return {
        "provider": provider,
        "task_type": task_type,
        "reasoning": f"Selected {provider} for {task_type} task"
    }
