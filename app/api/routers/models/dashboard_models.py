"""
Dashboard Pydantic Models

Schemas for the monitoring dashboard API responses.
Segregated from other models for clean architecture.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ==================== OVERVIEW STATS ====================

class DashboardOverviewStats(BaseModel):
    """Overview statistics for the dashboard header"""
    total_monitors: int
    monitors_up: int
    monitors_down: int
    monitors_paused: int
    monitors_unknown: int
    monitors_warning: int  # Monitors with response time > threshold
    
    # Global metrics
    global_uptime_percentage: float  # Weighted average uptime
    avg_response_time: Optional[float] = None  # Average across all monitors
    
    # Trends (compared to previous period)
    uptime_trend: Optional[float] = None  # +/- percentage points
    response_time_trend: Optional[float] = None  # +/- ms


# ==================== RECENT ACTIVITY ====================

class RecentIncident(BaseModel):
    """Recent incident for dashboard feed"""
    id: str
    monitor_id: str
    monitor_name: str
    monitor_type: str
    target: str
    started_at: str
    ended_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    is_resolved: bool


class RecentActivityResponse(BaseModel):
    """Recent incidents and events"""
    incidents: list[RecentIncident]
    total_incidents_24h: int
    total_downtime_minutes_24h: int


# ==================== MONITOR STATUS GRID ====================

class MonitorStatusItem(BaseModel):
    """Single monitor status for grid display"""
    id: str
    friendly_name: str
    monitor_type: str
    target: str
    current_status: str  # up, down, paused, unknown, warning
    response_time: Optional[float] = None
    uptime_percentage: Optional[float] = None
    last_check_at: Optional[str] = None


class MonitorStatusGridResponse(BaseModel):
    """All monitors status for grid view"""
    monitors: list[MonitorStatusItem]
    total: int


# ==================== RESPONSE TIME CHART ====================

class ResponseTimeDataPoint(BaseModel):
    """Aggregated response time data point"""
    timestamp: str
    avg_response_time: Optional[float] = None
    min_response_time: Optional[float] = None
    max_response_time: Optional[float] = None
    total_checks: int
    failed_checks: int


class ResponseTimeTrendResponse(BaseModel):
    """Aggregated response time trend for dashboard chart"""
    data: list[ResponseTimeDataPoint]
    range: str  # "24h" | "7d" | "30d"
    overall_avg: Optional[float] = None
    overall_uptime: float


# ==================== UPTIME BY TYPE ====================

class UptimeByTypeItem(BaseModel):
    """Uptime statistics grouped by monitor type"""
    monitor_type: str
    count: int
    uptime_percentage: float
    avg_response_time: Optional[float] = None


class UptimeByTypeResponse(BaseModel):
    """Uptime breakdown by monitor type"""
    types: list[UptimeByTypeItem]


# ==================== MAP DATA (COMING SOON) ====================

class MonitorLocation(BaseModel):
    """Monitor location for map display"""
    id: str
    friendly_name: str
    target: str
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None


class MapDataResponse(BaseModel):
    """Monitor locations for map visualization"""
    locations: list[MonitorLocation]
    coming_soon: bool = True  # Flag to indicate feature status


# ==================== WARNINGS ====================

class WarningItem(BaseModel):
    """Warning/alert item"""
    id: str
    monitor_id: str
    monitor_name: str
    warning_type: str  # "slow_response", "high_error_rate", "ssl_expiring", etc.
    message: str
    severity: str  # "low", "medium", "high"
    created_at: str


class WarningsResponse(BaseModel):
    """Active warnings list"""
    warnings: list[WarningItem]
    total: int


# ==================== FULL DASHBOARD RESPONSE ====================

class DashboardResponse(BaseModel):
    """Complete dashboard data in single response"""
    overview: DashboardOverviewStats
    recent_activity: RecentActivityResponse
    response_trend: ResponseTimeTrendResponse
    uptime_by_type: UptimeByTypeResponse
    warnings: WarningsResponse
    map_data: MapDataResponse
