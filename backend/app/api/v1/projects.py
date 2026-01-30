"""
Project/Client/Engagement management API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.project import Project, Client, ProjectNote, ProjectStatus, EngagementType
from sqlalchemy.orm import Session

router = APIRouter()


# ============ Client Endpoints ============

class ClientCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None


class ClientResponse(BaseModel):
    id: str
    name: str
    industry: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    project_count: int = 0
    created_at: str

    class Config:
        from_attributes = True


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    """Create a new client"""
    db_client = Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)

    return ClientResponse(
        id=db_client.id,
        name=db_client.name,
        industry=db_client.industry,
        contact_name=db_client.contact_name,
        contact_email=db_client.contact_email,
        project_count=0,
        created_at=db_client.created_at.isoformat()
    )


@router.get("/clients", response_model=List[ClientResponse])
async def list_clients(db: Session = Depends(get_db)):
    """List all clients"""
    clients = db.query(Client).order_by(Client.name).all()
    return [
        ClientResponse(
            id=c.id,
            name=c.name,
            industry=c.industry,
            contact_name=c.contact_name,
            contact_email=c.contact_email,
            project_count=len(c.projects) if c.projects else 0,
            created_at=c.created_at.isoformat()
        )
        for c in clients
    ]


@router.delete("/clients/{client_id}")
async def delete_client(client_id: str, db: Session = Depends(get_db)):
    """Delete a client"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return {"message": "Client deleted"}


# ============ Project Endpoints ============

