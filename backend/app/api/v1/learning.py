"""
Continuous learning endpoints
"""

from fastapi import APIRouter, Depends
from typing import List, Dict, Any
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.continuous_learning import ContinuousLearningService

router = APIRouter()
learning_service = ContinuousLearningService()


@router.get("/techniques")
async def get_learned_techniques(
    current_user: User = Depends(get_current_user)
):
    """Get learned techniques"""
    techniques = learning_service.get_learned_techniques()
    return {"techniques": techniques}


@router.get("/tools")
async def get_learned_tools(
    current_user: User = Depends(get_current_user)
):
    """Get learned tools"""
    tools = learning_service.get_learned_tools()
    return {"tools": tools}


@router.get("/workflows")
async def get_learned_workflows(
    current_user: User = Depends(get_current_user)
):
    """Get learned workflows"""
    workflows = learning_service.get_learned_workflows()
    return {"workflows": workflows}


@router.get("/recommendations")
async def get_recommendations(
    context: str,
    current_user: User = Depends(get_current_user)
):
    """Get recommendations based on learned knowledge"""
    recommendations = learning_service.get_recommendations(context)
    return {"recommendations": recommendations}


@router.post("/scan/{scan_id}/learn")
async def learn_from_scan(
    scan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Learn from scan results"""
    result = learning_service.learn_from_scan_results(scan_id)
    return result


@router.get("/knowledge-base")
async def get_knowledge_base_summary(
    current_user: User = Depends(get_current_user)
):
    """Get knowledge base summary"""
    return {
        "techniques_count": len(learning_service.knowledge_base.get("techniques", {})),
        "tools_count": len(learning_service.knowledge_base.get("tools", {})),
        "workflows_count": len(learning_service.knowledge_base.get("workflows", {})),
        "patterns_count": len(learning_service.knowledge_base.get("patterns", {})),
        "last_updated": learning_service.knowledge_base.get("last_updated")
    }
