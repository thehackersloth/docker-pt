"""
Report generation service
Generates PDF, HTML, JSON, CSV, and Word reports
Includes screenshots and evidence in reports
"""

import logging
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding, FindingSeverity
from app.models.report import Report, ReportType, ReportFormat
from app.services.ai_service import AIService
from app.services.report_templates import ReportTemplateGenerator, ReportTemplate
from app.services.evidence_collector import EvidenceCollector
import json
import csv

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate various report formats"""
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.db = SessionLocal()
        self.scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        self.ai_service = AIService()
        self.reports_dir = Path("/data/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, report_type: ReportType, format: ReportFormat, use_ai: bool = False, template: str = None) -> Dict[str, Any]:
        """Generate a report"""
        logger.info(f"Generating {report_type.value} report in {format.value} format")
        
        # Get findings
        findings = self.db.query(Finding).filter(Finding.scan_id == self.scan_id).all()
        
        # Get template if specified
        template_data = None
        if template:
            try:
                template_enum = ReportTemplate(template.lower())
                template_data = ReportTemplateGenerator.get_template(template_enum)
            except:
                pass
        
        # Generate based on format
        if format == ReportFormat.PDF:
            return self._generate_pdf(report_type, findings, use_ai)
        elif format == ReportFormat.HTML:
            return self._generate_html(report_type, findings, use_ai)
        elif format == ReportFormat.JSON:
            return self._generate_json(report_type, findings)
        elif format == ReportFormat.CSV:
            return self._generate_csv(report_type, findings)
        elif format == ReportFormat.WORD:
            return self._generate_word(report_type, findings, use_ai)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_pdf(self, report_type: ReportType, findings: List[Finding], use_ai: bool) -> Dict[str, Any]:
        """Generate PDF report with screenshots and evidence"""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_LEFT

            filename = f"report_{self.scan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = self.reports_dir / filename

            doc = SimpleDocTemplate(str(filepath), pagesize=letter)
            story = []
            styles = getSampleStyleSheet()

            # Custom styles
            finding_style = ParagraphStyle(
                'FindingStyle',
                parent=styles['Normal'],
                spaceBefore=6,
                spaceAfter=6
            )

            # Title
            title = Paragraph(f"<b>{self.scan.name} - {report_type.value.title()} Report</b>", styles['Title'])
            story.append(title)
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
            story.append(Spacer(1, 0.3*inch))

            # Executive Summary
            if report_type in [ReportType.EXECUTIVE, ReportType.FULL]:
                summary = self._generate_executive_summary(findings, use_ai)
                story.append(Paragraph("<b>Executive Summary</b>", styles['Heading1']))
                story.append(Paragraph(summary, styles['Normal']))
                story.append(Spacer(1, 0.2*inch))

            # Findings Summary Table
            story.append(Paragraph("<b>Findings Summary</b>", styles['Heading1']))
            data = [['Severity', 'Title', 'Target', 'Status']]
            for finding in findings:
                data.append([
                    finding.severity.value.upper(),
                    finding.title[:50],
                    finding.target[:30] if finding.target else 'N/A',
                    finding.status.value
                ])

            table = Table(data, colWidths=[1*inch, 3*inch, 2*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), '#4472C4'),
                ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), '#F2F2F2'),
                ('GRID', (0, 0), (-1, -1), 1, '#CCCCCC'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.3*inch))

            # Detailed Findings with Screenshots (for technical/full reports)
            if report_type in [ReportType.TECHNICAL, ReportType.FULL]:
                story.append(PageBreak())
                story.append(Paragraph("<b>Detailed Findings</b>", styles['Heading1']))
                story.append(Spacer(1, 0.2*inch))

                for i, finding in enumerate(findings, 1):
                    # Finding header
                    severity_color = {
                        'critical': '#dc3545',
                        'high': '#fd7e14',
                        'medium': '#ffc107',
                        'low': '#28a745',
                        'info': '#17a2b8'
                    }.get(finding.severity.value, '#6c757d')

                    story.append(Paragraph(
                        f"<b>{i}. {finding.title}</b>",
                        styles['Heading2']
                    ))

                    # Finding details
                    story.append(Paragraph(f"<b>Severity:</b> {finding.severity.value.upper()}", finding_style))
                    story.append(Paragraph(f"<b>Target:</b> {finding.target}", finding_style))
                    if finding.cve_id:
                        story.append(Paragraph(f"<b>CVE:</b> {finding.cve_id}", finding_style))
                    if finding.cvss_score:
                        story.append(Paragraph(f"<b>CVSS Score:</b> {finding.cvss_score}", finding_style))

                    story.append(Spacer(1, 0.1*inch))
                    story.append(Paragraph("<b>Description:</b>", finding_style))
                    story.append(Paragraph(finding.description or "No description available.", styles['Normal']))

                    if finding.remediation:
                        story.append(Spacer(1, 0.1*inch))
                        story.append(Paragraph("<b>Remediation:</b>", finding_style))
                        story.append(Paragraph(finding.remediation, styles['Normal']))

                    # Include web screenshot if available
                    screenshot_path = self._get_finding_screenshot(finding)
                    if screenshot_path and Path(screenshot_path).exists():
                        story.append(Spacer(1, 0.1*inch))
                        story.append(Paragraph("<b>Web Screenshot:</b>", finding_style))
                        try:
                            img = Image(screenshot_path, width=6*inch, height=4*inch)
                            img.hAlign = 'LEFT'
                            story.append(img)
                        except Exception as e:
                            logger.warning(f"Could not include web screenshot: {e}")

                    # Include terminal screenshot if available
                    terminal_path = self._get_terminal_screenshot(finding)
                    if terminal_path and Path(terminal_path).exists():
                        story.append(Spacer(1, 0.1*inch))
                        story.append(Paragraph("<b>Tool Output:</b>", finding_style))
                        try:
                            img = Image(terminal_path, width=6*inch, height=4*inch)
                            img.hAlign = 'LEFT'
                            story.append(img)
                        except Exception as e:
                            logger.warning(f"Could not include terminal screenshot: {e}")

                    story.append(Spacer(1, 0.3*inch))

            doc.build(story)

            return {
                "success": True,
                "file_path": str(filepath),
                "file_size": filepath.stat().st_size,
                "format": "pdf"
            }
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return {"success": False, "error": str(e)}

    def _get_finding_screenshot(self, finding: Finding) -> Optional[str]:
        """Get web screenshot path for a finding"""
        # Check if finding has evidence with screenshot
        if finding.evidence and isinstance(finding.evidence, dict):
            return finding.evidence.get('screenshot')

        # Check evidence directory for matching screenshots
        evidence_dir = Path(f"/data/evidence/{self.scan_id}")
        if evidence_dir.exists():
            for screenshot in evidence_dir.glob(f"screenshot_{finding.id}_*.png"):
                return str(screenshot)

        return None

    def _get_terminal_screenshot(self, finding: Finding) -> Optional[str]:
        """Get terminal screenshot path for a finding"""
        # Check if finding has evidence with terminal screenshot
        if finding.evidence and isinstance(finding.evidence, dict):
            return finding.evidence.get('terminal_screenshot')

        # Check evidence directory for matching terminal screenshots
        evidence_dir = Path(f"/data/evidence/{self.scan_id}")
        if evidence_dir.exists():
            for screenshot in evidence_dir.glob(f"terminal_{finding.id}_*.png"):
                return str(screenshot)

        return None

    def capture_screenshots_for_findings(self, include_terminal: bool = True) -> Dict[str, Any]:
        """Capture screenshots for all findings (web pages and terminal output)"""
        evidence_collector = EvidenceCollector(self.scan_id)
        findings = self.db.query(Finding).filter(Finding.scan_id == self.scan_id).all()

        web_captured = 0
        web_failed = 0
        terminal_captured = 0
        terminal_failed = 0

        for finding in findings:
            # Capture web screenshots
            if finding.target and finding.target.startswith(('http://', 'https://')):
                result = evidence_collector.capture_screenshot(finding.target, str(finding.id))
                if result:
                    finding.evidence = finding.evidence or {}
                    finding.evidence['screenshot'] = result
                    web_captured += 1
                else:
                    web_failed += 1

            # Capture terminal screenshots
            if include_terminal and finding.tool_output:
                tool_name = finding.tool or "Tool Output"
                result = evidence_collector.capture_terminal_screenshot(
                    str(finding.tool_output),
                    str(finding.id),
                    title=f"{tool_name} - {finding.title[:50]}"
                )
                if result:
                    finding.evidence = finding.evidence or {}
                    finding.evidence['terminal_screenshot'] = result
                    terminal_captured += 1
                else:
                    terminal_failed += 1

        self.db.commit()

        return {
            "web_captured": web_captured,
            "web_failed": web_failed,
            "terminal_captured": terminal_captured,
            "terminal_failed": terminal_failed,
            "total_web_findings": web_captured + web_failed,
            "total_terminal_findings": terminal_captured + terminal_failed
        }
    
    def _generate_html(self, report_type: ReportType, findings: List[Finding], use_ai: bool) -> Dict[str, Any]:
        """Generate HTML report with embedded screenshots"""
        try:
            filename = f"report_{self.scan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            filepath = self.reports_dir / filename

            html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.scan.name} - {report_type.value.title()} Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4472C4; padding-bottom: 10px; }}
        h2 {{ color: #4472C4; }}
        .finding {{ margin: 20px 0; padding: 20px; border-left: 4px solid #4472C4; background: #f9f9f9; border-radius: 0 8px 8px 0; }}
        .finding.critical {{ border-left-color: #dc3545; background: #fff5f5; }}
        .finding.high {{ border-left-color: #fd7e14; background: #fff8f0; }}
        .finding.medium {{ border-left-color: #ffc107; background: #fffef0; }}
        .finding.low {{ border-left-color: #28a745; background: #f0fff4; }}
        .finding.info {{ border-left-color: #17a2b8; background: #f0f9ff; }}
        .severity-badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; color: white; font-weight: bold; font-size: 12px; }}
        .severity-critical {{ background: #dc3545; }}
        .severity-high {{ background: #fd7e14; }}
        .severity-medium {{ background: #ffc107; color: #333; }}
        .severity-low {{ background: #28a745; }}
        .severity-info {{ background: #17a2b8; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #4472C4; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .screenshot {{ max-width: 100%; margin: 15px 0; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ flex: 1; padding: 20px; background: #f0f0f0; border-radius: 8px; text-align: center; }}
        .stat-card.critical {{ background: #dc3545; color: white; }}
        .stat-card.high {{ background: #fd7e14; color: white; }}
        .stat-card.medium {{ background: #ffc107; }}
        .stat-card.low {{ background: #28a745; color: white; }}
        .stat-value {{ font-size: 36px; font-weight: bold; }}
        .stat-label {{ font-size: 14px; margin-top: 5px; }}
        .remediation {{ background: #e8f5e9; padding: 15px; border-radius: 8px; margin-top: 10px; }}
        .meta {{ color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{self.scan.name}</h1>
        <h2>{report_type.value.title()} Report</h2>
        <p class="meta">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{len(findings)}</div>
                <div class="stat-label">Total Findings</div>
            </div>
            <div class="stat-card critical">
                <div class="stat-value">{sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-card high">
                <div class="stat-value">{sum(1 for f in findings if f.severity == FindingSeverity.HIGH)}</div>
                <div class="stat-label">High</div>
            </div>
            <div class="stat-card medium">
                <div class="stat-value">{sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)}</div>
                <div class="stat-label">Medium</div>
            </div>
            <div class="stat-card low">
                <div class="stat-value">{sum(1 for f in findings if f.severity == FindingSeverity.LOW)}</div>
                <div class="stat-label">Low</div>
            </div>
        </div>

        <h3>Findings Summary</h3>
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Title</th>
                    <th>Target</th>
                    <th>CVE</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""
            for finding in findings:
                html += f"""
                <tr>
                    <td><span class="severity-badge severity-{finding.severity.value}">{finding.severity.value.upper()}</span></td>
                    <td>{finding.title}</td>
                    <td>{finding.target}</td>
                    <td>{finding.cve_id or '-'}</td>
                    <td>{finding.status.value}</td>
                </tr>
