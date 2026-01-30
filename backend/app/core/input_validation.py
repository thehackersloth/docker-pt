"""
Input validation and sanitization utilities
"""

import re
from typing import Any, List
from ipaddress import ip_address, ip_network, AddressValueError


def validate_ip(ip: str) -> bool:
    """Validate IP address"""
    try:
        ip_address(ip)
        return True
    except (ValueError, AddressValueError):
        return False


def validate_ip_range(ip_range: str) -> bool:
    """Validate IP range/CIDR"""
    try:
        ip_network(ip_range, strict=False)
        return True
    except (ValueError, AddressValueError):
        return False


def validate_domain(domain: str) -> bool:
    """Validate domain name"""
    pattern = r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$'
    return bool(re.match(pattern, domain.lower()))


def sanitize_input(input_str: str) -> str:
    """Sanitize user input"""
    # Remove null bytes
    input_str = input_str.replace('\x00', '')
    
    # Remove control characters except newline and tab
    input_str = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F]', '', input_str)
    
    # Limit length
    if len(input_str) > 10000:
        input_str = input_str[:10000]
    
    return input_str.strip()


def validate_scan_targets(targets: List[str]) -> tuple[bool, str]:
    """Validate scan targets"""
    if not targets:
        return False, "No targets provided"
    
    if len(targets) > 1000:
        return False, "Too many targets (max 1000)"
    
    for target in targets:
        target = target.strip()
        if not target:
            continue
        
        # Check if IP, IP range, or domain
        if not (validate_ip(target) or validate_ip_range(target) or validate_domain(target)):
            return False, f"Invalid target format: {target}"
    
    return True, ""


def validate_port(port: str) -> bool:
    """Validate port number or range"""
    try:
        if '-' in port:
            start, end = port.split('-')
            start_port = int(start)
            end_port = int(end)
            return 1 <= start_port <= 65535 and 1 <= end_port <= 65535 and start_port <= end_port
        else:
            port_num = int(port)
            return 1 <= port_num <= 65535
    except (ValueError, AttributeError):
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename"""
    # Remove path components
    filename = filename.replace('/', '').replace('\\', '').replace('..', '')
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename
