"""
APScheduler Configuration

Configures the scheduler to periodically trigger monitor checks.
Uses AsyncIOScheduler for async compatibility.
"""

from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from worker.engine import check_due_monitors


# Scheduler configuration
SCHEDULER_INTERVAL_SECONDS = 10  # How often to check for due monitors


def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the APScheduler instance.
    
    Returns:
        Configured AsyncIOScheduler instance
    """
    scheduler = AsyncIOScheduler(
        job_defaults={
            'coalesce': True,  # Combine missed executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 60,  # Allow 60 seconds for misfired jobs
        }
    )
    
    # Add the main check job
    scheduler.add_job(
        check_due_monitors,
        trigger=IntervalTrigger(seconds=SCHEDULER_INTERVAL_SECONDS),
        id='check_due_monitors',
        name='Check Due Monitors',
        replace_existing=True,
    )
    
    return scheduler


def start_scheduler(scheduler: AsyncIOScheduler) -> None:
    """
    Start the scheduler.
    
    Args:
        scheduler: The APScheduler instance to start
    """
    scheduler.start()
    print(f"[{datetime.now().isoformat()}] Scheduler started (interval: {SCHEDULER_INTERVAL_SECONDS}s)")


def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    """
    Gracefully shutdown the scheduler.
    
    Args:
        scheduler: The APScheduler instance to stop
    """
    scheduler.shutdown(wait=True)
    print(f"[{datetime.now().isoformat()}] Scheduler stopped")
