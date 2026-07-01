"""
Dashboard Services

Business logic for the monitoring dashboard.
Segregated from other services for clean architecture.
"""

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

from app.core.db import StandaloneMonitor, StandaloneMonitorMetric, MonitorIncident
from app.api.routers.models.dashboard_models import (
    DashboardOverviewStats,
    RecentIncident,
    RecentActivityResponse,
    MonitorStatusItem,
    MonitorStatusGridResponse,
    ResponseTimeDataPoint,
    ResponseTimeTrendResponse,
    UptimeByTypeItem,
    UptimeByTypeResponse,
    MapDataResponse,
    MonitorLocation,
    WarningItem,
    WarningsResponse,
)

# ==================== CONSTANTS ====================

# Response time threshold for "warning" status (ms)
WARNING_RESPONSE_THRESHOLD = 1000  # 1 second


# ==================== OVERVIEW STATS ====================

async def get_overview_stats(
    user_id: UUID,
    db: AsyncSession
) -> DashboardOverviewStats:
    """
    Get overview statistics for dashboard header.
    
    Calculates:
    - Monitor counts by status
    - Warning count (slow response monitors)
    - Global uptime percentage
    - Average response time
    - Trends compared to previous period
    """
    # Get all user's monitors
    result = await db.execute(
        select(StandaloneMonitor).where(StandaloneMonitor.user_id == user_id)
    )
    monitors = result.scalars().all()
    
    if not monitors:
        return DashboardOverviewStats(
            total_monitors=0,
            monitors_up=0,
            monitors_down=0,
            monitors_paused=0,
            monitors_unknown=0,
            monitors_warning=0,
            global_uptime_percentage=100.0,
            avg_response_time=None,
            uptime_trend=None,
            response_time_trend=None,
        )
    
    # Count by status
    monitors_up = 0
    monitors_down = 0
    monitors_paused = 0
    monitors_unknown = 0
    monitors_warning = 0
    
    for monitor in monitors:
        if not monitor.is_active:
            monitors_paused += 1
        elif monitor.current_status == "up":
            # Check if response time is above warning threshold
            if monitor.response_time and monitor.response_time > WARNING_RESPONSE_THRESHOLD:
                monitors_warning += 1
            else:
                monitors_up += 1
        elif monitor.current_status == "down":
            monitors_down += 1
        else:
            monitors_unknown += 1
    
    # Calculate global uptime (last 30 days)
    since_30d = datetime.utcnow() - timedelta(days=30)
    monitor_ids = [m.id for m in monitors if m.is_active]
    
    if monitor_ids:
        metrics_result = await db.execute(
            select(StandaloneMonitorMetric).where(
                and_(
                    StandaloneMonitorMetric.monitor_id.in_(monitor_ids),
                    StandaloneMonitorMetric.timestamp >= since_30d
                )
            )
        )
        metrics = metrics_result.scalars().all()
        
        if metrics:
            up_count = sum(1 for m in metrics if m.status == "up")
            global_uptime = round((up_count / len(metrics)) * 100, 2)
            
            # Average response time
            response_times = [m.response_time for m in metrics if m.response_time is not None]
            avg_response = round(sum(response_times) / len(response_times), 2) if response_times else None
        else:
            global_uptime = 100.0
            avg_response = None
    else:
        global_uptime = 100.0
        avg_response = None
    
    # Calculate trends (compare last 24h vs previous 24h)
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_48h = now - timedelta(hours=48)
    
    uptime_trend = None
    response_trend = None
    
    if monitor_ids:
        # Current period metrics
        current_result = await db.execute(
            select(StandaloneMonitorMetric).where(
                and_(
                    StandaloneMonitorMetric.monitor_id.in_(monitor_ids),
                    StandaloneMonitorMetric.timestamp >= since_24h
                )
            )
        )
        current_metrics = current_result.scalars().all()
        
        # Previous period metrics
        prev_result = await db.execute(
            select(StandaloneMonitorMetric).where(
                and_(
                    StandaloneMonitorMetric.monitor_id.in_(monitor_ids),
                    StandaloneMonitorMetric.timestamp >= since_48h,
                    StandaloneMonitorMetric.timestamp < since_24h
                )
            )
        )
        prev_metrics = prev_result.scalars().all()
        
        if current_metrics and prev_metrics:
            # Uptime trend
            current_uptime = (sum(1 for m in current_metrics if m.status == "up") / len(current_metrics)) * 100
            prev_uptime = (sum(1 for m in prev_metrics if m.status == "up") / len(prev_metrics)) * 100
            uptime_trend = round(current_uptime - prev_uptime, 2)
            
            # Response time trend
            current_rt = [m.response_time for m in current_metrics if m.response_time]
            prev_rt = [m.response_time for m in prev_metrics if m.response_time]
            if current_rt and prev_rt:
                current_avg_rt = sum(current_rt) / len(current_rt)
                prev_avg_rt = sum(prev_rt) / len(prev_rt)
                response_trend = round(current_avg_rt - prev_avg_rt, 2)
    
    return DashboardOverviewStats(
        total_monitors=len(monitors),
        monitors_up=monitors_up,
        monitors_down=monitors_down,
        monitors_paused=monitors_paused,
        monitors_unknown=monitors_unknown,
        monitors_warning=monitors_warning,
        global_uptime_percentage=global_uptime,
        avg_response_time=avg_response,
        uptime_trend=uptime_trend,
        response_time_trend=response_trend,
    )


