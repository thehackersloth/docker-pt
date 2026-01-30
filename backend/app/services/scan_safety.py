"""
Scan safety controls (rate limiting, DoS protection, validation)
"""

import logging
from typing import List, Dict, Any
from ipaddress import ip_address, ip_network, AddressValueError
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class ScanSafetyService:
    """Scan safety and protection service"""
    
    def __init__(self):
        self.rate_limits = defaultdict(list)
        self.scan_counts = defaultdict(int)
    
    def validate_target(self, target: str, user_id: str) -> tuple[bool, str]:
        """Validate if target is safe to scan"""
        # Check if target is in blocked ranges
        blocked_ranges = getattr(settings, 'BLOCKED_IP_RANGES', '').split(',')
        for blocked in blocked_ranges:
            blocked = blocked.strip()
            if not blocked:
                continue
            try:
                if self._is_in_range(target, blocked):
                    return False, f"Target {target} is in blocked range {blocked}"
            except:
                pass
        
        # Check whitelist if enabled
        if getattr(settings, 'WHITELIST_MODE', False):
            allowed_ranges = getattr(settings, 'ALLOWED_IP_RANGES', '').split(',')
            is_allowed = False
            for allowed in allowed_ranges:
                allowed = allowed.strip()
                if not allowed:
                    continue
                try:
                    if self._is_in_range(target, allowed):
                        is_allowed = True
                        break
                except:
                    pass
            
            if not is_allowed:
                return False, f"Target {target} is not in allowed ranges"
        
        return True, ""
    
    def _is_in_range(self, ip: str, range_str: str) -> bool:
        """Check if IP is in range"""
        try:
            ip_obj = ip_address(ip)
            network = ip_network(range_str, strict=False)
            return ip_obj in network
        except (ValueError, AddressValueError):
            return False
    
    def check_rate_limit(self, target: str, scan_type: str) -> tuple[bool, str]:
        """Check rate limit for target"""
        key = f"{target}:{scan_type}"
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        self.rate_limits[key] = [
            ts for ts in self.rate_limits[key]
            if ts > minute_ago
        ]
        
        # Check limit (max 1 scan per minute per target)
        if len(self.rate_limits[key]) >= 1:
            return False, f"Rate limit exceeded for {target}. Maximum 1 scan per minute."
        
        # Add current scan
        self.rate_limits[key].append(now)
        return True, ""
    
    def check_concurrent_limits(self, user_id: str) -> tuple[bool, str]:
        """Check concurrent scan limits"""
        db = SessionLocal()
        try:
            max_concurrent = getattr(settings, 'MAX_CONCURRENT_SCANS', 5)
            
            active_scans = db.query(Scan).filter(
                Scan.created_by == user_id,
                Scan.status.in_([ScanStatus.PENDING, ScanStatus.RUNNING])
            ).count()
            
            if active_scans >= max_concurrent:
                return False, f"Maximum {max_concurrent} concurrent scans allowed"
            
            return True, ""
        finally:
            db.close()
    
    def check_resource_limits(self, scan_id: str) -> tuple[bool, str]:
        """Check resource usage limits"""
        import psutil

        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        max_cpu = getattr(settings, 'MAX_CPU_PERCENT', 90)
        if cpu_percent > max_cpu:
            return False, f"CPU usage too high ({cpu_percent}%). Maximum allowed: {max_cpu}%"

        # Check memory usage
        memory = psutil.virtual_memory()
        max_memory = getattr(settings, 'MAX_MEMORY_PERCENT', 85)
        if memory.percent > max_memory:
            return False, f"Memory usage too high ({memory.percent}%). Maximum allowed: {max_memory}%"

        # Check disk space
        disk = psutil.disk_usage('/')
        min_disk_gb = getattr(settings, 'MIN_DISK_SPACE_GB', 1)
        free_gb = disk.free / (1024 ** 3)
        if free_gb < min_disk_gb:
            return False, f"Insufficient disk space ({free_gb:.1f}GB free). Minimum required: {min_disk_gb}GB"

        # Check if scan is already running (to prevent duplicate runs)
        db = SessionLocal()
        try:
            existing_scan = db.query(Scan).filter(
                Scan.id == scan_id,
                Scan.status == ScanStatus.RUNNING
            ).first()
            if existing_scan:
                return False, f"Scan {scan_id} is already running"
        finally:
            db.close()

        return True, ""
    
    def validate_scan_request(
        self,
        targets: List[str],
        scan_type: str,
        user_id: str
    ) -> tuple[bool, str]:
        """Validate entire scan request"""
        # Check concurrent limits
        can_scan, msg = self.check_concurrent_limits(user_id)
        if not can_scan:
            return False, msg
        
        # Validate each target
        for target in targets:
            # Validate target
            is_valid, msg = self.validate_target(target, user_id)
            if not is_valid:
                return False, msg
            
            # Check rate limit
            can_scan, msg = self.check_rate_limit(target, scan_type)
            if not can_scan:
                return False, msg
        
        return True, ""