class ProjectCreate(BaseModel):
    name: str
    client_id: Optional[str] = None
    engagement_type: str
    description: Optional[str] = None
    scope: Optional[List[str]] = None
    out_of_scope: Optional[List[str]] = None
    rules_of_engagement: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    report_due_date: Optional[str] = None
    lead_tester: Optional[str] = None
    team_members: Optional[List[str]] = None
    compliance_frameworks: Optional[List[str]] = None
    emergency_contact: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    engagement_type: str
    status: str
    description: Optional[str] = None
    scope: Optional[List[str]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    compliance_frameworks: Optional[List[str]] = None
    created_at: str

    class Config:
        from_attributes = True


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project/engagement"""
    # Parse dates
    start_date = datetime.fromisoformat(project.start_date) if project.start_date else None
    end_date = datetime.fromisoformat(project.end_date) if project.end_date else None
    report_due = datetime.fromisoformat(project.report_due_date) if project.report_due_date else None

    db_project = Project(
        name=project.name,
        client_id=project.client_id,
        engagement_type=EngagementType(project.engagement_type),
        description=project.description,
        scope=project.scope,
        out_of_scope=project.out_of_scope,
        rules_of_engagement=project.rules_of_engagement,
        start_date=start_date,
        end_date=end_date,
        report_due_date=report_due,
        lead_tester=project.lead_tester,
        team_members=project.team_members,
        compliance_frameworks=project.compliance_frameworks,
        emergency_contact=project.emergency_contact
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    client_name = None
    if db_project.client_id:
        client = db.query(Client).filter(Client.id == db_project.client_id).first()
        client_name = client.name if client else None

    return ProjectResponse(
        id=db_project.id,
        name=db_project.name,
        client_id=db_project.client_id,
        client_name=client_name,
        engagement_type=db_project.engagement_type.value,
        status=db_project.status.value,
        description=db_project.description,
        scope=db_project.scope,
        start_date=db_project.start_date.isoformat() if db_project.start_date else None,
        end_date=db_project.end_date.isoformat() if db_project.end_date else None,
        compliance_frameworks=db_project.compliance_frameworks,
        created_at=db_project.created_at.isoformat()
    )


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all projects"""
    query = db.query(Project)

    if status:
        query = query.filter(Project.status == ProjectStatus(status))
    if client_id:
        query = query.filter(Project.client_id == client_id)

    projects = query.order_by(Project.created_at.desc()).all()

    results = []
    for p in projects:
        client_name = None
        if p.client_id:
            client = db.query(Client).filter(Client.id == p.client_id).first()
            client_name = client.name if client else None

        results.append(ProjectResponse(
            id=p.id,
            name=p.name,
            client_id=p.client_id,
            client_name=client_name,
            engagement_type=p.engagement_type.value,
            status=p.status.value,
            description=p.description,
            scope=p.scope,
            start_date=p.start_date.isoformat() if p.start_date else None,
            end_date=p.end_date.isoformat() if p.end_date else None,
            compliance_frameworks=p.compliance_frameworks,
            created_at=p.created_at.isoformat()
        ))

    return results


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a specific project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    client_name = None
    if project.client_id:
        client = db.query(Client).filter(Client.id == project.client_id).first()
        client_name = client.name if client else None

    return ProjectResponse(
        id=project.id,
        name=project.name,
        client_id=project.client_id,
        client_name=client_name,
        engagement_type=project.engagement_type.value,
        status=project.status.value,
        description=project.description,
        scope=project.scope,
        start_date=project.start_date.isoformat() if project.start_date else None,
        end_date=project.end_date.isoformat() if project.end_date else None,
        compliance_frameworks=project.compliance_frameworks,
        created_at=project.created_at.isoformat()
    )


@router.put("/{project_id}/status")
async def update_project_status(project_id: str, new_status: str, db: Session = Depends(get_db)):
    """Update project status"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectStatus(new_status)
    db.commit()
    return {"message": "Status updated", "status": new_status}


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}


# ============ Notes Endpoints ============

class NoteCreate(BaseModel):
    project_id: Optional[str] = None
    finding_id: Optional[str] = None
    scan_id: Optional[str] = None
    title: Optional[str] = None
    content: str
    note_type: Optional[str] = "general"
    is_pinned: Optional[bool] = False


class NoteResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    finding_id: Optional[str] = None
    scan_id: Optional[str] = None
    title: Optional[str] = None
    content: str
    note_type: str
    is_pinned: bool
    created_at: str
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(note: NoteCreate, db: Session = Depends(get_db)):
    """Create a new note"""
    db_note = ProjectNote(**note.model_dump())
    db.add(db_note)
    db.commit()
    db.refresh(db_note)

    return NoteResponse(
        id=db_note.id,
        project_id=db_note.project_id,
        finding_id=db_note.finding_id,
        scan_id=db_note.scan_id,
        title=db_note.title,
        content=db_note.content,
        note_type=db_note.note_type,
        is_pinned=db_note.is_pinned,
        created_at=db_note.created_at.isoformat(),
        created_by=db_note.created_by
    )


@router.get("/notes", response_model=List[NoteResponse])
async def list_notes(
    project_id: Optional[str] = None,
    finding_id: Optional[str] = None,
    scan_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List notes with optional filtering"""
    query = db.query(ProjectNote)

    if project_id:
        query = query.filter(ProjectNote.project_id == project_id)
    if finding_id:
        query = query.filter(ProjectNote.finding_id == finding_id)
    if scan_id:
        query = query.filter(ProjectNote.scan_id == scan_id)

    notes = query.order_by(ProjectNote.is_pinned.desc(), ProjectNote.created_at.desc()).all()

    return [
        NoteResponse(
            id=n.id,
            project_id=n.project_id,
            finding_id=n.finding_id,
            scan_id=n.scan_id,
            title=n.title,
            content=n.content,
            note_type=n.note_type,
            is_pinned=n.is_pinned,
            created_at=n.created_at.isoformat(),
            created_by=n.created_by
        )
        for n in notes
    ]


@router.delete("/notes/{note_id}")
async def delete_note(note_id: str, db: Session = Depends(get_db)):
    """Delete a note"""
    note = db.query(ProjectNote).filter(ProjectNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"message": "Note deleted"}
