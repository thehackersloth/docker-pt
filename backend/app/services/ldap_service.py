"""
LDAP/Active Directory authentication service
"""

import ldap3
from ldap3 import Server, Connection, ALL, SUBTREE
from typing import Optional, Dict, Any, List
import logging
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import create_access_token, get_password_hash
from datetime import datetime

logger = logging.getLogger(__name__)


class LDAPService:
    """LDAP/Active Directory authentication service"""
    
    def __init__(self):
        self.server_url = getattr(settings, 'LDAP_SERVER', '')
        self.base_dn = getattr(settings, 'LDAP_BASE_DN', '')
        self.bind_dn = getattr(settings, 'LDAP_BIND_DN', '')
        self.bind_password = getattr(settings, 'LDAP_BIND_PASSWORD', '')
        self.user_search_base = getattr(settings, 'LDAP_USER_SEARCH_BASE', '')
        self.user_search_filter = getattr(settings, 'LDAP_USER_SEARCH_FILTER', '(sAMAccountName={username})')
        self.user_attributes = ['cn', 'mail', 'sAMAccountName', 'displayName', 'memberOf']
        self.enabled = getattr(settings, 'LDAP_ENABLED', False)
    
    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user against LDAP/AD"""
        if not self.enabled:
            return None
        
        try:
            # Connect to LDAP server
            server = Server(self.server_url, get_info=ALL)
            
            # First, bind with service account to search for user
            conn = Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True
            )
            
            # Search for user
            search_base = self.user_search_base or self.base_dn
            search_filter = self.user_search_filter.format(username=username)
            
            conn.search(
                search_base,
                search_filter,
                search_scope=SUBTREE,
                attributes=self.user_attributes
            )
            
            if not conn.entries:
                logger.warning(f"LDAP user not found: {username}")
                return None
            
            user_dn = conn.entries[0].entry_dn
            user_attrs = conn.entries[0]
            
            # Try to bind with user's credentials
            user_conn = Connection(
                server,
                user=user_dn,
                password=password,
                auto_bind=True
            )
            
            # Extract user information
            email = str(user_attrs.mail) if hasattr(user_attrs, 'mail') else None
            if not email:
                # Try alternative email attributes
                email = str(user_attrs.userPrincipalName) if hasattr(user_attrs, 'userPrincipalName') else None
            
            full_name = str(user_attrs.cn) if hasattr(user_attrs, 'cn') else str(user_attrs.displayName) if hasattr(user_attrs, 'displayName') else username
            
            # Get groups
            groups = []
            if hasattr(user_attrs, 'memberOf'):
                groups = [str(g) for g in user_attrs.memberOf]
            
            user_conn.unbind()
            conn.unbind()
            
            return {
                'username': username,
                'email': email or f"{username}@domain.local",
                'full_name': full_name,
                'dn': user_dn,
                'groups': groups
            }
            
        except ldap3.core.exceptions.LDAPBindError as e:
            logger.warning(f"LDAP authentication failed for {username}: {e}")
            return None
        except Exception as e:
            logger.error(f"LDAP error: {e}")
            return None
    
    def get_or_create_user(self, ldap_user: Dict[str, Any]) -> User:
        """Get or create user from LDAP info"""
        db = SessionLocal()
        try:
            username = ldap_user['username']
            email = ldap_user['email']
            
            # Check if user exists
            user = db.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if user:
                # Update user info
                user.full_name = ldap_user.get('full_name')
                user.last_login = datetime.utcnow()
                db.commit()
                return user
            
            # Determine role from groups
            role = UserRole.VIEWER
            groups = ldap_user.get('groups', [])
            admin_groups = getattr(settings, 'LDAP_ADMIN_GROUPS', [])
            operator_groups = getattr(settings, 'LDAP_OPERATOR_GROUPS', [])
            
            for group in groups:
                if any(admin_group.lower() in group.lower() for admin_group in admin_groups):
                    role = UserRole.ADMIN
                    break
                elif any(op_group.lower() in group.lower() for op_group in operator_groups):
                    role = UserRole.OPERATOR
                    break
            
            # Create new user
            user = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(f"ldap_{username}"),  # Placeholder, LDAP handles auth
                full_name=ldap_user.get('full_name'),
                role=role,
                is_active=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return user
        finally:
            db.close()
    
    def search_users(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for users in LDAP"""
        if not self.enabled:
            return []
        
        try:
            server = Server(self.server_url, get_info=ALL)
            conn = Connection(
                server,
                user=self.bind_dn,
                password=self.bind_password,
                auto_bind=True
            )
            
            search_base = self.user_search_base or self.base_dn
            search_filter = f"(&(objectClass=user)(|(cn=*{query}*)(sAMAccountName=*{query}*)(mail=*{query}*)))"
            
            conn.search(
                search_base,
                search_filter,
                search_scope=SUBTREE,
                attributes=self.user_attributes,
                size_limit=limit
            )
            
            users = []
            for entry in conn.entries:
                users.append({
                    'username': str(entry.sAMAccountName) if hasattr(entry, 'sAMAccountName') else '',
                    'email': str(entry.mail) if hasattr(entry, 'mail') else '',
                    'full_name': str(entry.cn) if hasattr(entry, 'cn') else '',
                    'dn': entry.entry_dn
                })
            
            conn.unbind()
            return users
            
        except Exception as e:
            logger.error(f"LDAP search error: {e}")
            return []
