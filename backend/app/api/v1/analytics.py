"""
Analytics endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.analytics import AnalyticsService
from app.services.ai.cost_optimizer import AICostOptimizer

router = APIRouter()
analytics_service = AnalyticsService()
cost_optimizer = AICostOptimizer()


@router.get("/schedules")
async def get_schedule_analytics(days: int = 30):
    """Get schedule execution analytics"""
    return analytics_service.get_schedule_analytics(days)


@router.get("/ai/performance")
async def get_ai_performance(days: int = 30):
    """Get AI model performance metrics"""
    return analytics_service.get_ai_performance_metrics(days)


@router.get("/ai/cost/recommendations")
async def get_cost_recommendations():
    """Get AI cost optimization recommendations"""
    recommendations = analytics_service.get_cost_optimization_recommendations()
    return {
        "recommendations": recommendations,
        "count": len(recommendations)
    }
