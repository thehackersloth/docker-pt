"""
Session management endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List
from datetime import datetime
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.session import Session
from sqlalchemy.orm import Session

router = APIRouter()


class SessionResponse(BaseModel):
    id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    is_active: bool


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all active sessions for current user"""
    sessions = db.query(Session).filter(
        Session.user_id == str(current_user.id),
        Session.is_active == True
    ).order_by(Session.last_activity.desc()).all()
    
    return [
        SessionResponse(
            id=str(s.id),
            ip_address=s.ip_address or "Unknown",
            user_agent=s.user_agent or "Unknown",
            created_at=s.created_at,
            last_activity=s.last_activity,
            expires_at=s.expires_at,
            is_active=s.is_active
        )
        for s in sessions
    ]


@router.delete("/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a session"""
    session = db.query(Session).filter(
        Session.id == session_id,
        Session.user_id == str(current_user.id)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    db.commit()
    
    return {"message": "Session revoked"}


@router.delete("")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke all sessions for current user"""
    sessions = db.query(Session).filter(
        Session.user_id == str(current_user.id),
        Session.is_active == True
    ).all()
    
    for session in sessions:
        session.is_active = False
    
    db.commit()
    
    return {"message": f"Revoked {len(sessions)} sessions"}
