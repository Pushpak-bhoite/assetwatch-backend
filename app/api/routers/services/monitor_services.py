
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

import re
from app.core.db import User, StandaloneMonitor, MonitorTag, StandaloneMonitorMetric, MonitorIncident, get_db
from app.users import current_active_user
from app.api.routers.models.monitors_models import (
    StandaloneMonitorResponse,
    SparklinePoint,
    MonitorIncidentResponse,
    HourlyStatusPoint,
    HourlyStatusResponse,
    MetricsChartPoint,
    MetricsChartResponse,
    MonitorDetailResponse,
)

# ==================== CONSTANTS ====================

# Check intervals in seconds
INTERVAL_OPTIONS = {
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1hr": 3600,
    "12hr": 43200,
}

# TCP Port options for Port monitoring
TCP_PORTS = {
    "FTP": 21,
    "SSH/SFTP": 22,
    "SMTP": 25,
    "DNS": 53,
    "HTTP": 80,
    "POP3": 110,
    "IMAP": 143,
    "HTTPS": 443,
    "SMTP-SSL": 465,
    "SMTP-TLS": 587,
    "IMAP-SSL": 993,
    "POP3-SSL": 995,
    "MySQL": 3306,
}

# DNS Record types
DNS_RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA"]


# ===================== SUB-HELPER FUNCTIONS =================================
# Sparkline period label generators based on check interval
# Returns human-readable time period for N data points
def _format_sparkline_period(interval: str, point_count: int) -> str:
    """Generate human-readable period label for sparkline data"""
    interval_seconds = INTERVAL_OPTIONS.get(interval, 300)
    total_seconds = interval_seconds * point_count
    
    if total_seconds < 60:
        return f"last {total_seconds} secs"
    elif total_seconds < 3600:
        mins = total_seconds / 60
        if mins == int(mins):
            return f"last {int(mins)} mins"
        return f"last {mins:.1f} mins"
    elif total_seconds < 86400:
        hrs = total_seconds / 3600
        if hrs == int(hrs):
            return f"last {int(hrs)} hrs"
        return f"last {hrs:.1f} hrs"
    else:
        days = total_seconds / 86400
        if days == int(days):
            return f"last {int(days)} days"
        return f"last {days:.1f} days"




# ==================== HELPER FUNCTIONS ====================

def validate_url(url: str) -> str:
    """Validate and return URL"""
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must start with http:// or https://")
    return url


def validate_host(host: str) -> str:
    """Validate IP address or hostname"""
    ip_regex = r'^(\d{1,3}\.){3}\d{1,3}$'
    hostname_regex = r'^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$'
    if not (re.match(ip_regex, host) or re.match(hostname_regex, host) or len(host) >= 2):
        raise ValueError("Enter a valid IP address or hostname")
    return host


def validate_interval(interval: str) -> str:
    """Validate check interval"""
    if interval not in INTERVAL_OPTIONS:
        raise ValueError(f"Invalid interval. Must be one of: {', '.join(INTERVAL_OPTIONS.keys())}")
    return interval


def validate_record_type(record_type: str) -> str:
    """Validate DNS record type"""
    if record_type.upper() not in DNS_RECORD_TYPES:
        raise ValueError(f"Invalid record type. Must be one of: {', '.join(DNS_RECORD_TYPES)}")
    return record_type.upper()


def clean_host(host: str) -> str:
    """Remove protocol prefix if present"""
    if host.startswith(('http://', 'https://')):
        host = host.replace('http://', '').replace('https://', '').split('/')[0]
    return host


async def get_tags_list(monitor_id: UUID, db: AsyncSession) -> list[str]:
    """Get list of tags for a monitor"""
    result = await db.execute(
        select(MonitorTag.tag).where(MonitorTag.monitor_id == monitor_id)
    )
    return [row[0] for row in result.fetchall()]


async def calculate_uptime_percentage(
    monitor_id: UUID,
    db: AsyncSession,
    days: int = 30
) -> Optional[float]:
    """Calculate uptime percentage from metrics"""
    since = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(StandaloneMonitorMetric).where(
            StandaloneMonitorMetric.monitor_id == monitor_id,
            StandaloneMonitorMetric.timestamp >= since
        )
    )
    metrics = result.scalars().all()
    
    if not metrics:
        return None
    
    up_count = sum(1 for m in metrics if m.status == "up")
    return round((up_count / len(metrics)) * 100, 2)


