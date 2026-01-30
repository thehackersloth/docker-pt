"""
Log rotation service
"""

import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from app.core.config import settings

logger = logging.getLogger(__name__)


class LogRotationService:
    """Log rotation and management"""
    
    def __init__(self):
        self.log_dir = Path("/data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
    
    def setup_rotating_handler(self, log_file: str, logger_name: str = None):
        """Setup rotating file handler"""
        log_path = self.log_dir / log_file
        
        handler = RotatingFileHandler(
            str(log_path),
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        if logger_name:
            log = logging.getLogger(logger_name)
        else:
            log = logging.getLogger()
        
        log.addHandler(handler)
        return handler
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up logs older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete log file {log_file}: {e}")
        
        return deleted_count
    
    def get_log_stats(self) -> dict:
        """Get log file statistics"""
        stats = {
            "total_files": 0,
            "total_size": 0,
            "files": []
        }
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                size = log_file.stat().st_size
                stats["total_files"] += 1
                stats["total_size"] += size
                stats["files"].append({
                    "name": log_file.name,
                    "size": size,
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
            except:
                pass
        
        return stats
