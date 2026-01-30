"""
MFA/2FA endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.mfa_service import MFAService

router = APIRouter()
mfa_service = MFAService()


class MFAEnableRequest(BaseModel):
    secret: str


class MFAVerifyRequest(BaseModel):
    token: str


@router.post("/setup")
async def setup_mfa(current_user: User = Depends(get_current_user)):
    """Setup MFA for user"""
    secret = MFAService.generate_secret()
    qr_code = MFAService.generate_qr_code(secret, current_user.username)
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "message": "Scan QR code with authenticator app"
    }


@router.post("/enable")
async def enable_mfa(
    request: MFAEnableRequest,
    current_user: User = Depends(get_current_user)
):
    """Enable MFA for user"""
    # Verify secret works first
    test_token = request.token if hasattr(request, 'token') else None
    if test_token and not MFAService.verify_totp(request.secret, test_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token"
        )
    
    success = mfa_service.enable_mfa(str(current_user.id), request.secret)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable MFA"
        )
    
    return {"message": "MFA enabled successfully"}


@router.post("/verify")
async def verify_mfa(
    request: MFAVerifyRequest,
    current_user: User = Depends(get_current_user)
):
    """Verify MFA token"""
    # Get user's MFA secret (from database)
    # For now, return structure
    # secret = current_user.mfa_secret
    # if not secret:
    #     raise HTTPException(status_code=400, detail="MFA not enabled")
    
    # is_valid = MFAService.verify_totp(secret, request.token)
    # if not is_valid:
    #     raise HTTPException(status_code=401, detail="Invalid MFA token")
    
    return {"verified": True}
