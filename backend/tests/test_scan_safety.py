"""
Scan safety tests
"""

import pytest
from app.services.scan_safety import ScanSafetyService


def test_validate_target():
    """Test target validation"""
    service = ScanSafetyService()
    
    # Valid target
    is_valid, msg = service.validate_target("8.8.8.8", "user1")
    assert is_valid is True
    
    # Blocked target (if configured)
    # This depends on BLOCKED_IP_RANGES setting
    pass


def test_rate_limit():
    """Test rate limiting"""
    service = ScanSafetyService()
    
    # First scan should pass
    can_scan, msg = service.check_rate_limit("8.8.8.8", "network")
    assert can_scan is True
    
    # Second scan immediately should fail
    can_scan, msg = service.check_rate_limit("8.8.8.8", "network")
    assert can_scan is False
