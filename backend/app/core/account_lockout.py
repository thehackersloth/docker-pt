"""
Account lockout after failed login attempts
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from app.core.config import settings

logger = logging.getLogger(__name__)


class AccountLockoutService:
    """Account lockout service"""
    
    def __init__(self):
        self.failed_attempts = defaultdict(int)
        self.lockout_until = {}
        self.max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
        self.lockout_duration = getattr(settings, 'ACCOUNT_LOCKOUT_DURATION', 1800)  # 30 minutes
    
    def record_failed_attempt(self, username: str) -> bool:
        """Record failed login attempt and check if account should be locked"""
        self.failed_attempts[username] += 1
        
        if self.failed_attempts[username] >= self.max_attempts:
            self.lockout_until[username] = datetime.utcnow() + timedelta(seconds=self.lockout_duration)
            logger.warning(f"Account {username} locked due to {self.failed_attempts[username]} failed attempts")
            return True
        
        return False
    
    def record_successful_attempt(self, username: str):
        """Record successful login and reset failed attempts"""
        self.failed_attempts[username] = 0
        if username in self.lockout_until:
            del self.lockout_until[username]
    
    def is_locked(self, username: str) -> tuple[bool, Optional[str]]:
        """Check if account is locked"""
        if username not in self.lockout_until:
            return False, None
        
        if datetime.utcnow() < self.lockout_until[username]:
            remaining = (self.lockout_until[username] - datetime.utcnow()).total_seconds()
            return True, f"Account locked. Try again in {int(remaining)} seconds"
        
        # Lockout expired
        del self.lockout_until[username]
        self.failed_attempts[username] = 0
        return False, None
    
    def get_remaining_attempts(self, username: str) -> int:
        """Get remaining login attempts"""
        attempts = self.failed_attempts.get(username, 0)
        return max(0, self.max_attempts - attempts)


# Global instance
lockout_service = AccountLockoutService()
