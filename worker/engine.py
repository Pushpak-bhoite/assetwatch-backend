"""
Monitoring Engine

Orchestrates the monitoring checks:
1. Queries database for monitors due for checking
2. Runs appropriate checkers concurrently
3. Updates monitor status and metrics in database

Uses asyncio semaphore to limit concurrent checks.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_maker, StandaloneMonitor, StandaloneMonitorMetric
from worker.checkers import run_check, CheckResult


# Configuration
MAX_CONCURRENT_CHECKS = 50  # Maximum concurrent monitor checks
FAILURES_BEFORE_DOWN = 3  # Number of consecutive failures before marking as down

# Check interval mapping (string to seconds)
INTERVAL_SECONDS = {
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1hr": 3600,
    "12hr": 43200,
}


async def check_due_monitors() -> None:
    """
    Main function called by scheduler.
    Fetches monitors due for checking and runs checks concurrently.
    """
    async with async_session_maker() as session:
        # Get monitors that are due for checking
        monitors = await get_due_monitors(session)
        
        if not monitors:
            return
        
        print(f"[{datetime.now().isoformat()}] Found {len(monitors)} monitors due for checking")
        
        # Create semaphore to limit concurrent checks
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
        
        # Run checks concurrently
        tasks = [
            check_monitor_with_semaphore(semaphore, monitor, session)
            for monitor in monitors
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Commit all changes
        await session.commit()


async def get_due_monitors(session: AsyncSession) -> list[StandaloneMonitor]:
    """
    Get all active monitors that are due for checking.
    
    A monitor is due if:
    - is_active = 1
    - next_check_at is NULL (never checked) OR next_check_at <= now
    
    Args:
        session: Database session
        
    Returns:
        List of monitors due for checking
    """
    now = datetime.utcnow()
    
    result = await session.execute(
        select(StandaloneMonitor).where(
            and_(
                StandaloneMonitor.is_active == 1,
                or_(
                    StandaloneMonitor.next_check_at.is_(None),
                    StandaloneMonitor.next_check_at <= now
                )
            )
        )
    )
    
    return list(result.scalars().all())


async def check_monitor_with_semaphore(
    semaphore: asyncio.Semaphore,
    monitor: StandaloneMonitor,
    session: AsyncSession
) -> None:
    """
    Run a monitor check with semaphore limiting.
    
    Args:
        semaphore: Asyncio semaphore for concurrency limiting
        monitor: The monitor to check
        session: Database session
    """
    async with semaphore:
        try:
            await check_single_monitor(monitor, session)
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error checking monitor {monitor.id}: {e}")


async def check_single_monitor(
    monitor: StandaloneMonitor,
    session: AsyncSession
) -> None:
    """
    Execute a single monitor check and update database.
    
    Args:
        monitor: The monitor to check
        session: Database session
    """
    # Run the appropriate checker
    result = await run_check(monitor)
    
    # Update monitor status based on result
    await update_monitor_status(monitor, result, session)
    
    # Record metric
    await record_metric(monitor.id, result, session)
    
    # Calculate and set next check time
    interval_seconds = INTERVAL_SECONDS.get(monitor.check_interval, 300)
    monitor.next_check_at = datetime.utcnow() + timedelta(seconds=interval_seconds)
    monitor.last_check_at = datetime.utcnow()


async def update_monitor_status(
    monitor: StandaloneMonitor,
    result: CheckResult,
    session: AsyncSession
) -> None:
    """
    Update monitor status based on check result.
    
    Implements consecutive failure tracking:
    - On success: Reset failures, set status to "up"
    - On failure: Increment failures, set status to "down" after threshold
    
    Args:
        monitor: The monitor to update
        result: Check result from checker
        session: Database session
    """
    if result.success:
        # Check succeeded
        monitor.current_status = "up"
        monitor.consecutive_failures = 0
        monitor.response_time = result.response_time
    else:
        # Check failed
        monitor.consecutive_failures = (monitor.consecutive_failures or 0) + 1
        
        # Only mark as down after consecutive failures threshold
        if monitor.consecutive_failures >= FAILURES_BEFORE_DOWN:
            monitor.current_status = "down"
        
        monitor.response_time = result.response_time
    
    # Log the result
    status_str = "UP" if result.success else "DOWN"
    print(
        f"[{datetime.now().isoformat()}] "
        f"[{monitor.monitor_type.upper()}] {monitor.friendly_name}: {status_str} "
        f"({result.response_time:.2f}ms)"
        + (f" - {result.error_message}" if result.error_message else "")
    )


async def record_metric(
    monitor_id: UUID,
    result: CheckResult,
    session: AsyncSession
) -> None:
    """
    Record a check result as a metric in the database.
    
    Args:
        monitor_id: ID of the monitor
        result: Check result from checker
        session: Database session
    """
    metric = StandaloneMonitorMetric(
        monitor_id=monitor_id,
        status="up" if result.success else "down",
        response_time=result.response_time,
        error_message=result.error_message,
        resolved_value=result.resolved_value,
        timestamp=datetime.utcnow(),
    )
    session.add(metric)
