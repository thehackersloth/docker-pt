"""
Password reset functionality
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
import secrets
import hashlib
from app.core.database import SessionLocal, get_db
from app.core.security import get_password_hash, verify_password, get_current_user
from app.models.user import User
from app.services.email_service import EmailService
from sqlalchemy.orm import Session

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
email_service = EmailService()


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# In-memory token store (use Redis in production)
reset_tokens: dict[str, dict] = {}


@router.post("/request")
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset"""
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Don't reveal if user exists
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Generate reset token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Store token (expires in 1 hour)
    reset_tokens[token_hash] = {
        "user_id": str(user.id),
        "email": user.email,
        "expires_at": datetime.utcnow() + timedelta(hours=1)
    }
    
    # Send email
    reset_url = f"http://localhost/reset-password?token={token}"
    try:
        email_service.send_email(
            to=[user.email],
            subject="Password Reset Request",
            body=f"""
            You requested a password reset for your account.
            
            Click this link to reset your password:
            {reset_url}
            
            This link expires in 1 hour.
            
            If you didn't request this, please ignore this email.
            """
        )
    except Exception as e:
        # Log error but don't reveal to user
        pass
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/confirm")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    token_hash = hashlib.sha256(request.token.encode()).hexdigest()
    
    if token_hash not in reset_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    token_data = reset_tokens[token_hash]
    
    # Check expiration
    if datetime.utcnow() > token_data["expires_at"]:
        del reset_tokens[token_hash]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )
    
    # Get user
    user = db.query(User).filter(User.id == token_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate password
    if len(request.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters"
        )
    
    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    # Delete token
    del reset_tokens[token_hash]
    
    return {"message": "Password reset successfully"}


@router.post("/change")
async def change_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password (requires current password)"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(request.new_password) < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 12 characters"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
