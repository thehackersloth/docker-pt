"""
OAuth2/OIDC authentication service
"""

import httpx
import logging
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import create_access_token, get_password_hash
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OAuthService:
    """OAuth2/OIDC authentication service"""
    
    def __init__(self):
        self.providers = {}
        self._load_providers()
    
    def _load_providers(self):
        """Load OAuth provider configurations"""
        # Google OAuth
        if getattr(settings, 'OAUTH_GOOGLE_ENABLED', False):
            self.providers['google'] = {
                'client_id': getattr(settings, 'OAUTH_GOOGLE_CLIENT_ID', ''),
                'client_secret': getattr(settings, 'OAUTH_GOOGLE_CLIENT_SECRET', ''),
                'authorization_url': 'https://accounts.google.com/o/oauth2/v2/auth',
                'token_url': 'https://oauth2.googleapis.com/token',
                'userinfo_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
                'scopes': ['openid', 'email', 'profile']
            }
        
        # GitHub OAuth
        if getattr(settings, 'OAUTH_GITHUB_ENABLED', False):
            self.providers['github'] = {
                'client_id': getattr(settings, 'OAUTH_GITHUB_CLIENT_ID', ''),
                'client_secret': getattr(settings, 'OAUTH_GITHUB_CLIENT_SECRET', ''),
                'authorization_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'userinfo_url': 'https://api.github.com/user',
                'scopes': ['read:user', 'user:email']
            }
        
        # Microsoft/Azure AD
        if getattr(settings, 'OAUTH_MICROSOFT_ENABLED', False):
            tenant_id = getattr(settings, 'OAUTH_MICROSOFT_TENANT_ID', 'common')
            self.providers['microsoft'] = {
                'client_id': getattr(settings, 'OAUTH_MICROSOFT_CLIENT_ID', ''),
                'client_secret': getattr(settings, 'OAUTH_MICROSOFT_CLIENT_SECRET', ''),
                'authorization_url': f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize',
                'token_url': f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
                'userinfo_url': 'https://graph.microsoft.com/v1.0/me',
                'scopes': ['openid', 'email', 'profile']
            }
    
    def get_authorization_url(self, provider: str, redirect_uri: str, state: str) -> Optional[str]:
        """Get OAuth authorization URL"""
        if provider not in self.providers:
            return None
        
        config = self.providers[provider]
        params = {
            'client_id': config['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(config['scopes']),
            'state': state
        }
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{config['authorization_url']}?{query_string}"
    
    async def exchange_code_for_token(self, provider: str, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        if provider not in self.providers:
            return None
        
        config = self.providers[provider]
        
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    'client_id': config['client_id'],
                    'client_secret': config['client_secret'],
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                }
                
                headers = {'Accept': 'application/json'}
                if provider == 'github':
                    headers['Accept'] = 'application/json'
                
                response = await client.post(
                    config['token_url'],
                    data=data,
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"OAuth token exchange failed: {e}")
            return None
    
    async def get_user_info(self, provider: str, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from OAuth provider"""
        if provider not in self.providers:
            return None
        
        config = self.providers[provider]
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {'Authorization': f'Bearer {access_token}'}
                
                response = await client.get(
                    config['userinfo_url'],
                    headers=headers,
                    timeout=10
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"OAuth user info fetch failed: {e}")
            return None
    
    def get_or_create_user(self, provider: str, user_info: Dict[str, Any]) -> User:
        """Get or create user from OAuth info"""
        db = SessionLocal()
        try:
            # Extract email
            email = user_info.get('email') or user_info.get('mail') or user_info.get('userPrincipalName')
            if not email:
                raise ValueError("No email found in OAuth user info")
            
            # Check if user exists
            user = db.query(User).filter(User.email == email).first()
            
            if user:
                # Update last login
                user.last_login = datetime.utcnow()
                db.commit()
                return user
            
            # Create new user
            username = user_info.get('login') or user_info.get('preferred_username') or email.split('@')[0]
            full_name = user_info.get('name') or f"{user_info.get('given_name', '')} {user_info.get('family_name', '')}".strip()
            
            user = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(f"oauth_{provider}_{email}"),  # Placeholder password
                full_name=full_name or None,
                role=UserRole.VIEWER,  # Default role
                is_active=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return user
        finally:
            db.close()
