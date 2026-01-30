"""
Schedule management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.schedule import Schedule, ScheduleType
from app.models.user import User
from sqlalchemy.orm import Session

router = APIRouter()


class ScheduleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    schedule_type: str  # one_time, daily, weekly, monthly, cron
    schedule_expression: str  # Cron expression or datetime
    timezone: str = "UTC"
    scan_config: dict
    email_enabled: bool = True
    email_recipients: Optional[List[str]] = None
    report_formats: Optional[List[str]] = None


class ScheduleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    schedule_type: str
    schedule_expression: str
    timezone: str
    enabled: bool
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    run_count: int
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new schedule"""
    db_schedule = Schedule(
        name=schedule.name,
        description=schedule.description,
        schedule_type=ScheduleType(schedule.schedule_type),
        schedule_expression=schedule.schedule_expression,
        timezone=schedule.timezone,
        scan_config=schedule.scan_config,
        email_enabled=schedule.email_enabled,
        email_recipients=schedule.email_recipients,
        report_formats=schedule.report_formats or ["pdf"],
        created_by=current_user.username if current_user else "system",
    )
    
    # Calculate next run time
    from app.tasks.schedule_tasks import calculate_next_run
    db_schedule.next_run_at = calculate_next_run(db_schedule)
    
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    
    return ScheduleResponse(
        id=str(db_schedule.id),
        name=db_schedule.name,
        description=db_schedule.description,
        schedule_type=db_schedule.schedule_type.value,
        schedule_expression=db_schedule.schedule_expression,
        timezone=db_schedule.timezone,
        enabled=db_schedule.enabled,
        last_run_at=db_schedule.last_run_at,
        next_run_at=db_schedule.next_run_at,
        run_count=db_schedule.run_count,
        created_at=db_schedule.created_at,
    )


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    enabled: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all schedules"""
    query = db.query(Schedule)
    if enabled is not None:
        query = query.filter(Schedule.enabled == enabled)
    
    schedules = query.offset(skip).limit(limit).all()
    
    return [
        ScheduleResponse(
            id=str(s.id),
            name=s.name,
            description=s.description,
            schedule_type=s.schedule_type.value,
            schedule_expression=s.schedule_expression,
            timezone=s.timezone,
            enabled=s.enabled,
            last_run_at=s.last_run_at,
            next_run_at=s.next_run_at,
            run_count=s.run_count,
            created_at=s.created_at,
        )
        for s in schedules
    ]


@router.post("/{schedule_id}/enable")
async def enable_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """Enable a schedule"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.enabled = True
    db.commit()
    
    return {"message": "Schedule enabled", "schedule_id": schedule_id}


@router.post("/{schedule_id}/disable")
async def disable_schedule(schedule_id: str, db: Session = Depends(get_db)):
    """Disable a schedule"""
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    schedule.enabled = False
    db.commit()
    
    return {"message": "Schedule disabled", "schedule_id": schedule_id}
