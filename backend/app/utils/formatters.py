"""
Data formatting utilities
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string"""
    if not dt:
        return ""
    return dt.strftime(format)


def format_datetime_relative(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '2 hours ago')"""
    if not dt:
        return ""

    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h" if hours else f"{days}d"


def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable string"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.2f} GB"


def format_severity(severity: str) -> str:
    """Format severity with emoji indicator"""
    severity_map = {
        'critical': '🔴 Critical',
        'high': '🟠 High',
        'medium': '🟡 Medium',
        'low': '🟢 Low',
        'info': '🔵 Info'
    }
    return severity_map.get(severity.lower(), severity)


def format_cvss_score(score: float) -> str:
    """Format CVSS score with rating"""
    if score >= 9.0:
        return f"{score:.1f} (Critical)"
    elif score >= 7.0:
        return f"{score:.1f} (High)"
    elif score >= 4.0:
        return f"{score:.1f} (Medium)"
    elif score >= 0.1:
        return f"{score:.1f} (Low)"
    else:
        return f"{score:.1f} (None)"


def format_port_list(ports: List[int]) -> str:
    """Format list of ports, grouping consecutive ports into ranges"""
    if not ports:
        return ""

    ports = sorted(set(ports))
    ranges = []
    start = end = ports[0]

    for port in ports[1:]:
        if port == end + 1:
            end = port
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = end = port

    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")

    return ", ".join(ranges)


def format_findings_summary(findings: List[Dict[str, Any]]) -> str:
    """Format findings summary for display"""
    if not findings:
        return "No findings"

    severity_counts = {}
    for finding in findings:
        severity = finding.get('severity', 'unknown').lower()
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    parts = []
    for severity in ['critical', 'high', 'medium', 'low', 'info']:
        count = severity_counts.get(severity, 0)
        if count > 0:
            parts.append(f"{count} {severity.capitalize()}")

    return ", ".join(parts) if parts else "No findings"


def format_json_pretty(data: Any) -> str:
    """Format data as pretty-printed JSON"""
    return json.dumps(data, indent=2, default=str)


def truncate_string(s: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate string to max length with suffix"""
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing invalid characters"""
    import re
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized or "unnamed"


def format_table(headers: List[str], rows: List[List[str]], max_width: int = 80) -> str:
    """Format data as ASCII table"""
    if not headers or not rows:
        return ""

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Build table
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    lines = [separator]

    # Header
    header_line = "|"
    for i, h in enumerate(headers):
        header_line += f" {h.ljust(col_widths[i])} |"
    lines.append(header_line)
    lines.append(separator)

    # Rows
    for row in rows:
        row_line = "|"
        for i, cell in enumerate(row):
            if i < len(col_widths):
                row_line += f" {str(cell).ljust(col_widths[i])} |"
        lines.append(row_line)

    lines.append(separator)

    return "\n".join(lines)
