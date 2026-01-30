"""
PDF upload endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import List
import shutil
from pathlib import Path
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.services.pdf_reader import PDFReader
from app.services.continuous_learning import ContinuousLearningService
from datetime import datetime
import hashlib
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# PDF storage directory
PDF_STORAGE = Path("/data/methodologies")
PDF_STORAGE.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    auto_learn: bool = True
):
    """Upload PDF for methodology extraction"""
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Validate file size (max 100MB)
    file_content = await file.read()
    if len(file_content) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 100MB limit"
        )
    
    try:
        # Generate unique filename
        file_hash = hashlib.md5(file_content).hexdigest()
        filename = f"{file_hash}_{file.filename}"
        filepath = PDF_STORAGE / filename
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        # Extract methodology
        pdf_reader = PDFReader()
        methodology = pdf_reader.extract_methodology(str(filepath))
        
        # Learn from PDF if enabled
        learned = {}
        if auto_learn:
            learning_service = ContinuousLearningService()
            learned = learning_service.learn_from_pdf(str(filepath))
        
        return {
            "success": True,
            "filename": filename,
            "original_name": file.filename,
            "size": len(file_content),
            "methodology": {
                "phases": len(methodology.get("phases", [])),
                "tools": len(methodology.get("tools", [])),
                "techniques": len(methodology.get("techniques", []))
            },
            "learned": learned
        }
        
    except Exception as e:
        logger.error(f"PDF upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/list")
async def list_uploaded_pdfs(
    current_user: User = Depends(get_current_user)
):
    """List all uploaded PDFs"""
    pdfs = []
    
    for pdf_file in PDF_STORAGE.glob("*.pdf"):
        pdf_reader = PDFReader()
        methodology = pdf_reader.extract_methodology(str(pdf_file))
        
        pdfs.append({
            "filename": pdf_file.name,
            "size": pdf_file.stat().st_size,
            "uploaded_at": datetime.fromtimestamp(pdf_file.stat().st_mtime).isoformat(),
            "methodology": {
                "phases": len(methodology.get("phases", [])),
                "tools": len(methodology.get("tools", [])),
                "techniques": len(methodology.get("techniques", []))
            }
        })
    
    return {"pdfs": pdfs}


@router.delete("/{filename}")
async def delete_pdf(
    filename: str,
    current_user: User = Depends(require_admin)
):
    """Delete uploaded PDF"""
    filepath = PDF_STORAGE / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    
    try:
        filepath.unlink()
        return {"success": True, "message": f"PDF {filename} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@router.post("/{filename}/relearn")
async def relearn_pdf(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Re-learn from a PDF"""
    filepath = PDF_STORAGE / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    
    learning_service = ContinuousLearningService()
    learned = learning_service.learn_from_pdf(str(filepath))
    
    return {
        "success": True,
        "filename": filename,
        "learned": learned
    }