async def get_sparkline_data(
    monitor_id: UUID,
    check_interval: str,
    db: AsyncSession,
    limit: int = 30
) -> tuple[list[SparklinePoint], Optional[str]]:
    """
    Fetch last N metrics for sparkline visualization.
    Returns (sparkline_points, period_label)
    
    Returns empty list and None if < 2 data points available.
    """
    result = await db.execute(
        select(StandaloneMonitorMetric)
        .where(StandaloneMonitorMetric.monitor_id == monitor_id)
        .order_by(desc(StandaloneMonitorMetric.timestamp))
        .limit(limit)
    )
    metrics = result.scalars().all()
    
    # Need at least 2 points for a meaningful sparkline
    if len(metrics) < 2:
        return [], None
    
    # Reverse to chronological order (oldest first for left-to-right display)
    metrics = list(reversed(metrics))
    
    # Calculate period label based on actual data points
    period_label = _format_sparkline_period(check_interval, len(metrics))
    
    sparkline_points = [
        SparklinePoint(
            response_time=m.response_time,
            status=m.status,
            timestamp=m.timestamp.isoformat()
        )
        for m in metrics
    ]
    
    return sparkline_points, period_label


async def build_monitor_response(
    monitor: StandaloneMonitor,
    db: AsyncSession
) -> StandaloneMonitorResponse:
    """Build response object for a monitor"""
    tags = await get_tags_list(monitor.id, db)
    uptime = await calculate_uptime_percentage(monitor.id, db)
    
    # Get sparkline data (last 30 checks)
    sparkline_data, sparkline_period = await get_sparkline_data(
        monitor.id,
        monitor.check_interval,
        db
    )
    
    return StandaloneMonitorResponse(
        id=str(monitor.id),
        user_id=str(monitor.user_id),
        monitor_type=monitor.monitor_type,
        friendly_name=monitor.friendly_name,
        target=monitor.target,
        tags=tags,
        notify_email=bool(monitor.notify_email),
        check_interval=monitor.check_interval,
        check_interval_seconds=INTERVAL_OPTIONS.get(monitor.check_interval, 300),
        is_active=bool(monitor.is_active),
        current_status=monitor.current_status if monitor.is_active else "paused",
        last_check_at=monitor.last_check_at.isoformat() if monitor.last_check_at else None,
        response_time=monitor.response_time,
        uptime_percentage=uptime,
        created_at=monitor.created_at.isoformat(),
        updated_at=monitor.updated_at.isoformat(),
        port=monitor.port,
        port_name=monitor.port_name,
        dns_server=monitor.dns_server,
        record_type=monitor.record_type,
        expected_value=monitor.expected_value,
        sparkline_data=sparkline_data,
        sparkline_period=sparkline_period,
    )


async def create_tags(monitor_id: UUID, tags: list[str], db: AsyncSession):
    """Create tags for a monitor"""
    for tag in tags:
        if tag.strip():  # Skip empty tags
            db_tag = MonitorTag(
                monitor_id=monitor_id,
                tag=tag.strip()
            )
            db.add(db_tag)


async def update_tags(monitor_id: UUID, tags: list[str], db: AsyncSession):
    """Replace all tags for a monitor"""
    # Delete existing tags
    existing_tags = await db.execute(
        select(MonitorTag).where(MonitorTag.monitor_id == monitor_id)
    )
    for tag in existing_tags.scalars().all():
        await db.delete(tag)
    
    # Create new tags
    await create_tags(monitor_id, tags, db)


# ==================== MONITOR DETAILS PAGE SERVICES ====================

