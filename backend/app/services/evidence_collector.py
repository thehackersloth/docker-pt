"""
Evidence collection service (screenshots, pcaps, logs, terminal captures)
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.database import SessionLocal
from app.models.scan import Scan
from app.models.finding import Finding
import textwrap

logger = logging.getLogger(__name__)


class EvidenceCollector:
    """Collect evidence for findings"""
    
    def __init__(self, scan_id: str):
        self.scan_id = scan_id
        self.evidence_dir = Path(f"/data/evidence/{scan_id}")
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
    
    def capture_screenshot(self, url: str, finding_id: str) -> Optional[str]:
        """Capture screenshot of a web page"""
        try:
            # Use headless browser (requires selenium/chrome)
            screenshot_file = self.evidence_dir / f"screenshot_{finding_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            # For now, use wkhtmltoimage or similar
            # In production, use Selenium with headless Chrome
            cmd = ['wkhtmltoimage', '--width', '1920', url, str(screenshot_file)]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            process.communicate()
            
            if screenshot_file.exists():
                return str(screenshot_file)
            
            return None
            
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def capture_pcap(self, interface: str, duration: int = 60, finding_id: str = None) -> Optional[str]:
        """Capture network traffic (pcap)"""
        try:
            pcap_file = self.evidence_dir / f"capture_{finding_id or 'general'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pcap"
            
            cmd = ['tcpdump', '-i', interface, '-w', str(pcap_file), '-G', str(duration)]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            process.communicate(timeout=duration + 5)
            
            if pcap_file.exists():
                return str(pcap_file)
            
            return None
            
        except Exception as e:
            logger.error(f"PCAP capture failed: {e}")
            return None
    
    def save_logs(self, logs: str, finding_id: str, log_type: str = "tool_output") -> Optional[str]:
        """Save logs as evidence"""
        try:
            log_file = self.evidence_dir / f"{log_type}_{finding_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            log_file.write_text(logs)
            return str(log_file)
        except Exception as e:
            logger.error(f"Log save failed: {e}")
            return None

    def capture_terminal_screenshot(self, output: str, finding_id: str, title: str = None) -> Optional[str]:
        """Convert terminal/command output to an image screenshot"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            screenshot_file = self.evidence_dir / f"terminal_{finding_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            # Terminal styling
            bg_color = (30, 30, 30)  # Dark terminal background
            text_color = (0, 255, 0)  # Green terminal text
            title_color = (255, 255, 255)  # White title
            border_color = (80, 80, 80)  # Gray border

            # Try to use a monospace font
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
                title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 16)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono.ttf", 14)
                    title_font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf", 16)
                except:
                    font = ImageFont.load_default()
                    title_font = font

            # Clean and wrap text
            lines = output.strip().split('\n')
            # Limit output length for image
            max_lines = 60
            if len(lines) > max_lines:
                lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"]

            # Wrap long lines
            wrapped_lines = []
            max_width = 120  # characters
            for line in lines:
                if len(line) > max_width:
                    wrapped_lines.extend(textwrap.wrap(line, max_width) or [''])
                else:
                    wrapped_lines.append(line)

            # Calculate image size
            char_width = 8
            char_height = 18
            padding = 20
            title_height = 40 if title else 0

            img_width = min(max_width * char_width + padding * 2, 1200)
            img_height = len(wrapped_lines) * char_height + padding * 2 + title_height

            # Create image
            img = Image.new('RGB', (img_width, img_height), bg_color)
            draw = ImageDraw.Draw(img)

            # Draw border
            draw.rectangle([0, 0, img_width - 1, img_height - 1], outline=border_color, width=2)

            # Draw title bar if provided
            y_offset = padding
            if title:
                draw.rectangle([0, 0, img_width, title_height], fill=(50, 50, 50))
                draw.text((padding, 10), f"$ {title}", fill=title_color, font=title_font)
                y_offset = title_height + 10

            # Draw terminal output
            for i, line in enumerate(wrapped_lines):
                # Color coding for common patterns
                line_color = text_color
                if line.startswith('[+]') or 'SUCCESS' in line.upper():
                    line_color = (0, 255, 0)  # Green
                elif line.startswith('[-]') or 'ERROR' in line.upper() or 'FAIL' in line.upper():
                    line_color = (255, 80, 80)  # Red
                elif line.startswith('[*]') or line.startswith('[!]'):
                    line_color = (255, 255, 0)  # Yellow
                elif line.startswith('CRITICAL') or 'VULN' in line.upper():
                    line_color = (255, 0, 0)  # Bright red
                elif 'PORT' in line.upper() and 'OPEN' in line.upper():
                    line_color = (0, 255, 255)  # Cyan

                draw.text((padding, y_offset + i * char_height), line, fill=line_color, font=font)

            img.save(str(screenshot_file), 'PNG')
            return str(screenshot_file)

        except ImportError:
            logger.warning("PIL/Pillow not installed, falling back to text file")
            return self.save_logs(output, finding_id, "terminal_output")
        except Exception as e:
            logger.error(f"Terminal screenshot capture failed: {e}")
            return None

    def capture_tool_output_screenshot(self, tool_name: str, command: str, output: str, finding_id: str) -> Optional[str]:
        """Capture tool command and output as a terminal screenshot"""
        formatted_output = f"Command: {command}\n{'=' * 80}\n\n{output}"
        return self.capture_terminal_screenshot(formatted_output, finding_id, title=tool_name)
    
    def collect_finding_evidence(self, finding_id: str, evidence_types: List[str]) -> Dict[str, Any]:
        """Collect evidence for a finding"""
        db = SessionLocal()
        try:
            finding = db.query(Finding).filter(Finding.id == finding_id).first()
            if not finding:
                return {"error": "Finding not found"}

            evidence = finding.evidence or {}

            # Web screenshot
            if "screenshot" in evidence_types and finding.target and finding.target.startswith("http"):
                screenshot = self.capture_screenshot(finding.target, finding_id)
                if screenshot:
                    evidence["screenshot"] = screenshot

            # Terminal/tool output screenshot
            if "terminal" in evidence_types and finding.tool_output:
                tool_name = finding.tool or "Tool Output"
                terminal_screenshot = self.capture_terminal_screenshot(
                    str(finding.tool_output),
                    finding_id,
                    title=f"{tool_name} - {finding.title[:50]}"
                )
                if terminal_screenshot:
                    evidence["terminal_screenshot"] = terminal_screenshot

            # PCAP capture
            if "pcap" in evidence_types:
                pcap = self.capture_pcap("eth0", 60, finding_id)
                if pcap:
                    evidence["pcap"] = pcap

            # Raw log files
            if "logs" in evidence_types and finding.tool_output:
                log_file = self.save_logs(str(finding.tool_output), finding_id)
                if log_file:
                    evidence["logs"] = log_file

            # Update finding with evidence
            if evidence:
                finding.evidence = evidence
                db.commit()

            return {
                "success": True,
                "finding_id": finding_id,
                "evidence": evidence
            }

        except Exception as e:
            logger.error(f"Evidence collection failed: {e}")
            return {"error": str(e), "success": False}
        finally:
            db.close()

    def capture_all_terminal_screenshots(self, scan_id: str) -> Dict[str, Any]:
        """Capture terminal screenshots for all findings with tool output"""
        db = SessionLocal()
        try:
            findings = db.query(Finding).filter(Finding.scan_id == scan_id).all()

            captured = 0
            failed = 0

            for finding in findings:
                if finding.tool_output:
                    tool_name = finding.tool or "Tool Output"
                    screenshot = self.capture_terminal_screenshot(
                        str(finding.tool_output),
                        str(finding.id),
                        title=f"{tool_name} - {finding.title[:50]}"
                    )
                    if screenshot:
                        evidence = finding.evidence or {}
                        evidence["terminal_screenshot"] = screenshot
                        finding.evidence = evidence
                        captured += 1
                    else:
                        failed += 1

            db.commit()

            return {
                "captured": captured,
                "failed": failed,
                "total_findings_with_output": captured + failed
            }

        except Exception as e:
            logger.error(f"Terminal screenshot capture failed: {e}")
            return {"error": str(e), "captured": 0, "failed": 0}
        finally:
            db.close()
