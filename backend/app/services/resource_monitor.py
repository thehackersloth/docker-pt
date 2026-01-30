"""
Resource monitoring service
"""

import psutil
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """System resource monitoring"""
    
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """Get current system resource statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network stats
            net_io = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "per_cpu": psutil.cpu_percent(interval=1, percpu=True)
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def get_process_stats(process_name: str) -> Dict[str, Any]:
        """Get stats for a specific process"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                if process_name.lower() in proc.info['name'].lower():
                    return {
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu_percent": proc.info['cpu_percent'],
                        "memory_mb": proc.info['memory_info'].rss / 1024 / 1024
                    }
            return {"error": "Process not found"}
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def check_health() -> Dict[str, Any]:
        """Check system health"""
        stats = ResourceMonitor.get_system_stats()
        
        if "error" in stats:
            return {"status": "unhealthy", "error": stats["error"]}
        
        warnings = []
        
        # Check CPU
        if stats["cpu"]["percent"] > 90:
            warnings.append("High CPU usage")
        
        # Check memory
        if stats["memory"]["percent"] > 90:
            warnings.append("High memory usage")
        
        # Check disk
        if stats["disk"]["percent"] > 90:
            warnings.append("Low disk space")
        
        status = "healthy" if not warnings else "degraded"
        
        return {
            "status": status,
            "warnings": warnings,
            "stats": stats
        }
