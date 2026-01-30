"""
Metasploit Framework API endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.tool_runners.metasploit_runner import MetasploitRunner
from app.core.security import get_current_user, require_admin
from app.models.user import User

router = APIRouter()


class MetasploitExecuteRequest(BaseModel):
    module: str
    targets: List[str]
    payload: Optional[str] = None
    lhost: str = "0.0.0.0"
    lport: int = 4444
    options: Optional[Dict[str, Any]] = None


class MetasploitPayloadRequest(BaseModel):
    payload_type: str
    lhost: str
    lport: int
    options: Optional[Dict[str, Any]] = None


@router.post("/execute")
async def execute_metasploit(request: MetasploitExecuteRequest, scan_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Execute a Metasploit module"""
    try:
        runner = MetasploitRunner(scan_id or "manual")
        results = runner.run(
            targets=request.targets,
            config={
                "module": request.module,
                "payload": request.payload,
                "lhost": request.lhost,
                "lport": request.lport,
                "options": request.options or {},
            }
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-payload")
async def generate_payload(request: MetasploitPayloadRequest, current_user: User = Depends(get_current_user)):
    """Generate a Metasploit payload"""
    try:
        runner = MetasploitRunner("payload_gen")
        results = runner.generate_payload(
            payload_type=request.payload_type,
            lhost=request.lhost,
            lport=request.lport,
            **(request.options or {})
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules")
async def list_modules(module_type: str = "exploit", current_user: User = Depends(get_current_user)):
    """List available Metasploit modules"""
    try:
        runner = MetasploitRunner("list")
        modules = runner.list_modules(module_type)
        return {
            "success": True,
            "module_type": module_type,
            "modules": modules,
            "count": len(modules)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/modules/{module_name}")
async def get_module_info(module_name: str, current_user: User = Depends(get_current_user)):
    """Get information about a specific Metasploit module"""
    import re
    # Sanitize module name - only allow valid msf module paths
    if not re.match(r'^[a-zA-Z0-9_/\-\.]+$', module_name):
        raise HTTPException(status_code=400, detail="Invalid module name")

    try:
        import subprocess
        cmd = ['msfconsole', '-q', '-x', f'info {module_name}; exit']
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(timeout=60)

        if process.returncode != 0:
            raise HTTPException(status_code=404, detail="Module not found")

        return {
            "success": True,
            "module": module_name,
            "info": stdout
        }
    except subprocess.TimeoutExpired:
        process.kill()
        raise HTTPException(status_code=504, detail="Module info request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
