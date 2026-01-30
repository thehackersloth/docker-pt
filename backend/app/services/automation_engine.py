"""
Full Automation Engine - Automates entire pentesting workflow
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus, ScanType
from app.models.finding import Finding, FindingSeverity, FindingStatus
from app.models.asset import Asset, AssetType
from app.services.methodology_service import MethodologyService
from app.services.scan_engine import ScanEngine
from app.services.ai_service import AIService
from app.services.result_aggregator import ResultAggregator
from app.services.tool_runners.nmap_runner import NmapRunner
from app.services.tool_runners.sqlmap_runner import SQLMapRunner
from app.services.tool_runners.bloodhound_runner import BloodHoundRunner
from app.services.tool_runners.metasploit_runner import MetasploitRunner
from app.services.tool_runners.crackmapexec_runner import CrackMapExecRunner
from app.services.tool_runners.impacket_runner import ImpacketRunner
import asyncio

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Full automation engine for pentesting"""
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.db = SessionLocal()
        self.scan = self.db.query(Scan).filter(Scan.id == scan_id).first()
        self.methodology_service = MethodologyService()
        self.scan_engine = ScanEngine(scan_id)
        self.ai_service = AIService()
        self.result_aggregator = ResultAggregator(scan_id)
        
    def automate_full_workflow(self) -> Dict[str, Any]:
        """Automate the entire pentesting workflow"""
        try:
            # Update scan status
            self.scan.status = ScanStatus.RUNNING
            self.db.commit()
            
            # Get methodology phases
            phases = self.methodology_service.get_scan_phases(self.scan.scan_type)
            
            all_findings = []
            all_assets = []
            
            # Execute each phase automatically
            for phase in phases:
                logger.info(f"Automating phase: {phase['phase']}")
                
                phase_results = self._automate_phase(phase)
                
                if phase_results:
                    all_findings.extend(phase_results.get('findings', []))
                    all_assets.extend(phase_results.get('assets', []))
                    
                    # Auto-exploit if critical/high findings
                    if phase_results.get('auto_exploit', False):
                        exploit_results = self._auto_exploit_findings(phase_results['findings'])
                        all_findings.extend(exploit_results.get('findings', []))
            
            # Auto-analyze all findings
            analyzed_findings = self._auto_analyze_findings(all_findings)
            
            # Auto-generate report
            report = self._auto_generate_report(analyzed_findings)
            
            # Auto-suggest next steps
            next_steps = self._auto_suggest_next_steps(analyzed_findings, all_assets)
            
            # Update scan status
            self.scan.status = ScanStatus.COMPLETED
            self.scan.updated_at = datetime.utcnow()
            self.db.commit()
            
            # Learn from scan results automatically
            try:
                from app.services.continuous_learning import ContinuousLearningService
                learning_service = ContinuousLearningService()
                learning_service.learn_from_scan_results(self.scan_id)
            except Exception as e:
                logger.warning(f"Continuous learning failed: {e}")
            
            return {
                "scan_id": self.scan_id,
                "status": "completed",
                "phases_executed": len(phases),
                "findings_count": len(analyzed_findings),
                "assets_discovered": len(all_assets),
                "report": report,
                "next_steps": next_steps
            }
            
        except Exception as e:
            logger.error(f"Automation failed: {e}", exc_info=True)
            self.scan.status = ScanStatus.FAILED
            self.db.commit()
            raise
    
    def _automate_phase(self, phase: Dict[str, Any]) -> Dict[str, Any]:
        """Automate a single phase"""
        findings = []
        assets = []
        auto_exploit = False
        
        # Get tools for this phase
        tools = phase.get('tools', []) + phase.get('additional_tools', [])
        
        for tool in tools:
            try:
                # Auto-select tool runner
                runner = self._get_tool_runner(tool)
                if not runner:
                    continue
                
                # Auto-generate command
                command = self.methodology_service.get_tool_command(
                    tool,
                    phase['phase'],
                    self.scan.targets[0] if self.scan.targets else ""
                )
                
                # Auto-execute tool
                logger.info(f"Auto-executing {tool} for phase {phase['phase']}")
                results = runner.run(self.scan.targets, {
                    'auto_mode': True,
                    'command': command,
                    'phase': phase['phase']
                })
                
                # Auto-parse results
                parsed = self.result_aggregator.aggregate_tool_results(tool, results)
                
                # Auto-create findings
                phase_findings = self._auto_create_findings(parsed, tool, phase)
                findings.extend(phase_findings)
                
                # Auto-discover assets
                phase_assets = self._auto_discover_assets(parsed, tool)
                assets.extend(phase_assets)
                
                # Check if we should auto-exploit
                critical_findings = [f for f in phase_findings if f.severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH]]
                if critical_findings:
                    auto_exploit = True
                
            except Exception as e:
                logger.error(f"Tool {tool} automation failed: {e}")
                continue
        
        return {
            "phase": phase['phase'],
            "findings": findings,
            "assets": assets,
            "auto_exploit": auto_exploit
        }
    
    def _get_tool_runner(self, tool: str):
        """Auto-select tool runner"""
        runners = {
            'nmap': NmapRunner,
            'sqlmap': SQLMapRunner,
            'bloodhound': BloodHoundRunner,
            'metasploit': MetasploitRunner,
            'crackmapexec': CrackMapExecRunner,
            'impacket': ImpacketRunner
        }
        
        runner_class = runners.get(tool.lower())
        if runner_class:
            return runner_class(self.scan_id)
        return None
    
    def _auto_create_findings(self, parsed_results: Dict[str, Any], tool: str, phase: Dict[str, Any]) -> List[Finding]:
        """Automatically create findings from results"""
        findings = []
        
        # Extract vulnerabilities from results
        vulnerabilities = parsed_results.get('vulnerabilities', [])
        for vuln in vulnerabilities:
            # Auto-determine severity
            severity = self._auto_determine_severity(vuln, tool)
            
            # Auto-generate title
            title = self._auto_generate_finding_title(vuln, tool)
            
            # Auto-generate description
            description = self._auto_generate_finding_description(vuln, tool, phase)
            
            finding = Finding(
                scan_id=self.scan_id,
                title=title,
                description=description,
                severity=severity,
                status=FindingStatus.OPEN,
                target=vuln.get('target', self.scan.targets[0] if self.scan.targets else ''),
                cve_id=vuln.get('cve'),
                created_at=datetime.utcnow()
            )
            
            self.db.add(finding)
            findings.append(finding)
        
        self.db.commit()
        return findings
    
    def _auto_determine_severity(self, vuln: Dict[str, Any], tool: str) -> FindingSeverity:
        """Automatically determine finding severity"""
        # Use AI to determine severity if available
        try:
            severity_text = self.ai_service.analyze_vulnerability(
                vuln.get('description', ''),
                tool
            )
            
            severity_map = {
                'critical': FindingSeverity.CRITICAL,
                'high': FindingSeverity.HIGH,
                'medium': FindingSeverity.MEDIUM,
                'low': FindingSeverity.LOW,
                'info': FindingSeverity.INFO
            }
            
            for key, value in severity_map.items():
                if key in severity_text.lower():
                    return value
        except:
            pass
        
        # Fallback to rule-based
        if 'critical' in str(vuln).lower() or 'rce' in str(vuln).lower():
            return FindingSeverity.CRITICAL
        elif 'high' in str(vuln).lower() or 'sqli' in str(vuln).lower():
            return FindingSeverity.HIGH
        elif 'medium' in str(vuln).lower():
            return FindingSeverity.MEDIUM
        else:
            return FindingSeverity.LOW
    
    def _auto_generate_finding_title(self, vuln: Dict[str, Any], tool: str) -> str:
        """Automatically generate finding title"""
        if vuln.get('title'):
            return vuln['title']
        if vuln.get('cve'):
            return f"{vuln['cve']} - {tool} detection"
        return f"Vulnerability detected by {tool}"
    
    def _auto_generate_finding_description(self, vuln: Dict[str, Any], tool: str, phase: Dict[str, Any]) -> str:
        """Automatically generate finding description"""
        description = f"Vulnerability detected during {phase['phase']} phase using {tool}.\n\n"
        description += f"Details: {vuln.get('description', 'No additional details available')}\n\n"
        
        if vuln.get('cve'):
            description += f"CVE: {vuln['cve']}\n"
        
        # Add methodology context
        techniques = phase.get('techniques', [])
        if techniques:
            description += f"\nRelevant techniques: {', '.join(techniques[:3])}"
        
        return description
    
    def _auto_discover_assets(self, parsed_results: Dict[str, Any], tool: str) -> List[Asset]:
        """Automatically discover assets"""
        assets = []
        
        hosts = parsed_results.get('hosts', [])
        for host in hosts:
            # Check if asset already exists
            existing = self.db.query(Asset).filter(
                Asset.scan_id == self.scan_id,
                Asset.ip_address == host.get('ip')
            ).first()
            
            if existing:
                continue
            
            asset = Asset(
                scan_id=self.scan_id,
                ip_address=host.get('ip', ''),
                hostname=host.get('hostname'),
                asset_type=AssetType.HOST,
                discovered_by=tool,
                created_at=datetime.utcnow()
            )
            
            self.db.add(asset)
            assets.append(asset)
        
        self.db.commit()
        return assets
    
    def _auto_exploit_findings(self, findings: List[Finding]) -> Dict[str, Any]:
        """Automatically attempt exploitation"""
        exploit_results = {
            "findings": [],
            "exploited": []
        }
        
        critical_findings = [f for f in findings if f.severity in [FindingSeverity.CRITICAL, FindingSeverity.HIGH]]
        
        for finding in critical_findings:
            try:
                # Get exploitation workflow
                workflow = self.methodology_service.get_exploitation_workflow(finding)
                
                if not workflow:
                    continue
                
                # Auto-select exploit tool
                exploit_tool = workflow.get('recommended_tools', [])
                if not exploit_tool:
                    continue
                
                # Attempt exploitation
                logger.info(f"Auto-exploiting finding: {finding.title}")
                exploit_result = self._attempt_exploitation(finding, exploit_tool[0])
                
                if exploit_result.get('success'):
                    # Create exploitation finding
                    exploit_finding = Finding(
                        scan_id=self.scan_id,
                        title=f"Exploitation successful: {finding.title}",
                        description=f"Successfully exploited {finding.title}. {exploit_result.get('details', '')}",
                        severity=FindingSeverity.CRITICAL,
                        status=FindingStatus.CONFIRMED,
                        target=finding.target,
                        created_at=datetime.utcnow()
                    )
                    
                    self.db.add(exploit_finding)
                    exploit_results["findings"].append(exploit_finding)
                    exploit_results["exploited"].append(finding.id)
                    
                    # Update original finding
                    finding.status = FindingStatus.CONFIRMED
                
            except Exception as e:
                logger.error(f"Auto-exploitation failed for {finding.id}: {e}")
                continue
        
        self.db.commit()
        return exploit_results
    
    def _attempt_exploitation(self, finding: Finding, tool: str) -> Dict[str, Any]:
        """Attempt to exploit a finding"""
        try:
            if tool.lower() == 'metasploit':
                runner = MetasploitRunner(self.scan_id)
                # Auto-generate exploit module
                exploit_module = self._auto_generate_exploit_module(finding)
                
                result = runner.run([finding.target], {
                    'module': exploit_module,
                    'auto_exploit': True
                })
                
                return {
                    "success": result.get('success', False),
                    "details": result.get('output', '')
                }
            
            # Add other exploit tools as needed
            return {"success": False, "details": "Tool not implemented"}
            
        except Exception as e:
            logger.error(f"Exploitation attempt failed: {e}")
            return {"success": False, "details": str(e)}
    
    def _auto_generate_exploit_module(self, finding: Finding) -> str:
        """Auto-generate Metasploit exploit module using AI"""
        try:
            module_code = self.ai_service.generate_metasploit_module(
                finding.title,
                finding.description,
                finding.target
            )
            return module_code
        except:
            # Fallback to generic module
            return f"exploit/windows/smb/ms17_010_eternalblue"
    
    def _auto_analyze_findings(self, findings: List[Finding]) -> List[Finding]:
        """Automatically analyze findings using AI"""
        analyzed = []
        
        for finding in findings:
            try:
                # AI analysis
                analysis = self.ai_service.analyze_vulnerability(
                    finding.description,
                    "automated"
                )
                
                # Update finding with analysis
                finding.description += f"\n\nAI Analysis: {analysis}"
                
                # Auto-detect false positives
                if 'false positive' in analysis.lower() or 'not vulnerable' in analysis.lower():
                    finding.status = FindingStatus.FALSE_POSITIVE
                
                analyzed.append(finding)
                
            except Exception as e:
                logger.error(f"AI analysis failed for {finding.id}: {e}")
                analyzed.append(finding)
        
        self.db.commit()
        return analyzed
    
    def _auto_generate_report(self, findings: List[Finding]) -> Dict[str, Any]:
        """Automatically generate report"""
        from app.services.report_generator import ReportGenerator
        from app.models.report import ReportType, ReportFormat

        try:
            generator = ReportGenerator(self.scan_id)
            report = generator.generate(
                report_type=ReportType.EXECUTIVE,
                format=ReportFormat.PDF,
                use_ai=True
            )
            
            return {
                "report_id": report.get('id'),
                "format": "pdf",
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Auto-report generation failed: {e}")
            return {"error": str(e)}
    
    def _auto_suggest_next_steps(self, findings: List[Finding], assets: List[Asset]) -> List[Dict[str, Any]]:
        """Automatically suggest next steps"""
        next_steps = []
        
        # Analyze findings to suggest next steps
        critical_count = len([f for f in findings if f.severity == FindingSeverity.CRITICAL])
        high_count = len([f for f in findings if f.severity == FindingSeverity.HIGH])
        
        if critical_count > 0:
            next_steps.append({
                "priority": "high",
                "action": "Immediate remediation required",
                "description": f"{critical_count} critical vulnerabilities found",
                "recommended_tools": ["metasploit", "exploitdb"]
            })
        
        if high_count > 0:
            next_steps.append({
                "priority": "medium",
                "action": "Schedule remediation",
                "description": f"{high_count} high severity vulnerabilities found",
                "recommended_tools": ["patch management"]
            })
        
        # Suggest lateral movement if AD scan
        if self.scan.scan_type == ScanType.AD and assets:
            next_steps.append({
                "priority": "medium",
                "action": "Lateral movement assessment",
                "description": f"{len(assets)} assets discovered, assess lateral movement paths",
                "recommended_tools": ["bloodhound", "crackmapexec", "impacket"]
            })
        
        # Use AI to generate additional suggestions
        try:
            # Create a simple suggestion based on findings
            finding_titles = [f.title for f in findings[:10]]
            if finding_titles:
                next_steps.append({
                    "priority": "low",
                    "action": "Review findings",
                    "description": f"Review {len(finding_titles)} findings for additional context",
                    "recommended_tools": []
                })
        except:
            pass
        
        return next_steps
