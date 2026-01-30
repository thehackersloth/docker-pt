"""
Base tool runner class
All tool runners should inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseToolRunner(ABC):
    """Base class for all tool runners"""

    def __init__(self, scan_id: str, tool_name: str):
        self.scan_id = scan_id
        self.tool_name = tool_name
        self.logger = logging.getLogger(f"{__name__}.{tool_name}")

    def _append_log(self, message: str):
        """Append message to scan output log"""
        try:
            from app.core.database import SessionLocal
            from app.models.scan import Scan

            db = SessionLocal()
            try:
                scan = db.query(Scan).filter(Scan.id == self.scan_id).first()
                if scan:
                    timestamp = datetime.utcnow().strftime("%H:%M:%S")
                    log_entry = f"[{timestamp}] {message}"
                    if scan.output_log:
                        scan.output_log = scan.output_log + log_entry
                    else:
                        scan.output_log = log_entry
                    db.commit()
            finally:
                db.close()
        except Exception as e:
            self.logger.error(f"Failed to append log: {e}")
    
    @abstractmethod
    def validate_input(self, targets: List[str], config: Dict[str, Any] = None) -> bool:
        """Validate input parameters"""
        pass
    
    @abstractmethod
    def run(self, targets: List[str], config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the tool"""
        pass
    
    @abstractmethod
    def parse_output(self, output: str) -> Dict[str, Any]:
        """Parse tool output"""
        pass
    
    def get_progress(self) -> int:
        """Get execution progress (0-100)"""
        return 0
    
    def cleanup(self):
        """Cleanup after execution"""
        pass
