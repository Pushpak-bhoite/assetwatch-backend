
# ==================== ASSETS MODELS ====================

from pydantic import BaseModel, Field
from datetime import date
from typing import Literal, Optional

from app.core.constants import ASSET_TYPES


# ==================== ASSETWATCH TYPE DEFINITIONS ====================

# All valid asset types from Wanaware

# Monitor type options
MONITOR_TYPE = Literal["performance", "availability"]

# Target type - is the target an IP address or hostname?
TARGET_TYPE = Literal["ip", "hostname"]

# Protocol options for Performance monitors
PERFORMANCE_PROTOCOL = Literal["icmp", "http", "https"]

# Circuit type options for Availability monitors
CIRCUIT_TYPE = Literal[ "broadband", "dia"]

# Check interval options (in seconds)
PERFORMANCE_INTERVAL = Literal[60, 300, 900]  # 1min, 5min, 15min
AVAILABILITY_INTERVAL = Literal[30, 60, 300, 900]  # 30sec, 1min, 5min, 15min


# ==================== ASSET SCHEMAS ====================

class AssetCreate(BaseModel):
    """
    Schema for creating a new asset.
    
    Form Fields:
    1. Asset Name (required) - User-friendly name for the asset
    2. Asset Type (required) - Select from Wanaware asset types
    3. Description (optional) - Additional details about the asset
    """
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=255, 
        description="User-friendly name for the asset (e.g., 'Main Office Router')"
    )
    asset_type: ASSET_TYPES = Field(
        ..., 
        description="Type of asset from Wanaware categories"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Optional description of the asset"
    )


