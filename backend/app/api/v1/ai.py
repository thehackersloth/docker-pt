"""
AI-powered features endpoints
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
from app.services.ai_service import AIService
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()
ai_service = AIService()


class AIProviderInfo(BaseModel):
    name: str
    display_name: str
    available: bool
    type: str  # local, cloud, bridge
    description: str


class AIProviderSelectRequest(BaseModel):
    provider: str


@router.get("/providers", response_model=List[AIProviderInfo])
async def list_ai_providers():
    """List all available AI providers"""
    providers = ai_service.list_available_providers()
    return [AIProviderInfo(**p) for p in providers]


@router.get("/providers/active")
async def get_active_provider():
    """Get currently active AI provider"""
    provider = ai_service.get_provider()
    if not provider:
        return {
            "active": False,
            "provider": None,
            "message": "No AI provider available. Start Claude Code bridge or configure API keys."
        }

    return {
        "active": True,
        "provider": provider.name,
        "display_name": ai_service._get_display_name(provider.name),
        "type": ai_service._get_provider_type(provider.name)
    }


@router.post("/providers/select")
async def select_ai_provider(request: AIProviderSelectRequest):
    """Select AI provider to use"""
    success = ai_service.set_preferred_provider(request.provider)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{request.provider}' not available"
        )

    return {
        "success": True,
        "provider": request.provider,
        "message": f"AI provider set to {request.provider}"
    }


@router.get("/providers/detect-claude-code")
async def detect_claude_code():
    """Check if Claude Code is available on host"""
    detected = ai_service._detect_claude_code()
    return {
        "detected": detected,
        "bridge_url": "http://host.docker.internal:9999",
        "instructions": "Run 'python claude_code_bridge.py' on host machine" if not detected else "Claude Code bridge is running!"
    }


class AIGenerateRequest(BaseModel):
    prompt: str
    provider: Optional[str] = None
    model: Optional[str] = None
    task_type: Optional[str] = None  # analysis, report, exploit, module


class AIGenerateResponse(BaseModel):
    success: bool
    result: Optional[str] = None
    provider: str
    model: str
    error: Optional[str] = None


@router.post("/generate-text", response_model=AIGenerateResponse)
async def generate_text(request: AIGenerateRequest, current_user: User = Depends(get_current_user)):
    """Generate text using AI"""
    try:
        provider = ai_service.get_provider(request.provider)
        if not provider:
            raise HTTPException(status_code=503, detail="No AI provider available")
        
        result = provider.generate_text(request.prompt, request.model)
        
        if not result:
            raise HTTPException(status_code=500, detail="AI generation failed")
        
        return AIGenerateResponse(
            success=True,
            result=result,
            provider=provider.name,
            model=request.model or "default"
        )
    except Exception as e:
        return AIGenerateResponse(
            success=False,
            error=str(e),
            provider="unknown",
            model="unknown"
        )


@router.post("/analyze-vulnerability")
async def analyze_vulnerability(vulnerability_data: Dict[str, Any], current_user: User = Depends(get_current_user)):
    """AI-powered vulnerability analysis"""
    prompt = f"""
    Analyze this vulnerability for a penetration testing report:
    
    CVE: {vulnerability_data.get('cve_id', 'Unknown')}
    Description: {vulnerability_data.get('description', '')}
    Severity: {vulnerability_data.get('severity', 'Unknown')}
    Target: {vulnerability_data.get('target', 'Unknown')}
    
    Provide:
    1. Business impact assessment
    2. Exploitability analysis
    3. Remediation recommendations
    4. Risk score explanation
    """
    
    result = ai_service.generate_text(prompt)
    
    return {
        "success": result is not None,
        "analysis": result,
        "vulnerability": vulnerability_data
    }


@router.post("/generate-metasploit-module")
async def generate_metasploit_module(module_data: Dict[str, Any], current_user: User = Depends(get_current_user)):
    """Generate custom Metasploit module"""
    prompt = f"""
    Generate a complete Metasploit exploit module in Ruby for:
    
    CVE: {module_data.get('cve_id', 'Custom')}
    Vulnerability: {module_data.get('vulnerability', '')}
    Target: {module_data.get('target', '')}
    Requirements: {module_data.get('requirements', '')}
    
    Create a complete Ruby module with:
    1. Module metadata (name, description, author, references)
    2. Exploit initialization
    3. Exploit method
    4. Payload handling
    5. Error handling
    6. Documentation comments
    """
    
    result = ai_service.generate_text(prompt)
    
    return {
        "success": result is not None,
        "module_code": result,
        "module_data": module_data
    }


@router.post("/generate-exploit")
async def generate_exploit(exploit_data: Dict[str, Any], current_user: User = Depends(get_current_user)):
    """Generate custom exploit code"""
    language = exploit_data.get('language', 'python')
    vulnerability = exploit_data.get('vulnerability', '')
    target = exploit_data.get('target', '')
    
    prompt = f"""
    Generate a {language} exploit for:
    
    Vulnerability: {vulnerability}
    Target: {target}
    
    Create a complete, working exploit with:
    1. Error handling
    2. Comments explaining the exploit
    3. Payload integration
    4. Success verification
    """
    
    result = ai_service.generate_text(prompt)
    
    return {
        "success": result is not None,
        "exploit_code": result,
        "language": language,
        "exploit_data": exploit_data
    }


@router.post("/generate-report")
async def generate_report(report_data: Dict[str, Any], current_user: User = Depends(get_current_user)):
    """Generate AI-powered report"""
    report_type = report_data.get('type', 'technical')
    scan_results = report_data.get('scan_results', {})
    
    prompt = f"""
    Generate a {report_type} penetration testing report based on these findings:
    
    {json.dumps(scan_results, indent=2)}
    
    Create a comprehensive report with:
    1. Executive summary (if executive type)
    2. Technical findings
    3. Risk assessment
    4. Remediation recommendations
    5. Evidence summary
    """
    
    result = ai_service.generate_text(prompt)
    
    return {
        "success": result is not None,
        "report": result,
        "report_type": report_type
    }


@router.post("/detect-false-positive")
async def detect_false_positive(finding_data: Dict[str, Any], current_user: User = Depends(get_current_user)):
    """AI-powered false positive detection"""
    prompt = f"""
    Analyze this finding to determine if it's a false positive:

    Title: {finding_data.get('title', '')}
    Description: {finding_data.get('description', '')}
    Tool: {finding_data.get('tool_name', '')}
    Target: {finding_data.get('target', '')}
    Tool Output: {json.dumps(finding_data.get('tool_output', {}), indent=2)}

    Provide:
    1. False positive probability (0-100%)
    2. Reasoning
    3. Confidence level
    4. Recommendations
    """

    result = ai_service.generate_text(prompt)

    return {
        "success": result is not None,
        "analysis": result,
        "finding": finding_data
    }


# ==================== AUTONOMOUS AI PENTEST ====================

class AutonomousPentestRequest(BaseModel):
    """Request for autonomous AI-driven pentest"""
    task: str  # Natural language task description
    provider: str = "anthropic"  # AI provider: anthropic, openai, deepseek, ollama, openai_compatible
    api_key: Optional[str] = None  # API key (or use env var)
    model: Optional[str] = None  # Model name (provider-specific)
    base_url: Optional[str] = None  # Custom API base URL (for openai_compatible)
    targets: Optional[List[str]] = None  # Optional explicit targets

    @classmethod
    def validate_targets(cls, targets):
        """Validate target IPs/CIDRs are not internal"""
        import re
        if targets:
            for t in targets:
                # Block localhost and link-local
                if re.match(r'^(127\.|0\.0\.0\.0|localhost|::1|169\.254\.)', t):
                    raise ValueError(f"Target {t} is not allowed (localhost/link-local)")
        return targets


class AutonomousPentestResponse(BaseModel):
    """Response from autonomous pentest"""
    success: bool
    task: str
    iterations: int
    tool_calls: List[Dict[str, Any]]
    complete: bool
    summary: Optional[str]
    findings_count: Optional[int] = 0
    critical_findings: Optional[List[str]] = None
    error: Optional[str] = None


@router.post("/autonomous-pentest", response_model=AutonomousPentestResponse)
async def run_autonomous_pentest(request: AutonomousPentestRequest, current_user: User = Depends(get_current_user)):
    """
    Run an autonomous AI-driven penetration test.

    The AI will:
    1. Analyze the task
    2. Plan the attack
    3. Execute scans and exploits
    4. Document findings
    5. Generate report

    Example tasks:
    - "Scan 192.168.1.0/24 and find all vulnerabilities"
    - "Perform a full pentest on 10.0.0.5 including exploitation"
    - "Find and exploit any weak credentials on the network"
    """
    import os
    from app.services.ai.mcp_client import PentestMCPClient

    # Get API key from request or environment based on provider
    api_key = request.api_key
    if not api_key:
        env_var_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
        }
        env_var = env_var_map.get(request.provider.lower())
        if env_var:
            api_key = os.environ.get(env_var)

    # Check if API key is required for this provider
    providers_without_key = ["ollama", "claude_code", "claude_code_bridge"]
    if not api_key and request.provider.lower() not in providers_without_key:
        return AutonomousPentestResponse(
            success=False,
            task=request.task,
            iterations=0,
            tool_calls=[],
            complete=False,
            summary=None,
            error=f"No API key provided. Set {env_var_map.get(request.provider.lower(), 'API_KEY')} environment variable or pass api_key in request."
        )

    try:
        # Create MCP client with selected provider
        client = PentestMCPClient(
            provider=request.provider,
            api_key=api_key,
            model=request.model,
            base_url=request.base_url,
            platform_url=f"http://localhost:{os.environ.get('BACKEND_PORT', '8888')}"
        )

        # Build task with explicit targets if provided
        task = request.task
        if request.targets:
            task += f"\n\nTargets: {', '.join(request.targets)}"

        # Run autonomous pentest
        results = client.run_autonomous_pentest(task)

        return AutonomousPentestResponse(
            success=True,
            task=request.task,
            iterations=results.get("iterations", 0),
            tool_calls=results.get("tool_calls", []),
            complete=results.get("complete", False),
            summary=results.get("summary"),
            findings_count=results.get("findings_count", 0),
            critical_findings=results.get("critical_findings", [])
        )

    except Exception as e:
        return AutonomousPentestResponse(
            success=False,
            task=request.task,
            iterations=0,
            tool_calls=[],
            complete=False,
            summary=None,
            error=str(e)
        )


@router.get("/autonomous-pentest/status")
async def get_autonomous_pentest_status():
    """Check if autonomous pentest capability is available"""
    import os
    from app.services.ai.mcp_client import get_supported_providers

    # Check which providers have API keys configured
    configured_providers = []
    env_checks = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }

    for provider, env_var in env_checks.items():
        if os.environ.get(env_var):
            configured_providers.append(provider)

    # Ollama doesn't need a key
    configured_providers.append("ollama")

    return {
        "available": len(configured_providers) > 0,
        "configured_providers": configured_providers,
        "supported_providers": get_supported_providers(),
        "instructions": "Pass provider and api_key in request, or set environment variables (ANTHROPIC_API_KEY, OPENAI_API_KEY, DEEPSEEK_API_KEY)",
        "example_requests": [
            {
                "provider": "anthropic",
                "task": "Perform a full penetration test on 192.168.1.0/24",
                "api_key": "sk-ant-..."
            },
            {
                "provider": "deepseek",
                "task": "Scan 10.0.0.0/24 and find vulnerabilities",
                "api_key": "sk-..."
            },
            {
                "provider": "openai",
                "task": "Test credentials on FTP and SSH services",
                "model": "gpt-4-turbo",
                "api_key": "sk-..."
            },
            {
                "provider": "openai_compatible",
                "task": "Run recon on target network",
                "base_url": "https://your-api.com/v1",
                "model": "custom-model"
            }
        ]
    }
