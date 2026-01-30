"""
Input validation utilities
"""

import re
from ipaddress import ip_address, ip_network, AddressValueError
from typing import List, Tuple, Optional
from urllib.parse import urlparse


def validate_ip(ip: str) -> Tuple[bool, str]:
    """Validate IP address"""
    try:
        ip_address(ip)
        return True, ""
    except (ValueError, AddressValueError) as e:
        return False, f"Invalid IP address: {e}"


def validate_cidr(cidr: str) -> Tuple[bool, str]:
    """Validate CIDR notation"""
    try:
        ip_network(cidr, strict=False)
        return True, ""
    except (ValueError, AddressValueError) as e:
        return False, f"Invalid CIDR: {e}"


def validate_hostname(hostname: str) -> Tuple[bool, str]:
    """Validate hostname"""
    if len(hostname) > 255:
        return False, "Hostname too long (max 255 characters)"

    hostname_pattern = re.compile(
        r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)$'
    )

    labels = hostname.split('.')
    if not labels:
        return False, "Invalid hostname format"

    for label in labels:
        if not hostname_pattern.match(label):
            return False, f"Invalid hostname label: {label}"

    return True, ""


def validate_url(url: str) -> Tuple[bool, str]:
    """Validate URL"""
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format"
        if result.scheme not in ['http', 'https']:
            return False, "URL must use http or https scheme"
        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {e}"


def validate_port(port: int) -> Tuple[bool, str]:
    """Validate port number"""
    if not isinstance(port, int):
        return False, "Port must be an integer"
    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"
    return True, ""


def validate_port_range(port_range: str) -> Tuple[bool, str]:
    """Validate port range (e.g., '80', '80-443', '80,443,8080')"""
    if not port_range:
        return False, "Port range is empty"

    # Handle comma-separated ports
    for part in port_range.split(','):
        part = part.strip()

        # Handle range (e.g., 80-443)
        if '-' in part:
            try:
                start, end = part.split('-', 1)
                start_port = int(start.strip())
                end_port = int(end.strip())

                valid, msg = validate_port(start_port)
                if not valid:
                    return False, f"Invalid start port: {msg}"

                valid, msg = validate_port(end_port)
                if not valid:
                    return False, f"Invalid end port: {msg}"

                if start_port > end_port:
                    return False, "Start port must be less than end port"
            except ValueError:
                return False, f"Invalid port range: {part}"
        else:
            try:
                port = int(part)
                valid, msg = validate_port(port)
                if not valid:
                    return False, msg
            except ValueError:
                return False, f"Invalid port: {part}"

    return True, ""


def validate_target(target: str) -> Tuple[bool, str, str]:
    """
    Validate and identify target type
    Returns: (is_valid, error_message, target_type)
    Target types: 'ip', 'cidr', 'hostname', 'url'
    """
    # Check if URL
    if target.startswith('http://') or target.startswith('https://'):
        valid, msg = validate_url(target)
        return valid, msg, 'url' if valid else ''

    # Check if CIDR
    if '/' in target:
        valid, msg = validate_cidr(target)
        return valid, msg, 'cidr' if valid else ''

    # Check if IP
    valid, msg = validate_ip(target)
    if valid:
        return True, "", 'ip'

    # Check if hostname
    valid, msg = validate_hostname(target)
    if valid:
        return True, "", 'hostname'

    return False, "Target must be a valid IP, CIDR, hostname, or URL", ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email address"""
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    if email_pattern.match(email):
        return True, ""
    return False, "Invalid email format"


def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Validate password strength
    Returns: (is_valid, list of issues)
    """
    issues = []

    if len(password) < 12:
        issues.append("Password must be at least 12 characters")

    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")

    if not re.search(r'\d', password):
        issues.append("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append("Password must contain at least one special character")

    return len(issues) == 0, issues


def validate_cron_expression(cron: str) -> Tuple[bool, str]:
    """Validate cron expression"""
    parts = cron.strip().split()
    if len(parts) != 5:
        return False, "Cron expression must have 5 fields (minute hour day month weekday)"

    ranges = [
        (0, 59, "minute"),
        (0, 23, "hour"),
        (1, 31, "day"),
        (1, 12, "month"),
        (0, 7, "weekday")
    ]

    for i, part in enumerate(parts):
        min_val, max_val, name = ranges[i]

        if part == '*':
            continue

        # Handle step values (*/5)
        if part.startswith('*/'):
            try:
                step = int(part[2:])
                if step < 1:
                    return False, f"Invalid step value for {name}"
                continue
            except ValueError:
                return False, f"Invalid step value for {name}"

        # Handle comma-separated values
        for val in part.split(','):
            # Handle range (1-5)
            if '-' in val:
                try:
                    start, end = val.split('-', 1)
                    start, end = int(start), int(end)
                    if start < min_val or end > max_val or start > end:
                        return False, f"Invalid range for {name}: {val}"
                except ValueError:
                    return False, f"Invalid range for {name}: {val}"
            else:
                try:
                    num = int(val)
                    if num < min_val or num > max_val:
                        return False, f"Value {num} out of range for {name}"
                except ValueError:
                    return False, f"Invalid value for {name}: {val}"

    return True, ""