async def get_monitor_detail(
    monitor_id: UUID,
    db: AsyncSession
) -> MonitorDetailResponse:
    """Get extended monitor details for details page"""
    # Get monitor
    result = await db.execute(
        select(StandaloneMonitor).where(StandaloneMonitor.id == monitor_id)
    )
    monitor = result.scalar_one_or_none()
    if not monitor:
        return None
    
    # Get tags
    tags = await get_tags_list(monitor_id, db)
    
    # Calculate 30-day stats
    since_30d = datetime.utcnow() - timedelta(days=30)
    metrics_result = await db.execute(
        select(StandaloneMonitorMetric).where(
            StandaloneMonitorMetric.monitor_id == monitor_id,
            StandaloneMonitorMetric.timestamp >= since_30d
        )
    )
    metrics_30d = metrics_result.scalars().all()
    
    # Calculate uptime percentage
    total_checks_30d = len(metrics_30d)
    up_count = sum(1 for m in metrics_30d if m.status == "up")
    uptime_percentage_30d = round((up_count / total_checks_30d) * 100, 2) if total_checks_30d > 0 else 100.0
    
    # Calculate average response time
    response_times = [m.response_time for m in metrics_30d if m.response_time is not None]
    avg_response_time_30d = round(sum(response_times) / len(response_times), 2) if response_times else None
    
    # Count incidents in last 30 days
    incidents_result = await db.execute(
        select(func.count(MonitorIncident.id)).where(
            MonitorIncident.monitor_id == monitor_id,
            MonitorIncident.started_at >= since_30d
        )
    )
    total_incidents_30d = incidents_result.scalar() or 0
    
    # Get current ongoing incident (if any)
    current_incident_result = await db.execute(
        select(MonitorIncident).where(
            MonitorIncident.monitor_id == monitor_id,
            MonitorIncident.is_resolved == 0
        ).order_by(desc(MonitorIncident.started_at)).limit(1)
    )
    current_incident_db = current_incident_result.scalar_one_or_none()
    current_incident = None
    if current_incident_db:
        current_incident = MonitorIncidentResponse(
            id=str(current_incident_db.id),
            monitor_id=str(current_incident_db.monitor_id),
            started_at=current_incident_db.started_at.isoformat(),
            ended_at=current_incident_db.ended_at.isoformat() if current_incident_db.ended_at else None,
            duration_seconds=current_incident_db.duration_seconds,
            error_message=current_incident_db.error_message,
            check_count=current_incident_db.check_count,
            is_resolved=bool(current_incident_db.is_resolved),
        )
    
    # Get last error message
    last_error = None
    last_down = await db.execute(
        select(StandaloneMonitorMetric).where(
            StandaloneMonitorMetric.monitor_id == monitor_id,
            StandaloneMonitorMetric.status == "down"
        ).order_by(desc(StandaloneMonitorMetric.timestamp)).limit(1)
    )
    last_down_metric = last_down.scalar_one_or_none()
    if last_down_metric:
        last_error = last_down_metric.error_message
    
    return MonitorDetailResponse(
        id=str(monitor.id),
        user_id=str(monitor.user_id),
        monitor_type=monitor.monitor_type,
        friendly_name=monitor.friendly_name,
        target=monitor.target,
        tags=tags,
        notify_email=bool(monitor.notify_email),
        check_interval=monitor.check_interval,
        check_interval_seconds=INTERVAL_OPTIONS.get(monitor.check_interval, 300),
        is_active=bool(monitor.is_active),
        current_status=monitor.current_status if monitor.is_active else "paused",
        last_check_at=monitor.last_check_at.isoformat() if monitor.last_check_at else None,
        response_time=monitor.response_time,
        created_at=monitor.created_at.isoformat(),
        updated_at=monitor.updated_at.isoformat(),
        port=monitor.port,
        port_name=monitor.port_name,
        dns_server=monitor.dns_server,
        record_type=monitor.record_type,
        expected_value=monitor.expected_value,
        uptime_percentage_30d=uptime_percentage_30d,
        avg_response_time_30d=avg_response_time_30d,
        total_checks_30d=total_checks_30d,
        total_incidents_30d=total_incidents_30d,
        current_incident=current_incident,
        consecutive_failures=monitor.consecutive_failures or 0,
        last_error=last_error,
    )


