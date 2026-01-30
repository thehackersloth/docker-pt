"""
User invitation system
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import hashlib
from app.core.database import SessionLocal, get_db
from app.core.security import require_admin, get_current_user, get_password_hash
from app.models.user import User, UserRole
from app.services.email_service import EmailService
from sqlalchemy.orm import Session

router = APIRouter()
email_service = EmailService()


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "viewer"
    expires_in_days: int = 7


class InvitationResponse(BaseModel):
    id: str
    email: str
    role: str
    token: str
    expires_at: datetime
    created_at: datetime
    used: bool


# In-memory invitation store (use database in production)
invitations: dict[str, dict] = {}


@router.post("", response_model=InvitationResponse)
async def create_invitation(
    invitation: InvitationCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create user invitation"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == invitation.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate invitation token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Create invitation
    invitation_data = {
        "id": secrets.token_urlsafe(16),
        "email": invitation.email,
        "role": invitation.role,
        "token": token,
        "token_hash": token_hash,
        "created_by": str(current_user.id),
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=invitation.expires_in_days),
        "used": False
    }
    
    invitations[token_hash] = invitation_data
    
    # Send invitation email
    invite_url = f"http://localhost/register?token={token}"
    try:
        email_service.send_email(
            to=[invitation.email],
            subject="Invitation to Pentest Platform",
            body=f"""
            You have been invited to join the Pentest Platform.
            
            Click this link to register:
            {invite_url}
            
            This invitation expires in {invitation.expires_in_days} days.
            
            Your role will be: {invitation.role}
            """
        )
    except Exception as e:
        # Log error but don't fail
        pass
    
    return InvitationResponse(
        id=invitation_data["id"],
        email=invitation_data["email"],
        role=invitation_data["role"],
        token=token,
        expires_at=invitation_data["expires_at"],
        created_at=invitation_data["created_at"],
        used=invitation_data["used"]
    )


@router.get("", response_model=List[InvitationResponse])
async def list_invitations(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all invitations"""
    return [
        InvitationResponse(
            id=inv["id"],
            email=inv["email"],
            role=inv["role"],
            token=inv["token"],
            expires_at=inv["expires_at"],
            created_at=inv["created_at"],
            used=inv["used"]
        )
        for inv in invitations.values()
    ]


@router.post("/verify/{token}")
async def verify_invitation(
    token: str,
    db: Session = Depends(get_db)
):
    """Verify invitation token"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    if token_hash not in invitations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )
    
    invitation = invitations[token_hash]
    
    # Check expiration
    if datetime.utcnow() > invitation["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    # Check if already used
    if invitation["used"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been used"
        )
    
    return {
        "valid": True,
        "email": invitation["email"],
        "role": invitation["role"]
    }


@router.post("/accept/{token}")
async def accept_invitation(
    token: str,
    password: str,
    username: str,
    db: Session = Depends(get_db)
):
    """Accept invitation and create user"""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    if token_hash not in invitations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invitation token"
        )
    
    invitation = invitations[token_hash]
    
    # Validate
    if datetime.utcnow() > invitation["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )
    
    if invitation["used"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has already been used"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == invitation["email"]) | (User.username == username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    
    # Create user
    user = User(
        username=username,
        email=invitation["email"],
        hashed_password=get_password_hash(password),
        role=UserRole(invitation["role"]),
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Mark invitation as used
    invitation["used"] = True
    
    return {
        "message": "User created successfully",
        "user_id": str(user.id)
    }
