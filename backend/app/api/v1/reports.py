"""
Report generation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.report import Report, ReportType, ReportFormat
from app.models.scan import Scan
from app.models.user import User
from app.services.report_generator import ReportGenerator
from sqlalchemy.orm import Session

router = APIRouter()


class ReportGenerateRequest(BaseModel):
    scan_id: str
    report_type: str  # executive, technical, compliance, full
    format: str  # pdf, html, json, word
    template: Optional[str] = None
    capture_screenshots: Optional[bool] = False  # Capture screenshots before generating


class ReportResponse(BaseModel):
    id: str
    scan_id: str
    name: str
    report_type: str
    format: str
    generated_at: str
    file_path: Optional[str] = None

    class Config:
        from_attributes = True


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a report for a scan"""
    # Get scan
    scan = db.query(Scan).filter(Scan.id == request.scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Generate report
    generator = ReportGenerator(request.scan_id)

    # Capture screenshots if requested
    if request.capture_screenshots:
        screenshot_result = generator.capture_screenshots_for_findings()

    result = generator.generate(
        report_type=ReportType(request.report_type),
        format=ReportFormat(request.format),
        use_ai=request.template == "ai_enhanced"
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Report generation failed"))

    # Create report record
    report = Report(
        scan_id=request.scan_id,
        name=f"{scan.name} - {request.report_type}",
        report_type=ReportType(request.report_type),
        format=ReportFormat(request.format),
        file_path=result.get("file_path"),
        file_size=result.get("file_size"),
        generated_by=current_user.username if current_user else "system",
        ai_enhanced=request.template == "ai_enhanced"
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return ReportResponse(
        id=str(report.id),
        scan_id=str(report.scan_id),
        name=report.name,
        report_type=report.report_type.value,
        format=report.format.value,
        generated_at=report.generated_at.isoformat(),
        file_path=report.file_path,
    )


@router.get("/{report_id}/download")
async def download_report(report_id: str, db: Session = Depends(get_db)):
    """Download generated report"""
    import os
    from pathlib import Path

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.file_path:
        raise HTTPException(status_code=404, detail="Report file not generated yet")

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file not found on disk")

    # Determine content type based on format
    content_types = {
        'pdf': 'application/pdf',
        'html': 'text/html',
        'json': 'application/json',
        'csv': 'text/csv',
        'word': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }

    format_str = report.format.value if hasattr(report.format, 'value') else str(report.format)
    content_type = content_types.get(format_str, 'application/octet-stream')

    # Generate safe filename
    safe_name = "".join(c for c in report.name if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_name}.{format_str}"

    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=filename
    )


@router.post("/{report_id}/email")
async def email_report(report_id: str, email_request: dict, db: Session = Depends(get_db)):
    """Email a report to specified recipients"""
    from app.services.email_service import EmailService

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    email = email_request.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="Email address required")

    try:
        email_service = EmailService()
        result = email_service.send_report(
            to_email=email,
            report_name=report.name,
            report_path=report.file_path
        )

        if result.get('success'):
            report.email_sent = True
            from datetime import datetime
            report.email_sent_at = datetime.utcnow()
            report.email_recipients = [email]
            db.commit()

            return {"message": "Report sent successfully"}
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to send email'))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{report_id}")
async def delete_report(report_id: str, db: Session = Depends(get_db)):
    """Delete a report"""
    import os
    from pathlib import Path

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Delete file from disk if exists
    if report.file_path:
        file_path = Path(report.file_path)
        if file_path.exists():
            try:
                os.remove(file_path)
            except Exception as e:
                pass  # Log but continue with DB deletion

    # Delete from database
    db.delete(report)
    db.commit()

    return {"message": "Report deleted successfully"}


@router.post("/{scan_id}/capture-screenshots")
async def capture_screenshots(scan_id: str, db: Session = Depends(get_db)):
    """Capture screenshots for all web-based findings in a scan"""
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    generator = ReportGenerator(scan_id)
    result = generator.capture_screenshots_for_findings()

    return {
        "message": f"Captured {result['captured']} screenshots",
        "captured": result['captured'],
        "failed": result['failed'],
        "total_web_findings": result['total_web_findings']
    }


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    scan_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List reports"""
    query = db.query(Report)
    if scan_id:
        query = query.filter(Report.scan_id == scan_id)
    
    reports = query.offset(skip).limit(limit).all()
    
    return [
        ReportResponse(
            id=str(r.id),
            scan_id=str(r.scan_id),
            name=r.name,
            report_type=r.report_type.value,
            format=r.format.value,
            generated_at=r.generated_at.isoformat(),
            file_path=r.file_path,
        )
        for r in reports
    ]
