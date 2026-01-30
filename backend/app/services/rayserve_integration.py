"""
RayServe integration for custom AI models
"""

import logging
import httpx
from typing import Dict, Any, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class RayServeIntegration:
    """RayServe integration for custom AI models"""
    
    def __init__(self):
        self.base_url = settings.RAYSERVE_ENDPOINT
    
    def deploy_model(
        self,
        model_name: str,
        model_path: str,
        model_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deploy a custom AI model to RayServe"""
        try:
            # RayServe deployment API
            response = httpx.post(
                f"{self.base_url}/deploy",
                json={
                    "name": model_name,
                    "model_path": model_path,
                    "config": model_config
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"RayServe deployment failed: {e}")
            return {"error": str(e), "success": False}
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List deployed models"""
        try:
            response = httpx.get(f"{self.base_url}/models", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to list RayServe models: {e}")
            return []
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a deployed model"""
        try:
            response = httpx.get(f"{self.base_url}/models/{model_name}", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get model info: {e}")
            return None
    
    def invoke_model(self, model_name: str, input_data: Any) -> Optional[Any]:
        """Invoke a deployed model"""
        try:
            response = httpx.post(
                f"{self.base_url}/models/{model_name}/invoke",
                json={"input": input_data},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Model invocation failed: {e}")
            return None
    
    def create_serving_endpoint(self, endpoint_name: str, model_name: str) -> Dict[str, Any]:
        """Create a model serving endpoint"""
        try:
            response = httpx.post(
                f"{self.base_url}/endpoints",
                json={
                    "name": endpoint_name,
                    "model": model_name
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Endpoint creation failed: {e}")
            return {"error": str(e), "success": False}
    
    def set_model_version(self, model_name: str, version: str) -> bool:
        """Set model version"""
        try:
            response = httpx.put(
                f"{self.base_url}/models/{model_name}/version",
                json={"version": version},
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Version setting failed: {e}")
            return False
    
    def configure_routing(self, routing_config: Dict[str, Any]) -> bool:
        """Configure model routing"""
        try:
            response = httpx.post(
                f"{self.base_url}/routing",
                json=routing_config,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Routing configuration failed: {e}")
            return False
