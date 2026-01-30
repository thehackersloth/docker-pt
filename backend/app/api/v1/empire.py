"""
Empire/Starkiller API endpoints
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.tool_runners.empire_runner import EmpireRunner

router = APIRouter()


class EmpireStagerRequest(BaseModel):
    stager_type: str = "multi/launcher"
    listener: Optional[str] = None
    output_path: Optional[str] = None


class EmpireListenerRequest(BaseModel):
    operation: str  # start, stop, list
    listener_type: Optional[str] = "http"
    host: Optional[str] = "0.0.0.0"
    port: Optional[int] = 8080
    listener_id: Optional[str] = None


class EmpireModuleRequest(BaseModel):
    module: str
    agent: str
    options: Optional[Dict[str, Any]] = None


@router.post("/stager/generate")
async def generate_stager(request: EmpireStagerRequest, scan_id: Optional[str] = None):
    """Generate Empire stager"""
    try:
        runner = EmpireRunner(scan_id or "manual")
        results = runner._generate_stager({
            "stager_type": request.stager_type,
            "listener": request.listener,
            "output_path": request.output_path,
        })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/listener")
async def manage_listener(request: EmpireListenerRequest):
    """Manage Empire listener"""
    try:
        runner = EmpireRunner("listener")
        results = runner._manage_listener({
            "operation": request.operation,
            "listener_type": request.listener_type,
            "host": request.host,
            "port": request.port,
            "listener_id": request.listener_id,
        })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/module/execute")
async def execute_module(request: EmpireModuleRequest):
    """Execute Empire post-exploitation module"""
    try:
        runner = EmpireRunner("module")
        results = runner._execute_module({
            "module": request.module,
            "agent": request.agent,
            "options": request.options or {},
        })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
