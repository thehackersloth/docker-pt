"""
Natural language query interface for AI
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.ai_service import AIService
from app.core.database import get_db
from app.models.scan import Scan
from app.models.finding import Finding, FindingSeverity
from sqlalchemy.orm import Session

router = APIRouter()
ai_service = AIService()


class NaturalLanguageQuery(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    scan_id: Optional[str] = None


class NaturalLanguageResponse(BaseModel):
    answer: str
    confidence: float
    sources: list
    suggested_actions: list


@router.post("/query", response_model=NaturalLanguageResponse)
async def natural_language_query(
    request: NaturalLanguageQuery,
    db: Session = Depends(get_db)
):
    """Process natural language query using AI"""
    try:
        # Build context from database if scan_id provided
        context_parts = []
        
        if request.scan_id:
            scan = db.query(Scan).filter(Scan.id == request.scan_id).first()
            if scan:
                context_parts.append(f"Scan: {scan.name}")
                context_parts.append(f"Status: {scan.status.value}")
                context_parts.append(f"Findings: {scan.findings_count}")
                
                # Get findings
                findings = db.query(Finding).filter(Finding.scan_id == request.scan_id).limit(10).all()
                if findings:
                    context_parts.append("\nRecent Findings:")
                    for finding in findings:
                        context_parts.append(f"- {finding.severity.value.upper()}: {finding.title}")
        
        # Add custom context
        if request.context:
            for key, value in request.context.items():
                context_parts.append(f"{key}: {value}")
        
        context_str = "\n".join(context_parts) if context_parts else ""
        
        # Build prompt
        prompt = f"""
        You are a security expert assistant helping with penetration testing analysis.
        
        Context:
        {context_str}
        
        User Query: {request.query}
        
        Please provide:
        1. A clear, concise answer
        2. Relevant security insights
        3. Suggested actions if applicable
        4. Any relevant findings or recommendations
        
        Format your response as a helpful security analysis.
        """
        
        # Get AI response
        response = ai_service.generate_text(prompt)
        
        if not response:
            raise HTTPException(status_code=500, detail="AI service unavailable")
        
        # Parse response for suggested actions
        suggested_actions = []
        if "scan" in request.query.lower():
            suggested_actions.append("Create a new scan")
        if "finding" in request.query.lower() or "vulnerability" in request.query.lower():
            suggested_actions.append("View findings")
        if "report" in request.query.lower():
            suggested_actions.append("Generate report")
        
        return NaturalLanguageResponse(
            answer=response,
            confidence=0.85,  # Placeholder
            sources=[f"Scan {request.scan_id}"] if request.scan_id else [],
            suggested_actions=suggested_actions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_with_natural_language(
    query: str,
    scan_id: Optional[str] = None,
    finding_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Analyze scan or finding using natural language"""
    try:
        
        if finding_id:
            finding = db.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                raise HTTPException(status_code=404, detail="Finding not found")
            
            prompt = f"""
            Analyze this security finding:
            
            Title: {finding.title}
            Severity: {finding.severity.value}
            Description: {finding.description}
            Target: {finding.target}
            CVE: {finding.cve_id or 'None'}
            
            User Question: {query}
            
            Provide a detailed analysis addressing the user's question.
            """
        elif scan_id:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if not scan:
                raise HTTPException(status_code=404, detail="Scan not found")
            
            prompt = f"""
            Analyze this penetration test scan:
            
            Scan: {scan.name}
            Type: {scan.scan_type.value}
            Status: {scan.status.value}
            Findings: {scan.findings_count}
            Critical: {scan.critical_count}
            High: {scan.high_count}
            
            User Question: {query}
            
            Provide a detailed analysis addressing the user's question.
            """
        else:
            prompt = f"""
            Security Analysis Request:
            
            {query}
            
            Provide a comprehensive security analysis.
            """
        
        response = ai_service.generate_text(prompt)
        
        if not response:
            raise HTTPException(status_code=500, detail="AI service unavailable")
        
        return {
            "success": True,
            "analysis": response,
            "query": query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
