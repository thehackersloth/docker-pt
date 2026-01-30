"""
Authorization and disclaimer endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.authorization import Authorization, Disclaimer
from app.models.scan import Scan
from sqlalchemy.orm import Session

router = APIRouter()


class AuthorizationRequest(BaseModel):
    target: str
    scope: Optional[str] = None
    authorized_by: Optional[str] = None
    authorization_date: Optional[datetime] = None
    disclaimer_accepted: bool = False
    terms_accepted: bool = False


class AuthorizationResponse(BaseModel):
    id: str
    target: str
    disclaimer_accepted: bool
    terms_accepted: bool
    created_at: datetime


@router.get("/disclaimer/current")
async def get_current_disclaimer():
    """Get current active disclaimer"""
    db = SessionLocal()
    try:
        disclaimer = db.query(Disclaimer).filter(
            Disclaimer.is_active == True
        ).order_by(Disclaimer.created_at.desc()).first()
        
        if not disclaimer:
            # Return default disclaimer
            return {
                "version": "1.0",
                "title": "Penetration Testing Authorization",
                "content": """
                ⚠️ WARNING: UNAUTHORIZED ACCESS IS ILLEGAL
                
                This platform is for AUTHORIZED penetration testing only.
                
                By using this platform, you agree that:
                1. You have written authorization to test the specified targets
                2. You will only test systems you are authorized to test
                3. You understand that unauthorized access is illegal
                4. You accept full responsibility for your actions
                5. The platform authors are not liable for misuse
                
                You must have proper authorization before scanning any system.
                """
            }
        
        return {
            "version": disclaimer.version,
            "title": disclaimer.title,
            "content": disclaimer.content
        }
    finally:
        db.close()


@router.post("/create")
async def create_authorization(
    request: AuthorizationRequest,
    scan_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """Create scan authorization"""
    
    # Get current disclaimer
    disclaimer = db.query(Disclaimer).filter(
        Disclaimer.is_active == True
    ).order_by(Disclaimer.created_at.desc()).first()
    
    if not request.disclaimer_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the disclaimer to proceed"
        )
    
    if not request.terms_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must accept the terms to proceed"
        )
    
    # Create authorization
    authorization = Authorization(
        scan_id=scan_id,
        user_id=str(current_user.id),
        username=current_user.username,
        ip_address=http_request.client.host if http_request else None,
        user_agent=http_request.headers.get("user-agent") if http_request else None,
        target=request.target,
        scope=request.scope,
        authorized_by=request.authorized_by,
        authorization_date=request.authorization_date or datetime.utcnow(),
        disclaimer_accepted=request.disclaimer_accepted,
        disclaimer_text=disclaimer.content if disclaimer else None,
        disclaimer_version=disclaimer.version if disclaimer else "1.0",
        terms_accepted=request.terms_accepted,
        terms_version="1.0"
    )
    
    db.add(authorization)
    db.commit()
    db.refresh(authorization)
    
    return AuthorizationResponse(
        id=str(authorization.id),
        target=authorization.target,
        disclaimer_accepted=authorization.disclaimer_accepted,
        terms_accepted=authorization.terms_accepted,
        created_at=authorization.created_at
    )


@router.get("/scan/{scan_id}")
async def get_scan_authorization(
    scan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get authorization for a scan"""
    authorization = db.query(Authorization).filter(
        Authorization.scan_id == scan_id
    ).first()
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No authorization found for this scan"
        )
    
    return {
        "id": str(authorization.id),
        "target": authorization.target,
        "scope": authorization.scope,
        "authorized_by": authorization.authorized_by,
        "disclaimer_accepted": authorization.disclaimer_accepted,
        "terms_accepted": authorization.terms_accepted,
        "created_at": authorization.created_at
    }


@router.get("/validate/{target}")
async def validate_target_authorization(
    target: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate if target is authorized for scanning"""
    # Check for existing authorization
    authorization = db.query(Authorization).filter(
        Authorization.target == target,
        Authorization.user_id == str(current_user.id),
        Authorization.disclaimer_accepted == True,
        Authorization.terms_accepted == True
    ).order_by(Authorization.created_at.desc()).first()
    
    if not authorization:
        return {
            "authorized": False,
            "message": "No authorization found. Please create authorization first."
        }
    
    # Check if expired
    if authorization.expires_at and datetime.utcnow() > authorization.expires_at:
        return {
            "authorized": False,
            "message": "Authorization has expired"
        }
    
    return {
        "authorized": True,
        "authorization_id": str(authorization.id),
        "scope": authorization.scope,
        "authorized_by": authorization.authorized_by
    }
