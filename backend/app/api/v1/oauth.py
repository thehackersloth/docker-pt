"""
OAuth2/OIDC authentication endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import secrets
from app.core.database import SessionLocal, get_db
from app.services.oauth_service import OAuthService
from app.core.security import create_access_token
from app.core.config import settings
from datetime import timedelta

router = APIRouter()
oauth_service = OAuthService()


class OAuthCallback(BaseModel):
    code: str
    state: str


# Store OAuth states (use Redis in production)
oauth_states = {}


@router.get("/providers")
async def list_providers():
    """List available OAuth providers"""
    providers = []
    for provider in oauth_service.providers.keys():
        providers.append({
            "name": provider,
            "enabled": True,
            "authorization_url": f"/api/v1/oauth/{provider}/authorize"
        })
    return {"providers": providers}


@router.get("/{provider}/authorize")
async def authorize(
    provider: str,
    redirect_uri: str,
    request: Request
):
    """Initiate OAuth authorization"""
    if provider not in oauth_service.providers:
        raise HTTPException(status_code=404, detail="OAuth provider not found")
    
    # Generate state
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "provider": provider,
        "redirect_uri": redirect_uri
    }
    
    # Get authorization URL
    auth_url = oauth_service.get_authorization_url(
        provider,
        redirect_uri,
        state
    )
    
    if not auth_url:
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")
    
    return RedirectResponse(url=auth_url)


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str,
    state: str,
    request: Request
):
    """OAuth callback handler"""
    # Verify state
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Invalid state")
    
    state_data = oauth_states[state]
    if state_data["provider"] != provider:
        raise HTTPException(status_code=400, detail="State mismatch")
    
    redirect_uri = state_data["redirect_uri"]
    del oauth_states[state]
    
    # Exchange code for token
    token_data = await oauth_service.exchange_code_for_token(
        provider,
        code,
        redirect_uri
    )
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    
    access_token = token_data.get('access_token') or token_data.get('token')
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token in response")
    
    # Get user info
    user_info = await oauth_service.get_user_info(provider, access_token)
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    # Get or create user
    user = oauth_service.get_or_create_user(provider, user_info)
    
    # Create JWT token
    jwt_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Redirect to frontend with token
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    return RedirectResponse(
        url=f"{frontend_url}/auth/callback?token={jwt_token}"
    )


@router.post("/{provider}/token")
async def get_token(
    provider: str,
    code: str,
    redirect_uri: str
):
    """Exchange code for JWT token (API endpoint)"""
    # Exchange code for OAuth token
    token_data = await oauth_service.exchange_code_for_token(
        provider,
        code,
        redirect_uri
    )
    
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange code")
    
    access_token = token_data.get('access_token') or token_data.get('token')
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token")
    
    # Get user info
    user_info = await oauth_service.get_user_info(provider, access_token)
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")
    
    # Get or create user
    user = oauth_service.get_or_create_user(provider, user_info)
    
    # Create JWT token
    jwt_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email
        }
    }