# ==================== RECENT ACTIVITY ====================

async def get_recent_activity(
    user_id: UUID,
    db: AsyncSession,
    limit: int = 10
) -> RecentActivityResponse:
    """
    Get recent incidents and activity for the dashboard feed.
    """
    # Get user's monitor IDs
    monitors_result = await db.execute(
        select(StandaloneMonitor).where(StandaloneMonitor.user_id == user_id)
    )
    monitors = {str(m.id): m for m in monitors_result.scalars().all()}
    monitor_ids = list(monitors.keys())
    
    if not monitor_ids:
        return RecentActivityResponse(
            incidents=[],
            total_incidents_24h=0,
            total_downtime_minutes_24h=0,
        )
    
    # Convert to UUIDs for query
    monitor_uuids = [UUID(mid) for mid in monitor_ids]
    
    # Get recent incidents
    incidents_result = await db.execute(
        select(MonitorIncident).where(
            MonitorIncident.monitor_id.in_(monitor_uuids)
        ).order_by(MonitorIncident.started_at.desc()).limit(limit)
    )
    incidents = incidents_result.scalars().all()
    
    # Get 24h stats
    since_24h = datetime.utcnow() - timedelta(hours=24)
    incidents_24h_result = await db.execute(
        select(MonitorIncident).where(
            and_(
                MonitorIncident.monitor_id.in_(monitor_uuids),
                MonitorIncident.started_at >= since_24h
            )
        )
    )
    incidents_24h = incidents_24h_result.scalars().all()
    
    # Calculate total downtime
    now = datetime.utcnow()
    total_downtime_seconds = 0
    for inc in incidents_24h:
        end_time = inc.ended_at or now
        start = max(inc.started_at, since_24h)
        if end_time > start:
            total_downtime_seconds += int((end_time - start).total_seconds())
    
    # Build response
    recent_incidents = []
    for inc in incidents:
        monitor = monitors.get(str(inc.monitor_id))
        if monitor:
            recent_incidents.append(RecentIncident(
                id=str(inc.id),
                monitor_id=str(inc.monitor_id),
                monitor_name=monitor.friendly_name,
                monitor_type=monitor.monitor_type,
                target=monitor.target,
                started_at=inc.started_at.isoformat(),
                ended_at=inc.ended_at.isoformat() if inc.ended_at else None,
                duration_seconds=inc.duration_seconds,
                error_message=inc.error_message,
                is_resolved=bool(inc.is_resolved),
            ))
    
    return RecentActivityResponse(
        incidents=recent_incidents,
        total_incidents_24h=len(incidents_24h),
        total_downtime_minutes_24h=total_downtime_seconds // 60,
    )


# ==================== MONITOR STATUS GRID ====================

async def get_monitor_status_grid(
    user_id: UUID,
    db: AsyncSession
) -> MonitorStatusGridResponse:
    """
    Get all monitors with their current status for grid display.
    """
    result = await db.execute(
        select(StandaloneMonitor).where(
            StandaloneMonitor.user_id == user_id
        ).order_by(StandaloneMonitor.friendly_name)
    )
    monitors = result.scalars().all()
    
    # Get 30-day uptime for each monitor
    since_30d = datetime.utcnow() - timedelta(days=30)
    
    items = []
    for monitor in monitors:
        # Calculate uptime
        metrics_result = await db.execute(
            select(StandaloneMonitorMetric).where(
                and_(
                    StandaloneMonitorMetric.monitor_id == monitor.id,
                    StandaloneMonitorMetric.timestamp >= since_30d
                )
            )
        )
        metrics = metrics_result.scalars().all()
        
        uptime = None
        if metrics:
            up_count = sum(1 for m in metrics if m.status == "up")
            uptime = round((up_count / len(metrics)) * 100, 2)
        
        # Determine status (including warning)
        status = "paused" if not monitor.is_active else monitor.current_status
        if status == "up" and monitor.response_time and monitor.response_time > WARNING_RESPONSE_THRESHOLD:
            status = "warning"
        
        items.append(MonitorStatusItem(
            id=str(monitor.id),
            friendly_name=monitor.friendly_name,
            monitor_type=monitor.monitor_type,
            target=monitor.target,
            current_status=status,
            response_time=monitor.response_time,
            uptime_percentage=uptime,
            last_check_at=monitor.last_check_at.isoformat() if monitor.last_check_at else None,
        ))
    
    return MonitorStatusGridResponse(
        monitors=items,
        total=len(items),
    )


