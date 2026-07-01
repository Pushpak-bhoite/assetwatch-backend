"""
Dashboard API Router

Provides endpoints for the monitoring dashboard.
Segregated from other routers for clean architecture.

Endpoints:
- GET /dashboard - Full dashboard data
- GET /dashboard/overview - Overview stats only
- GET /dashboard/activity - Recent activity
- GET /dashboard/grid - Monitor status grid
- GET /dashboard/trend - Response time trend
- GET /dashboard/uptime-by-type - Uptime grouped by type
- GET /dashboard/warnings - Active warnings
- GET /dashboard/map - Map data (Coming Soon)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app.core.db import User, get_db
from app.users import current_active_user
from app.api.routers.models.dashboard_models import (
    DashboardOverviewStats,
    RecentActivityResponse,
    MonitorStatusGridResponse,
    ResponseTimeTrendResponse,
    UptimeByTypeResponse,
    WarningsResponse,
    MapDataResponse,
    DashboardResponse,
)
from app.api.routers.services.dashboard_services import (
    get_overview_stats,
    get_recent_activity,
    get_monitor_status_grid,
    get_response_time_trend,
    get_uptime_by_type,
    get_warnings,
    get_map_data,
)


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ==================== FULL DASHBOARD ====================

@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    trend_range: Literal["24h", "7d", "30d"] = Query(default="24h", description="Time range for trend chart"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get complete dashboard data in a single request.
    
    Combines all dashboard components:
    - Overview statistics
    - Recent activity/incidents
    - Response time trend
    - Uptime by monitor type
    - Active warnings
    - Map data (placeholder)
    """
    overview = await get_overview_stats(current_user.id, db)
    activity = await get_recent_activity(current_user.id, db)
    trend = await get_response_time_trend(current_user.id, db, trend_range)
    uptime_types = await get_uptime_by_type(current_user.id, db)
    warnings = await get_warnings(current_user.id, db)
    map_data = await get_map_data(current_user.id, db)
    
    return DashboardResponse(
        overview=overview,
        recent_activity=activity,
        response_trend=trend,
        uptime_by_type=uptime_types,
        warnings=warnings,
        map_data=map_data,
    )


# ==================== INDIVIDUAL ENDPOINTS ====================

@router.get("/overview", response_model=DashboardOverviewStats)
async def get_dashboard_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get overview statistics only.
    
    Returns:
    - Monitor counts by status (up, down, paused, warning)
    - Global uptime percentage
    - Average response time
    - Trends compared to previous period
    """
    return await get_overview_stats(current_user.id, db)


@router.get("/activity", response_model=RecentActivityResponse)
async def get_dashboard_activity(
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent incidents"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get recent incidents and activity.
    
    Returns:
    - Recent incidents list
    - 24-hour incident count
    - 24-hour total downtime
    """
    return await get_recent_activity(current_user.id, db, limit)


@router.get("/grid", response_model=MonitorStatusGridResponse)
async def get_dashboard_grid(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get all monitors status for grid display.
    
    Returns compact monitor info for quick status overview.
    """
    return await get_monitor_status_grid(current_user.id, db)


@router.get("/trend", response_model=ResponseTimeTrendResponse)
async def get_dashboard_trend(
    range: Literal["24h", "7d", "30d"] = Query(default="24h", description="Time range"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get aggregated response time trend for chart.
    
    Aggregates metrics across all monitors:
    - 24h: Hourly buckets
    - 7d: 6-hour buckets
    - 30d: Daily buckets
    """
    return await get_response_time_trend(current_user.id, db, range)


@router.get("/uptime-by-type", response_model=UptimeByTypeResponse)
async def get_dashboard_uptime_by_type(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get uptime statistics grouped by monitor type.
    
    Returns uptime percentage and count for each type (http, ping, port, dns).
    """
    return await get_uptime_by_type(current_user.id, db)


@router.get("/warnings", response_model=WarningsResponse)
async def get_dashboard_warnings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get active warnings for the user's monitors.
    
    Warning types:
    - slow_response: Response time above threshold
    - high_error_rate: Error rate above 10% in last hour
    """
    return await get_warnings(current_user.id, db)


@router.get("/map", response_model=MapDataResponse)
async def get_dashboard_map(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get monitor locations for map display.
    
    NOTE: This endpoint is a placeholder. Full implementation requires
    IP geolocation service integration.
    
    Returns monitors with coming_soon=True flag.
    """
    return await get_map_data(current_user.id, db)