class AssetUpdate(BaseModel):
    """Schema for updating an existing asset - all fields optional"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    asset_type: Optional[ASSET_TYPES] = None
    description: Optional[str] = Field(None, max_length=1000)


class AssetResponse(BaseModel):
    """Schema for asset in list responses"""
    id: str
    name: str
    asset_type: str
    description: Optional[str]
    created_at: str
    updated_at: str
    monitor_count: int = 0  # Number of monitors attached
    
    class Config:
        from_attributes = True


class MonitorResponse(BaseModel):
    """Schema for monitor response"""
    id: str
    asset_id: str
    monitor_type: str  # "performance" | "availability"
    target: str
    target_type: str  # "ip" | "hostname"
    port: Optional[int]
    protocol: Optional[str]  # For performance monitors
    circuit_type: Optional[str]  # For availability monitors
    check_interval: int  # In seconds
    is_active: bool
    current_status: str  # "up" | "down" | "unknown"
    last_check_at: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class AssetDetailResponse(AssetResponse):
    """Detailed asset response including attached monitors"""
    monitors: list[MonitorResponse] = []


# ==================== MONITOR SCHEMAS ====================

class MonitorBaseCreate(BaseModel):
    """
    Base fields for creating any monitor.
    These are common to both Performance and Availability monitors.
    
    Form Fields (common):
    3. Enter Target (required) - IP address or hostname to monitor
    4. Target Type (required) - Whether target is IP or hostname
    5. Port (optional) - Port number for specific service monitoring
    """
    target: str = Field(
        ..., 
        description="IP address or hostname to monitor (e.g., '192.168.1.1' or 'google.com')"
    )
    target_type: TARGET_TYPE = Field(
        ..., 
        description="Specify if target is an 'ip' address or 'hostname'"
    )
    port: Optional[int] = Field(
        None, 
        ge=1, 
        le=65535, 
        description="Optional port number (1-65535)"
    )


class PerformanceMonitorCreate(MonitorBaseCreate):
    """
    Schema for creating a Performance Monitor.
    
    Performance monitors track:
    - CPU Usage (%)
    - Memory Usage (%)
    - Disk I/O (MB/s)
    - Latency (ms)
    
    Form Fields:
    1. Select Asset (from URL path)
    2. Monitor Type = "performance"
    3. Enter Target - IP or hostname
    4. Target Type - ip | hostname
    5. Port (optional)
    6. Protocol - ICMP | HTTP | HTTPS
    7. Check Interval - 1min | 5min | 15min
    """
    monitor_type: Literal["performance"] = "performance"
    protocol: PERFORMANCE_PROTOCOL = Field(
        ..., 
        description="Protocol for monitoring: 'icmp' for ping, 'http' or 'https' for web endpoints"
    )
    check_interval: PERFORMANCE_INTERVAL = Field(
        300,  # Default 5 minutes
        description="Check interval in seconds: 60 (1min), 300 (5min), or 900 (15min)"
    )


class AvailabilityMonitorCreate(MonitorBaseCreate):
    """
    Schema for creating an Availability Monitor.
    
    Availability monitors track:
    - Status (UP/DOWN)
    - Response Time (ms)
    - Uptime Percentage (%)
    - Packet Loss (%)
    
    Form Fields:
    1. Select Asset (from URL path)
    2. Monitor Type = "availability"
    3. Enter Target - IP or hostname
    4. Target Type - ip | hostname
    5. Port (optional)
    6. Circuit Type - DIA | Broadband
    7. Check Interval - 30sec | 1min | 5min | 15min
    """
    monitor_type: Literal["availability"] = "availability"
    circuit_type: CIRCUIT_TYPE = Field(
        ..., 
        description="Circuit type: 'dia' (Dedicated Internet Access) or 'broadband'"
    )
    check_interval: AVAILABILITY_INTERVAL = Field(
        60,  # Default 1 minute
        description="Check interval in seconds: 30, 60 (1min), 300 (5min), or 900 (15min)"
    )


class MonitorUpdate(BaseModel):
    """Schema for updating a monitor - all fields optional"""
    target: Optional[str] = None
    target_type: Optional[TARGET_TYPE] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    protocol: Optional[PERFORMANCE_PROTOCOL] = None
    circuit_type: Optional[CIRCUIT_TYPE] = None
    check_interval: Optional[int] = Field(None, ge=30, le=900)
    is_active: Optional[bool] = None


# ==================== METRIC SCHEMAS ====================

class PerformanceMetricResponse(BaseModel):
    """
    Schema for a single performance metric data point.
    
    Data returned:
    - CPU Usage: e.g., "73%"
    - Memory Usage: e.g., "62%"
    - Disk I/O: e.g., "120MB/s"
    - Latency: e.g., "132ms"
    """
    id: str
    cpu_usage: float  # Percentage (0-100)
    memory_usage: float  # Percentage (0-100)
    disk_io: float  # MB/s
    latency: float  # Milliseconds
    timestamp: str
    
    class Config:
        from_attributes = True


class AvailabilityMetricResponse(BaseModel):
    """
    Schema for a single availability metric data point.
    
    Data returned:
    - Status: "UP" or "DOWN"
    - Response Time: e.g., "245ms"
    - Uptime: e.g., "99.98%"
    - Packet Loss: e.g., "0%"
    """
    id: str
    status: str  # "UP" | "DOWN"
    response_time: float  # Milliseconds
    uptime_percentage: float  # Percentage (0-100)
    packet_loss: float  # Percentage (0-100)
    timestamp: str
    
    class Config:
        from_attributes = True


class PerformanceMetricsListResponse(BaseModel):
    """Response containing list of performance metrics with metadata"""
    monitor_id: str
    asset_id: str
    asset_name: str
    monitor_type: str
    days: int
    total_records: int
    data: list[PerformanceMetricResponse]


class AvailabilityMetricsListResponse(BaseModel):
    """Response containing list of availability metrics with metadata"""
    monitor_id: str
    asset_id: str
    asset_name: str
    monitor_type: str
    days: int
    total_records: int
    data: list[AvailabilityMetricResponse]


# ==================== SUMMARY/DASHBOARD SCHEMAS ====================

class PerformanceSummary(BaseModel):
    """
    Summary statistics for performance metrics.
    Each metric has: avg, min, max, current values.
    """
    cpu: dict  # {"avg": float, "min": float, "max": float, "current": float}
    memory: dict
    disk_io: dict
    latency: dict


class AvailabilitySummary(BaseModel):
    """
    Summary statistics for availability metrics.
    Shows overall availability health of the asset.
    """
    current_status: str  # "UP" | "DOWN"
    uptime_percentage: float  # Overall uptime
    avg_response_time: float  # Average response time in ms
    total_checks: int  # Total number of checks performed
    up_count: int  # Number of successful checks
    down_count: int  # Number of failed checks
    last_downtime: Optional[str]  # ISO timestamp of last DOWN status


class MonitoringSummaryResponse(BaseModel):
    """Complete monitoring summary for an asset"""
    asset_id: str
    asset_name: str
    asset_type: str
    days: int  # Number of days of data included
    performance: Optional[PerformanceSummary]  # None if no performance monitors
    availability: Optional[AvailabilitySummary]  # None if no availability monitors


class DashboardStats(BaseModel):
    """
    Overall dashboard statistics for the user.
    Provides a bird's-eye view of all assets and monitors.
    """
    total_assets: int
    total_monitors: int
    active_monitors: int
    assets_up: int  # Monitors with "up" status
    assets_down: int  # Monitors with "down" status
    assets_unknown: int  # Monitors with "unknown" status
    avg_uptime: float  # Average uptime across all availability monitors
    recent_alerts: list[dict]  # Recent DOWN status events
    class Config:
        from_attributes = True

