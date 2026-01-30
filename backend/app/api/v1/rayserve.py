"""
RayServe integration endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.services.rayserve_integration import RayServeIntegration
from app.core.security import require_admin
from app.models.user import User

router = APIRouter()
rayserve = RayServeIntegration()


class ModelDeployRequest(BaseModel):
    model_name: str
    model_path: str
    deployment_config: Dict[str, Any]


class ModelInvokeRequest(BaseModel):
    input_data: Any


@router.post("/deploy")
async def deploy_model(
    request: ModelDeployRequest,
    current_user: User = Depends(require_admin)
):
    """Deploy a custom AI model"""
    result = rayserve.deploy_model(
        request.model_name,
        request.model_path,
        request.deployment_config
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.get("/models")
async def list_models():
    """List deployed models"""
    models = rayserve.list_models()
    return {"models": models, "count": len(models)}


@router.get("/models/{model_name}")
async def get_model_info(model_name: str):
    """Get model information"""
    info = rayserve.get_model_info(model_name)
    if not info:
        raise HTTPException(status_code=404, detail="Model not found")
    return info


@router.post("/models/{model_name}/invoke")
async def invoke_model(model_name: str, request: ModelInvokeRequest):
    """Invoke a deployed model"""
    result = rayserve.invoke_model(model_name, request.input_data)
    if not result:
        raise HTTPException(status_code=500, detail="Model invocation failed")
    return result


@router.post("/endpoints")
async def create_endpoint(
    endpoint_name: str,
    model_name: str,
    current_user: User = Depends(require_admin)
):
    """Create model serving endpoint"""
    result = rayserve.create_serving_endpoint(endpoint_name, model_name)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.put("/models/{model_name}/version")
async def set_model_version(
    model_name: str,
    version: str,
    current_user: User = Depends(require_admin)
):
    """Set model version"""
    success = rayserve.set_model_version(model_name, version)
    if not success:
        raise HTTPException(status_code=500, detail="Version setting failed")
    return {"success": True, "version": version}


@router.post("/routing")
async def configure_routing(
    routing_config: Dict[str, Any],
    current_user: User = Depends(require_admin)
):
    """Configure model routing"""
    success = rayserve.configure_routing(routing_config)
    if not success:
        raise HTTPException(status_code=500, detail="Routing configuration failed")
    return {"success": True}
