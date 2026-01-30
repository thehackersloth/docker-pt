"""
Resource monitoring endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.resource_monitor import ResourceMonitor

router = APIRouter()


class SystemStatsResponse(BaseModel):
    timestamp: str
    cpu: dict
    memory: dict
    disk: dict
    network: dict


@router.get("/system")
async def get_system_stats():
    """Get system resource statistics"""
    stats = ResourceMonitor.get_system_stats()
    return stats


@router.get("/health")
async def get_system_health():
    """Get system health status"""
    health = ResourceMonitor.check_health()
    return health


@router.get("/process/{process_name}")
async def get_process_stats(process_name: str):
    """Get stats for a specific process"""
    stats = ResourceMonitor.get_process_stats(process_name)
    return stats
