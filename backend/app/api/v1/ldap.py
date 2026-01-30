"""
LDAP/Active Directory authentication endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import SessionLocal, get_db
from app.services.ldap_service import LDAPService
from app.core.security import create_access_token, get_current_user
from app.core.config import settings
from app.models.user import User
from datetime import timedelta

router = APIRouter()
ldap_service = LDAPService()


class LDAPLogin(BaseModel):
    username: str
    password: str


class LDAPUserSearch(BaseModel):
    query: str
    limit: int = 10


@router.post("/login")
async def ldap_login(
    login: LDAPLogin,
    db: SessionLocal = Depends(get_db)
):
    """Login with LDAP/AD credentials"""
    if not ldap_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP authentication is not enabled"
        )
    
    # Authenticate against LDAP
    ldap_user = ldap_service.authenticate(login.username, login.password)
    if not ldap_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid LDAP credentials"
        )
    
    # Get or create user
    user = ldap_service.get_or_create_user(ldap_user)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create JWT token
    from app.core.security import create_access_token
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
            "email": user.email,
            "role": user.role.value
        }
    }


@router.get("/search")
async def search_users(
    query: str,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """Search for users in LDAP/AD"""
    if not ldap_service.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LDAP is not enabled"
        )
    
    users = ldap_service.search_users(query, limit)
    return {"users": users}


@router.get("/status")
async def ldap_status():
    """Get LDAP service status"""
    return {
        "enabled": ldap_service.enabled,
        "server": ldap_service.server_url if ldap_service.enabled else None,
        "base_dn": ldap_service.base_dn if ldap_service.enabled else None
    }