async def get_hourly_status(
    monitor_id: UUID,
    db: AsyncSession
) -> HourlyStatusResponse:
    """Get 24-hour status summary with hourly buckets"""
    now = datetime.utcnow()
    # Start from beginning of current hour, go back 24 hours
    current_hour_start = now.replace(minute=0, second=0, microsecond=0)
    start_time = current_hour_start - timedelta(hours=23)
    
    # Get all metrics in the 24-hour window
    result = await db.execute(
        select(StandaloneMonitorMetric).where(
            StandaloneMonitorMetric.monitor_id == monitor_id,
            StandaloneMonitorMetric.timestamp >= start_time
        ).order_by(StandaloneMonitorMetric.timestamp)
    )
    metrics = result.scalars().all()
    
    # Get incidents in the 24-hour window
    incidents_result = await db.execute(
        select(MonitorIncident).where(
            MonitorIncident.monitor_id == monitor_id,
            MonitorIncident.started_at >= start_time
        )
    )
    incidents = incidents_result.scalars().all()
    
    # Calculate total downtime from incidents
    total_downtime_seconds = 0
    for incident in incidents:
        end_time = incident.ended_at or now
        start = max(incident.started_at, start_time)
        if end_time > start:
            total_downtime_seconds += int((end_time - start).total_seconds())
    
    # Build hourly buckets
    hours = []
    for i in range(24):
        hour_start = start_time + timedelta(hours=i)
        hour_end = hour_start + timedelta(hours=1)
        
        # Get metrics for this hour
        hour_metrics = [m for m in metrics if hour_start <= m.timestamp < hour_end]
        
        total_checks = len(hour_metrics)
        failed_checks = sum(1 for m in hour_metrics if m.status == "down")
        
        # Determine status
        if total_checks == 0:
            status = "no_data"
            uptime = 100.0
        elif failed_checks == 0:
            status = "up"
            uptime = 100.0
        elif failed_checks == total_checks:
            status = "down"
            uptime = 0.0
        else:
            status = "partial"
            uptime = round(((total_checks - failed_checks) / total_checks) * 100, 2)
        
        hours.append(HourlyStatusPoint(
            hour=hour_start.hour,
            timestamp=hour_start.isoformat(),
            status=status,
            uptime_percentage=uptime,
            total_checks=total_checks,
            failed_checks=failed_checks,
        ))
    
    return HourlyStatusResponse(
        hours=hours,
        total_incidents=len(incidents),
        total_downtime_minutes=total_downtime_seconds // 60,
    )


async def get_metrics_chart(
    monitor_id: UUID,
    db: AsyncSession,
    range_str: str = "24h"
) -> MetricsChartResponse:
    """Get metrics for response time chart"""
    # Parse range
    range_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    
    if range_str not in range_map:
        range_str = "24h"
    
    time_delta = range_map[range_str]
    since = datetime.utcnow() - time_delta
    
    # Get metrics
    result = await db.execute(
        select(StandaloneMonitorMetric).where(
            StandaloneMonitorMetric.monitor_id == monitor_id,
            StandaloneMonitorMetric.timestamp >= since
        ).order_by(StandaloneMonitorMetric.timestamp)
    )
    metrics = result.scalars().all()
    
    # Build data points
    data = [
        MetricsChartPoint(
            timestamp=m.timestamp.isoformat(),
            response_time=m.response_time,
            status=m.status,
        )
        for m in metrics
    ]
    
    # Calculate stats
    response_times = [m.response_time for m in metrics if m.response_time is not None]
    avg_response = round(sum(response_times) / len(response_times), 2) if response_times else None
    min_response = round(min(response_times), 2) if response_times else None
    max_response = round(max(response_times), 2) if response_times else None
    
    # Calculate uptime for this range
    total = len(metrics)
    up_count = sum(1 for m in metrics if m.status == "up")
    uptime = round((up_count / total) * 100, 2) if total > 0 else 100.0
    
    return MetricsChartResponse(
        data=data,
        range=range_str,
        avg_response_time=avg_response,
        min_response_time=min_response,
        max_response_time=max_response,
        uptime_percentage=uptime,
    )


async def get_incidents(
    monitor_id: UUID,
    db: AsyncSession,
    limit: int = 20
) -> list[MonitorIncidentResponse]:
    """Get recent incidents for a monitor"""
    result = await db.execute(
        select(MonitorIncident).where(
            MonitorIncident.monitor_id == monitor_id
        ).order_by(desc(MonitorIncident.started_at)).limit(limit)
    )
    incidents = result.scalars().all()
    
    return [
        MonitorIncidentResponse(
            id=str(inc.id),
            monitor_id=str(inc.monitor_id),
            started_at=inc.started_at.isoformat(),
            ended_at=inc.ended_at.isoformat() if inc.ended_at else None,
            duration_seconds=inc.duration_seconds,
            error_message=inc.error_message,
            check_count=inc.check_count,
            is_resolved=bool(inc.is_resolved),
        )
        for inc in incidents
    ]