# ==================== RESPONSE TIME TREND ====================

async def get_response_time_trend(
    user_id: UUID,
    db: AsyncSession,
    range_str: str = "24h"
) -> ResponseTimeTrendResponse:
    """
    Get aggregated response time trend for dashboard chart.
    
    Aggregates metrics by hour for 24h/7d, by day for 30d.
    """
    # Parse range
    range_map = {
        "24h": (timedelta(hours=24), timedelta(hours=1)),
        "7d": (timedelta(days=7), timedelta(hours=6)),
        "30d": (timedelta(days=30), timedelta(days=1)),
    }
    
    if range_str not in range_map:
        range_str = "24h"
    
    time_delta, bucket_size = range_map[range_str]
    since = datetime.utcnow() - time_delta
    
    # Get user's active monitor IDs
    monitors_result = await db.execute(
        select(StandaloneMonitor.id).where(
            and_(
                StandaloneMonitor.user_id == user_id,
                StandaloneMonitor.is_active == 1
            )
        )
    )
    monitor_ids = [row[0] for row in monitors_result.fetchall()]
    
    if not monitor_ids:
        return ResponseTimeTrendResponse(
            data=[],
            range=range_str,
            overall_avg=None,
            overall_uptime=100.0,
        )
    
    # Get all metrics in range
    metrics_result = await db.execute(
        select(StandaloneMonitorMetric).where(
            and_(
                StandaloneMonitorMetric.monitor_id.in_(monitor_ids),
                StandaloneMonitorMetric.timestamp >= since
            )
        ).order_by(StandaloneMonitorMetric.timestamp)
    )
    metrics = metrics_result.scalars().all()
    
    if not metrics:
        return ResponseTimeTrendResponse(
            data=[],
            range=range_str,
            overall_avg=None,
            overall_uptime=100.0,
        )
    
    # Bucket metrics
    buckets: dict[datetime, list] = {}
    bucket_seconds = int(bucket_size.total_seconds())
    
    for metric in metrics:
        # Round timestamp to bucket
        ts = metric.timestamp.replace(second=0, microsecond=0)
        if bucket_seconds >= 3600:  # Hour or more
            ts = ts.replace(minute=0)
        if bucket_seconds >= 86400:  # Day
            ts = ts.replace(hour=0)
        
        if ts not in buckets:
            buckets[ts] = []
        buckets[ts].append(metric)
    
    # Build data points
    data = []
    for ts in sorted(buckets.keys()):
        bucket_metrics = buckets[ts]
        
        response_times = [m.response_time for m in bucket_metrics if m.response_time is not None]
        failed = sum(1 for m in bucket_metrics if m.status == "down")
        
        data.append(ResponseTimeDataPoint(
            timestamp=ts.isoformat(),
            avg_response_time=round(sum(response_times) / len(response_times), 2) if response_times else None,
            min_response_time=round(min(response_times), 2) if response_times else None,
            max_response_time=round(max(response_times), 2) if response_times else None,
            total_checks=len(bucket_metrics),
            failed_checks=failed,
        ))
    
    # Overall stats
    all_rt = [m.response_time for m in metrics if m.response_time is not None]
    overall_avg = round(sum(all_rt) / len(all_rt), 2) if all_rt else None
    up_count = sum(1 for m in metrics if m.status == "up")
    overall_uptime = round((up_count / len(metrics)) * 100, 2)
    
    return ResponseTimeTrendResponse(
        data=data,
        range=range_str,
        overall_avg=overall_avg,
        overall_uptime=overall_uptime,
    )


# ==================== UPTIME BY TYPE ====================

