"""
Rate limiting middleware
"""

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Dict
import time
from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production)
rate_limit_store: Dict[str, list] = defaultdict(list)


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        rate_limit_store[key] = [
            timestamp for timestamp in rate_limit_store[key]
            if timestamp > minute_ago
        ]
        
        # Check limit
        if len(rate_limit_store[key]) >= self.requests_per_minute:
            return False
        
        # Add current request
        rate_limit_store[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests"""
        now = time.time()
        minute_ago = now - 60
        
        rate_limit_store[key] = [
            timestamp for timestamp in rate_limit_store[key]
            if timestamp > minute_ago
        ]
        
        return max(0, self.requests_per_minute - len(rate_limit_store[key]))


def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Create rate limiter
    limiter = RateLimiter(requests_per_minute=60)
    
    # Check rate limit
    if not limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    response = call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(limiter.get_remaining(client_ip))
    return response