"""
            html += """
            </tbody>
        </table>

        <h3>Detailed Findings</h3>
"""
            for i, finding in enumerate(findings, 1):
                severity_class = finding.severity.value
                screenshot_html = ""
                terminal_html = ""

                # Get web screenshot and embed as base64
                screenshot_path = self._get_finding_screenshot(finding)
                if screenshot_path and Path(screenshot_path).exists():
                    try:
                        with open(screenshot_path, 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            screenshot_html = f'<p><strong>Web Screenshot:</strong></p><img class="screenshot" src="data:image/png;base64,{img_data}" alt="Web screenshot evidence" />'
                    except Exception as e:
                        logger.warning(f"Could not embed web screenshot: {e}")

                # Get terminal screenshot and embed as base64
                terminal_path = self._get_terminal_screenshot(finding)
                if terminal_path and Path(terminal_path).exists():
                    try:
                        with open(terminal_path, 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            terminal_html = f'<p><strong>Tool Output:</strong></p><img class="screenshot" src="data:image/png;base64,{img_data}" alt="Terminal output evidence" />'
                    except Exception as e:
                        logger.warning(f"Could not embed terminal screenshot: {e}")

                remediation_html = ""
                if finding.remediation:
                    remediation_html = f'<div class="remediation"><strong>Remediation:</strong><br>{finding.remediation}</div>'

                html += f"""
        <div class="finding {severity_class}">
            <h4>{i}. {finding.title}</h4>
            <p><span class="severity-badge severity-{severity_class}">{finding.severity.value.upper()}</span></p>
            <p><strong>Target:</strong> {finding.target}</p>
            {f'<p><strong>CVE:</strong> {finding.cve_id}</p>' if finding.cve_id else ''}
            {f'<p><strong>CVSS Score:</strong> {finding.cvss_score}</p>' if finding.cvss_score else ''}
            <p><strong>Description:</strong><br>{finding.description}</p>
            {remediation_html}
            {screenshot_html}
            {terminal_html}
        </div>