async def get_uptime_by_type(
    user_id: UUID,
    db: AsyncSession
) -> UptimeByTypeResponse:
    """
    Get uptime statistics grouped by monitor type.
    """
    # Get user's monitors grouped by type
    monitors_result = await db.execute(
        select(StandaloneMonitor).where(StandaloneMonitor.user_id == user_id)
    )
    monitors = monitors_result.scalars().all()
    
    if not monitors:
        return UptimeByTypeResponse(types=[])
    
    # Group by type
    types_data: dict[str, list[StandaloneMonitor]] = {}
    for monitor in monitors:
        if monitor.monitor_type not in types_data:
            types_data[monitor.monitor_type] = []
        types_data[monitor.monitor_type].append(monitor)
    
    # Calculate stats for each type
    since_30d = datetime.utcnow() - timedelta(days=30)
    items = []
    
    for monitor_type, type_monitors in types_data.items():
        monitor_ids = [m.id for m in type_monitors if m.is_active]
        
        if monitor_ids:
            metrics_result = await db.execute(
                select(StandaloneMonitorMetric).where(
                    and_(
                        StandaloneMonitorMetric.monitor_id.in_(monitor_ids),
                        StandaloneMonitorMetric.timestamp >= since_30d
                    )
                )
            )
            metrics = metrics_result.scalars().all()
            
            if metrics:
                up_count = sum(1 for m in metrics if m.status == "up")
                uptime = round((up_count / len(metrics)) * 100, 2)
                
                response_times = [m.response_time for m in metrics if m.response_time is not None]
                avg_rt = round(sum(response_times) / len(response_times), 2) if response_times else None
            else:
                uptime = 100.0
                avg_rt = None
        else:
            uptime = 100.0
            avg_rt = None
        
        items.append(UptimeByTypeItem(
            monitor_type=monitor_type,
            count=len(type_monitors),
            uptime_percentage=uptime,
            avg_response_time=avg_rt,
        ))
    
    # Sort by count descending
    items.sort(key=lambda x: x.count, reverse=True)
    
    return UptimeByTypeResponse(types=items)


# ==================== WARNINGS ====================

async def get_warnings(
    user_id: UUID,
    db: AsyncSession
) -> WarningsResponse:
    """
    Get active warnings for the user's monitors.
    
    Warning types:
    - slow_response: Response time consistently above threshold
    - high_error_rate: Error rate above threshold in last hour
    - ssl_expiring: SSL certificate expiring soon (Coming Soon)
    """
    warnings = []
    
    # Get user's monitors
    monitors_result = await db.execute(
        select(StandaloneMonitor).where(
            and_(
                StandaloneMonitor.user_id == user_id,
                StandaloneMonitor.is_active == 1
            )
        )
    )
    monitors = monitors_result.scalars().all()
    
    since_1h = datetime.utcnow() - timedelta(hours=1)
    now = datetime.utcnow()
    
    for monitor in monitors:
        # Check for slow response
        if monitor.response_time and monitor.response_time > WARNING_RESPONSE_THRESHOLD:
            warnings.append(WarningItem(
                id=f"slow_{monitor.id}",
                monitor_id=str(monitor.id),
                monitor_name=monitor.friendly_name,
                warning_type="slow_response",
                message=f"Response time is {int(monitor.response_time)}ms (threshold: {WARNING_RESPONSE_THRESHOLD}ms)",
                severity="medium",
                created_at=now.isoformat(),
            ))
        
        # Check for high error rate in last hour
        metrics_result = await db.execute(
            select(StandaloneMonitorMetric).where(
                and_(
                    StandaloneMonitorMetric.monitor_id == monitor.id,
                    StandaloneMonitorMetric.timestamp >= since_1h
                )
            )
        )
        metrics = metrics_result.scalars().all()
        
        if metrics:
            error_count = sum(1 for m in metrics if m.status == "down")
            error_rate = (error_count / len(metrics)) * 100
            
            if error_rate >= 10 and error_rate < 100:  # 10-99% errors = warning
                warnings.append(WarningItem(
                    id=f"errors_{monitor.id}",
                    monitor_id=str(monitor.id),
                    monitor_name=monitor.friendly_name,
                    warning_type="high_error_rate",
                    message=f"Error rate is {error_rate:.1f}% in the last hour ({error_count}/{len(metrics)} checks failed)",
                    severity="high" if error_rate >= 50 else "medium",
                    created_at=now.isoformat(),
                ))
    
    return WarningsResponse(
        warnings=warnings,
        total=len(warnings),
    )


# ==================== MAP DATA (COMING SOON) ====================

async def get_map_data(
    user_id: UUID,
    db: AsyncSession
) -> MapDataResponse:
    """
    Get monitor locations for map display.
    
    NOTE: This is a placeholder. IP geolocation would require:
    - Resolving hostnames to IPs
    - Using a geolocation service (MaxMind, ip-api, etc.)
    
    For now, returns monitors with coming_soon=True flag.
    """
    # Get user's monitors
    monitors_result = await db.execute(
        select(StandaloneMonitor).where(StandaloneMonitor.user_id == user_id)
    )
    monitors = monitors_result.scalars().all()
    
    locations = []
    for monitor in monitors:
        status = "paused" if not monitor.is_active else monitor.current_status
        if status == "up" and monitor.response_time and monitor.response_time > WARNING_RESPONSE_THRESHOLD:
            status = "warning"
        
        locations.append(MonitorLocation(
            id=str(monitor.id),
            friendly_name=monitor.friendly_name,
            target=monitor.target,
            status=status,
            latitude=None,  # Would be populated by geolocation service
            longitude=None,
            city=None,
            country=None,
        ))
    
    return MapDataResponse(
        locations=locations,
        coming_soon=True,
    )
