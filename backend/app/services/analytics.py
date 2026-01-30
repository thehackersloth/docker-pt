"""
Analytics and reporting service
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from app.models.schedule import Schedule
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Analytics and reporting service"""
    
    @staticmethod
    def get_schedule_analytics(days: int = 30) -> Dict[str, Any]:
        """Get schedule execution analytics"""
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            schedules = db.query(Schedule).filter(
                Schedule.created_at >= cutoff_date
            ).all()
            
            total_schedules = len(schedules)
            enabled_schedules = sum(1 for s in schedules if s.enabled)
            total_runs = sum(s.run_count for s in schedules)
            total_success = sum(s.success_count for s in schedules)
            total_failures = sum(s.failure_count for s in schedules)
            
            # Success rate
            success_rate = (total_success / total_runs * 100) if total_runs > 0 else 0
            
            # By schedule type
            by_type = {}
            for schedule in schedules:
                stype = schedule.schedule_type.value
                if stype not in by_type:
                    by_type[stype] = {"count": 0, "runs": 0, "success": 0}
                by_type[stype]["count"] += 1
                by_type[stype]["runs"] += schedule.run_count
                by_type[stype]["success"] += schedule.success_count
            
            return {
                "total_schedules": total_schedules,
                "enabled_schedules": enabled_schedules,
                "total_runs": total_runs,
                "total_success": total_success,
                "total_failures": total_failures,
                "success_rate": success_rate,
                "by_type": by_type
            }
        except Exception as e:
            logger.error(f"Failed to get schedule analytics: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    @staticmethod
    def get_ai_performance_metrics(days: int = 30) -> Dict[str, Any]:
        """Get AI model performance metrics"""
        # This would track AI response times, success rates, etc.
        # For now, return placeholder
        return {
            "total_requests": 0,
            "average_response_time": 0,
            "success_rate": 0,
            "by_provider": {}
        }
    
    @staticmethod
    def get_cost_optimization_recommendations() -> List[Dict[str, Any]]:
        """Get AI cost optimization recommendations"""
        recommendations = []
        
        # Check if local AI is being used
        from app.core.config import settings
        if not settings.AI_LOCAL_ONLY:
            recommendations.append({
                "type": "cost_savings",
                "priority": "high",
                "message": "Consider using local AI (Ollama, WhiteRabbit Neo) for cost savings",
                "estimated_savings": "90%+"
            })
        
        # Check for high usage
        # recommendations.append({
        #     "type": "batch_processing",
        #     "priority": "medium",
        #     "message": "Consider batch processing for multiple requests",
        #     "estimated_savings": "20-30%"
        # })
        
        return recommendations
