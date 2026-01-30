"""
Competitive features endpoints
"""

from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.user import User
from app.services.competitive_features import CompetitiveFeatures
from app.services.enterprise_features import EnterpriseFeatures

router = APIRouter()
competitive = CompetitiveFeatures()
enterprise = EnterpriseFeatures()


@router.get("/advantages")
async def get_competitive_advantages(
    current_user: User = Depends(get_current_user)
):
    """Get competitive advantages"""
    return competitive.get_competitive_advantages()


@router.get("/comparison")
async def get_feature_comparison(
    current_user: User = Depends(get_current_user)
):
    """Compare features with competitors"""
    return competitive.get_feature_comparison()


@router.get("/executive-summary")
async def get_executive_summary(
    current_user: User = Depends(get_current_user)
):
    """Get executive summary dashboard"""
    return enterprise.get_executive_summary()


@router.get("/compliance")
async def get_compliance_report(
    current_user: User = Depends(get_current_user)
):
    """Get compliance report"""
    return enterprise.get_compliance_report()


@router.get("/team-performance")
async def get_team_performance(
    current_user: User = Depends(get_current_user)
):
    """Get team performance metrics"""
    return enterprise.get_team_performance()
