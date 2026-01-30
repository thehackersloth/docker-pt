"""
Schedule execution tasks
"""

from celery import Task
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.schedule import Schedule
from app.models.scan import Scan, ScanStatus, ScanType
from app.tasks.scan_tasks import execute_scan_task
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


@celery_app.task(name="process_scheduled_scans")
def process_scheduled_scans():
    """
    Process all scheduled scans that are due to run
    """
    logger.info("Processing scheduled scans")
    
    db = SessionLocal()
    try:
        # Find schedules that are due
        now = datetime.utcnow()
        schedules = db.query(Schedule).filter(
            Schedule.enabled == True,
            Schedule.next_run_at <= now
        ).all()
        
        for schedule in schedules:
            try:
                # Create scan from schedule
                scan = Scan(
                    name=f"{schedule.name} - {now.strftime('%Y-%m-%d %H:%M:%S')}",
                    description=f"Scheduled scan: {schedule.description}",
                    scan_type=ScanType(schedule.scan_config.get('scan_type', 'network')),
                    status=ScanStatus.PENDING,
                    targets=schedule.scan_config.get('targets', []),
                    scan_config=schedule.scan_config,
                    created_by=schedule.created_by,
                )
                db.add(scan)
                db.commit()
                
                # Link scan to schedule
                scan.schedule_id = schedule.id
                db.commit()
                
                # Execute scan asynchronously
                execute_scan_task.delay(scan.id)
                
                # Update schedule
                schedule.last_run_at = now
                schedule.run_count += 1
                
                # Calculate next run time
                schedule.next_run_at = calculate_next_run(schedule)
                db.commit()
                
                logger.info(f"Scheduled scan {schedule.name} started: {scan.id}")
                
            except Exception as e:
                logger.error(f"Error processing schedule {schedule.id}: {e}")
                schedule.failure_count += 1
                db.commit()
                
    except Exception as e:
        logger.error(f"Error processing scheduled scans: {e}")
    finally:
        db.close()


def calculate_next_run(schedule: Schedule) -> datetime:
    """
    Calculate next run time based on schedule type
    """
    now = datetime.utcnow()

    if schedule.schedule_type == "one_time":
        return None  # Don't run again
    elif schedule.schedule_type == "daily":
        return now + timedelta(days=1)
    elif schedule.schedule_type == "weekly":
        return now + timedelta(weeks=1)
    elif schedule.schedule_type == "monthly":
        return now + timedelta(days=30)
    elif schedule.schedule_type == "cron":
        return parse_cron_expression(schedule.schedule_expression, now)

    return now + timedelta(hours=1)


def parse_cron_expression(cron_expr: str, from_time: datetime) -> datetime:
    """
    Parse cron expression and calculate next run time
    Supports standard cron format: minute hour day month weekday
    """
    try:
        # Try using croniter if available
        try:
            from croniter import croniter
            cron = croniter(cron_expr, from_time)
            return cron.get_next(datetime)
        except ImportError:
            pass

        # Fallback: simple cron parser
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron expression: {cron_expr}")
            return from_time + timedelta(hours=1)

        minute, hour, day, month, weekday = parts

        # Start from next minute
        next_run = from_time.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Simple parsing for common patterns
        for _ in range(60 * 24 * 31):  # Max 31 days search
            matches = True

            # Check minute
            if minute != '*':
                if '/' in minute:
                    step = int(minute.split('/')[1])
                    if next_run.minute % step != 0:
                        matches = False
                elif ',' in minute:
                    if str(next_run.minute) not in minute.split(','):
                        matches = False
                elif next_run.minute != int(minute):
                    matches = False

            # Check hour
            if hour != '*' and matches:
                if '/' in hour:
                    step = int(hour.split('/')[1])
                    if next_run.hour % step != 0:
                        matches = False
                elif ',' in hour:
                    if str(next_run.hour) not in hour.split(','):
                        matches = False
                elif next_run.hour != int(hour):
                    matches = False

            # Check day of month
            if day != '*' and matches:
                if ',' in day:
                    if str(next_run.day) not in day.split(','):
                        matches = False
                elif next_run.day != int(day):
                    matches = False

            # Check month
            if month != '*' and matches:
                if ',' in month:
                    if str(next_run.month) not in month.split(','):
                        matches = False
                elif next_run.month != int(month):
                    matches = False

            # Check weekday (0=Sunday or 7=Sunday, 1=Monday, etc.)
            if weekday != '*' and matches:
                current_weekday = (next_run.weekday() + 1) % 7  # Convert to cron format
                if ',' in weekday:
                    weekdays = [int(w) % 7 for w in weekday.split(',')]
                    if current_weekday not in weekdays:
                        matches = False
                else:
                    if current_weekday != int(weekday) % 7:
                        matches = False

            if matches:
                return next_run

            next_run += timedelta(minutes=1)

        # Fallback if no match found
        return from_time + timedelta(hours=1)

    except Exception as e:
        logger.error(f"Error parsing cron expression '{cron_expr}': {e}")
        return from_time + timedelta(hours=1)