"""

            html += """
    </div>
</body>
</html>
"""

            filepath.write_text(html)

            return {
                "success": True,
                "file_path": str(filepath),
                "file_size": filepath.stat().st_size,
                "format": "html"
            }
        except Exception as e:
            logger.error(f"HTML generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_json(self, report_type: ReportType, findings: List[Finding]) -> Dict[str, Any]:
        """Generate JSON report"""
        try:
            filename = f"report_{self.scan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.reports_dir / filename
            
            report_data = {
                "scan_id": self.scan_id,
                "scan_name": self.scan.name,
                "report_type": report_type.value,
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_findings": len(findings),
                    "critical": sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL),
                    "high": sum(1 for f in findings if f.severity == FindingSeverity.HIGH),
                    "medium": sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM),
                    "low": sum(1 for f in findings if f.severity == FindingSeverity.LOW),
                },
                "findings": [
                    {
                        "id": str(f.id),
                        "title": f.title,
                        "severity": f.severity.value,
                        "status": f.status.value,
                        "target": f.target,
                        "description": f.description,
                        "cve_id": f.cve_id,
                        "cvss_score": f.cvss_score,
                    }
                    for f in findings
                ]
            }
            
            filepath.write_text(json.dumps(report_data, indent=2))
            
            return {
                "success": True,
                "file_path": str(filepath),
                "file_size": filepath.stat().st_size,
                "format": "json"
            }
        except Exception as e:
            logger.error(f"JSON generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_csv(self, report_type: ReportType, findings: List[Finding]) -> Dict[str, Any]:
        """Generate CSV report"""
        try:
            filename = f"report_{self.scan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = self.reports_dir / filename
            
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['ID', 'Title', 'Severity', 'Status', 'Target', 'Description', 'CVE', 'CVSS'])
                
                for finding in findings:
                    writer.writerow([
                        str(finding.id),
                        finding.title,
                        finding.severity.value,
                        finding.status.value,
                        finding.target,
                        finding.description,
                        finding.cve_id or '',
                        finding.cvss_score or '',
                    ])
            
            return {
                "success": True,
                "file_path": str(filepath),
                "file_size": filepath.stat().st_size,
                "format": "csv"
            }
        except Exception as e:
            logger.error(f"CSV generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_word(self, report_type: ReportType, findings: List[Finding], use_ai: bool) -> Dict[str, Any]:
        """Generate Word document report"""
        # For now, generate HTML that can be opened in Word
        return self._generate_html(report_type, findings, use_ai)
    
    def _generate_executive_summary(self, findings: List[Finding], use_ai: bool) -> str:
        """Generate executive summary"""
        if use_ai:
            prompt = f"""
            Generate an executive summary for a penetration test report.
            
            Total Findings: {len(findings)}
            Critical: {sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)}
            High: {sum(1 for f in findings if f.severity == FindingSeverity.HIGH)}
            Medium: {sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)}
            Low: {sum(1 for f in findings if f.severity == FindingSeverity.LOW)}
            
            Provide a concise executive summary suitable for C-level executives.
            """
            result = self.ai_service.generate_text(prompt)
            return result or "Executive summary generation failed."
        else:
            return f"""
            This penetration test identified {len(findings)} security findings across the target environment.
            Of these, {sum(1 for f in findings if f.severity == FindingSeverity.CRITICAL)} are critical,
            {sum(1 for f in findings if f.severity == FindingSeverity.HIGH)} are high severity,
            {sum(1 for f in findings if f.severity == FindingSeverity.MEDIUM)} are medium severity,
            and {sum(1 for f in findings if f.severity == FindingSeverity.LOW)} are low severity.
            Immediate remediation is recommended for critical and high severity findings.
            """
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'db'):
            self.db.close()
