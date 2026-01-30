"""
Configuration management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from app.core.config import settings
from app.core.security import get_current_user, require_admin
from app.models.user import User

router = APIRouter()


class AIConfig(BaseModel):
    enabled: bool
    privacy_mode: str  # strict, normal, permissive
    local_only: bool
    
    # Cloud AI
    openai_enabled: bool
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo"
    
    anthropic_enabled: bool
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-opus-20240229"
    
    github_copilot_enabled: bool
    github_copilot_key: Optional[str] = None
    
    gemini_enabled: bool
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-pro"
    
    # Local AI
    ollama_enabled: bool
    ollama_base_url: str
    ollama_model: str
    
    llama_cpp_enabled: bool
    llama_cpp_model_path: str
    
    rayserve_enabled: bool
    rayserve_endpoint: str
    
    whiterabbit_neo_enabled: bool
    whiterabbit_neo_base_url: str
    whiterabbit_neo_model: str


class EmailConfig(BaseModel):
    enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool
    smtp_use_ssl: bool
    email_from: str
    email_from_name: str


class ScanConfig(BaseModel):
    max_concurrent_scans: int
    max_scan_duration: int
    require_authorization: bool
    confirm_destructive_actions: bool


class ToolConfig(BaseModel):
    nmap_enabled: bool
    openvas_enabled: bool
    owasp_zap_enabled: bool
    metasploit_enabled: bool
    bloodhound_enabled: bool
    crackmapexec_enabled: bool


class SecurityConfig(BaseModel):
    jwt_expiration: int
    require_mfa: bool
    audit_enabled: bool
    log_ai_queries: bool


class SystemConfig(BaseModel):
    app_name: str
    app_version: str
    timezone: str
    log_level: str
    debug: bool


class ConfigResponse(BaseModel):
    ai: AIConfig
    email: EmailConfig
    scan: ScanConfig
    tools: ToolConfig
    security: SecurityConfig
    system: SystemConfig


class ConfigUpdate(BaseModel):
    ai: Optional[AIConfig] = None
    email: Optional[EmailConfig] = None
    scan: Optional[ScanConfig] = None
    tools: Optional[ToolConfig] = None
    security: Optional[SecurityConfig] = None
    system: Optional[SystemConfig] = None


@router.get("", response_model=ConfigResponse)
async def get_config(current_user: User = Depends(get_current_user)):
    """Get current configuration"""
    return ConfigResponse(
        ai=AIConfig(
            enabled=settings.AI_ENABLED,
            privacy_mode=settings.AI_PRIVACY_MODE,
            local_only=settings.AI_LOCAL_ONLY,
            openai_enabled=settings.OPENAI_ENABLED,
            openai_api_key="***" if settings.OPENAI_API_KEY else None,
            openai_model="gpt-4-turbo",
            anthropic_enabled=settings.ANTHROPIC_ENABLED,
            anthropic_api_key="***" if settings.ANTHROPIC_API_KEY else None,
            anthropic_model="claude-3-opus-20240229",
            github_copilot_enabled=settings.GITHUB_COPILOT_ENABLED,
            github_copilot_key="***" if settings.GITHUB_COPILOT_KEY else None,
            gemini_enabled=settings.GEMINI_ENABLED,
            gemini_api_key="***" if settings.GEMINI_API_KEY else None,
            gemini_model="gemini-pro",
            ollama_enabled=settings.OLLAMA_ENABLED,
            ollama_base_url=settings.OLLAMA_BASE_URL,
            ollama_model=settings.OLLAMA_MODEL,
            llama_cpp_enabled=settings.LLAMA_CPP_ENABLED,
            llama_cpp_model_path=settings.LLAMA_CPP_MODEL_PATH,
            rayserve_enabled=settings.RAYSERVE_ENABLED,
            rayserve_endpoint=settings.RAYSERVE_ENDPOINT,
            whiterabbit_neo_enabled=settings.WHITERABBIT_NEO_ENABLED,
            whiterabbit_neo_base_url=settings.WHITERABBIT_NEO_BASE_URL,
            whiterabbit_neo_model=settings.WHITERABBIT_NEO_MODEL,
        ),
        email=EmailConfig(
            enabled=settings.SMTP_ENABLED,
            smtp_host=settings.SMTP_HOST,
            smtp_port=settings.SMTP_PORT,
            smtp_username=settings.SMTP_USERNAME,
            smtp_password="***" if settings.SMTP_PASSWORD else None,
            smtp_use_tls=settings.SMTP_USE_TLS,
            smtp_use_ssl=False,
            email_from=settings.EMAIL_FROM,
            email_from_name=settings.EMAIL_FROM_NAME,
        ),
        scan=ScanConfig(
            max_concurrent_scans=settings.MAX_CONCURRENT_SCANS,
            max_scan_duration=settings.MAX_SCAN_DURATION,
            require_authorization=True,
            confirm_destructive_actions=True,
        ),
        tools=ToolConfig(
            nmap_enabled=True,
            openvas_enabled=True,
            owasp_zap_enabled=True,
            metasploit_enabled=True,
            bloodhound_enabled=True,
            crackmapexec_enabled=True,
        ),
        security=SecurityConfig(
            jwt_expiration=settings.JWT_EXPIRATION,
            require_mfa=False,
            audit_enabled=settings.AUDIT_ENABLED,
            log_ai_queries=settings.LOG_AI_QUERIES,
        ),
        system=SystemConfig(
            app_name=settings.APP_NAME,
            app_version=settings.APP_VERSION,
            timezone=settings.TIMEZONE,
            log_level=settings.LOG_LEVEL,
            debug=settings.DEBUG,
        ),
    )


@router.put("", response_model=ConfigResponse)
async def update_config(config: ConfigUpdate, current_user: User = Depends(require_admin)):
    """Update configuration (admin only)"""
    import os
    from pathlib import Path

    env_file = Path("/app/backend/.env")
    env_updates = {}

    if config.ai:
        env_updates['AI_ENABLED'] = str(config.ai.enabled).lower()
        env_updates['AI_PRIVACY_MODE'] = config.ai.privacy_mode
        env_updates['AI_LOCAL_ONLY'] = str(config.ai.local_only).lower()
        env_updates['OPENAI_ENABLED'] = str(config.ai.openai_enabled).lower()
        if config.ai.openai_api_key and config.ai.openai_api_key != "***":
            env_updates['OPENAI_API_KEY'] = config.ai.openai_api_key
        env_updates['ANTHROPIC_ENABLED'] = str(config.ai.anthropic_enabled).lower()
        if config.ai.anthropic_api_key and config.ai.anthropic_api_key != "***":
            env_updates['ANTHROPIC_API_KEY'] = config.ai.anthropic_api_key
        env_updates['OLLAMA_ENABLED'] = str(config.ai.ollama_enabled).lower()
        env_updates['OLLAMA_BASE_URL'] = config.ai.ollama_base_url
        env_updates['OLLAMA_MODEL'] = config.ai.ollama_model

    if config.email:
        env_updates['SMTP_ENABLED'] = str(config.email.enabled).lower()
        env_updates['SMTP_HOST'] = config.email.smtp_host
        env_updates['SMTP_PORT'] = str(config.email.smtp_port)
        if config.email.smtp_username:
            env_updates['SMTP_USERNAME'] = config.email.smtp_username
        if config.email.smtp_password and config.email.smtp_password != "***":
            env_updates['SMTP_PASSWORD'] = config.email.smtp_password
        env_updates['SMTP_USE_TLS'] = str(config.email.smtp_use_tls).lower()
        env_updates['EMAIL_FROM'] = config.email.email_from
        env_updates['EMAIL_FROM_NAME'] = config.email.email_from_name

    if config.scan:
        env_updates['MAX_CONCURRENT_SCANS'] = str(config.scan.max_concurrent_scans)
        env_updates['MAX_SCAN_DURATION'] = str(config.scan.max_scan_duration)

    if config.system:
        env_updates['LOG_LEVEL'] = config.system.log_level
        env_updates['DEBUG'] = str(config.system.debug).lower()
        env_updates['TIMEZONE'] = config.system.timezone

    # Write updates to .env file
    if env_updates and env_file.exists():
        lines = env_file.read_text().splitlines()
        new_lines = []
        updated_keys = set()

        for line in lines:
            if '=' in line and not line.startswith('#'):
                key = line.split('=', 1)[0].strip()
                if key in env_updates:
                    new_lines.append(f"{key}={env_updates[key]}")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        # Add any new keys not already in file
        for key, value in env_updates.items():
            if key not in updated_keys:
                new_lines.append(f"{key}={value}")

        env_file.write_text('\n'.join(new_lines) + '\n')

        # Also update runtime settings
        for key, value in env_updates.items():
            os.environ[key] = str(value)

    return await get_config()


@router.post("/test-email")
async def test_email(current_user: User = Depends(require_admin)):
    """Test email configuration (admin only)"""
    from app.services.email_service import EmailService

    if not settings.SMTP_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP is not enabled"
        )

    try:
        email_service = EmailService()
        success = email_service.send_email(
            to=[settings.EMAIL_FROM],
            subject="Test Email - Professional Pentesting Platform",
            body="This is a test email from the Professional Pentesting Platform.\n\nIf you received this, your email configuration is working correctly."
        )

        if success:
            return {"message": "Test email sent successfully", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test email"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email test failed: {str(e)}"
        )


@router.post("/test-ai/{provider}")
async def test_ai(provider: str, current_user: User = Depends(get_current_user)):
    """Test AI provider connection"""
    from app.services.ai_service import AIService

    ai_service = AIService()
    test_prompt = "Respond with 'OK' if you can read this message."

    try:
        if provider == "openai":
            if not settings.OPENAI_ENABLED:
                raise HTTPException(status_code=400, detail="OpenAI is not enabled")
            response = ai_service._query_openai(test_prompt)
        elif provider == "anthropic":
            if not settings.ANTHROPIC_ENABLED:
                raise HTTPException(status_code=400, detail="Anthropic is not enabled")
            response = ai_service._query_anthropic(test_prompt)
        elif provider == "ollama":
            if not settings.OLLAMA_ENABLED:
                raise HTTPException(status_code=400, detail="Ollama is not enabled")
            response = ai_service._query_ollama(test_prompt)
        elif provider == "gemini":
            if not settings.GEMINI_ENABLED:
                raise HTTPException(status_code=400, detail="Gemini is not enabled")
            response = ai_service._query_gemini(test_prompt)
        elif provider == "whiterabbit_neo":
            if not settings.WHITERABBIT_NEO_ENABLED:
                raise HTTPException(status_code=400, detail="WhiteRabbit Neo is not enabled")
            response = ai_service._query_whiterabbit_neo(test_prompt)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

        if response:
            return {"message": f"AI provider {provider} is working", "success": True, "response": response[:100]}
        else:
            raise HTTPException(status_code=500, detail=f"No response from {provider}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI test failed: {str(e)}"
        )


@router.get("/ai-models")
async def get_ai_models():
    """Get available AI models"""
    import httpx

    models = {
        "ollama": [],
        "openai": ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "gemini": ["gemini-pro", "gemini-pro-vision"],
        "whiterabbit_neo": ["whiterabbit-neo", "whiterabbit-neo-7b", "whiterabbit-neo-13b", "whiterabbit-neo-70b"],
    }

    # Fetch Ollama models dynamically if enabled
    if settings.OLLAMA_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models["ollama"] = [m["name"] for m in data.get("models", [])]
        except Exception:
            models["ollama"] = ["llama2:7b", "llama2:13b", "mistral:7b", "codellama:34b"]

    if not models["ollama"]:
        models["ollama"] = ["llama2:7b", "llama2:13b", "mistral:7b", "codellama:34b"]

    return models
