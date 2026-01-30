"""
Backup service for database and data
"""

import logging
import subprocess
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class BackupService:
    """Backup service for databases and data"""
    
    def __init__(self):
        self.backup_dir = Path("/data/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def backup_postgres(self) -> Optional[str]:
        """Backup PostgreSQL database"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"postgres_{timestamp}.sql"
            
            cmd = [
                'pg_dump',
                '-h', settings.POSTGRES_HOST,
                '-p', str(settings.POSTGRES_PORT),
                '-U', settings.POSTGRES_USER,
                '-d', settings.POSTGRES_DB,
                '-f', str(backup_file)
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = settings.POSTGRES_PASSWORD
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"PostgreSQL backup failed: {stderr.decode()}")
                return None
            
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"PostgreSQL backup error: {e}")
            return None
    
    def backup_neo4j(self) -> Optional[str]:
        """Backup Neo4j database"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"neo4j_{timestamp}.dump"
            
            # Neo4j backup command
            cmd = [
                'neo4j-admin', 'dump',
                '--database=neo4j',
                '--to', str(backup_file)
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Neo4j backup failed: {stderr.decode()}")
                return None
            
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Neo4j backup error: {e}")
            return None
    
    def backup_data(self) -> Optional[str]:
        """Backup application data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"data_{timestamp}.tar.gz"
            
            data_dir = Path("/data")
            cmd = ['tar', '-czf', str(backup_file), '-C', str(data_dir.parent), 'data']
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Data backup failed: {stderr.decode()}")
                return None
            
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Data backup error: {e}")
            return None
    
    def full_backup(self) -> dict:
        """Perform full backup"""
        results = {
            "timestamp": datetime.now().isoformat(),
            "postgres": None,
            "neo4j": None,
            "data": None,
            "success": False
        }
        
        results["postgres"] = self.backup_postgres()
        results["neo4j"] = self.backup_neo4j()
        results["data"] = self.backup_data()
        
        results["success"] = all([
            results["postgres"],
            results["neo4j"],
            results["data"]
        ])
        
        return results
