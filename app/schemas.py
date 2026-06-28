"""
AssetWatch Pydantic Schemas

This module defines all request/response schemas for the API.
Based on Wanaware's form fields and data structures.

Schema Categories:
- Post schemas (kept for backwards compatibility)
- User schemas (fastapi-users integration)
- Asset schemas (create, update, response)
- Monitor schemas (performance and availability)
- Metric schemas (performance and availability data)
- Summary/Dashboard schemas (aggregated data)
"""

from pydantic import BaseModel, Field
from datetime import date
from fastapi_users import schemas
from typing import Literal, Optional
import uuid


# ==================== POST SCHEMAS (kept for backwards compatibility) ====================

class PostCreate(BaseModel):
    """Schema for creating a blog post"""
    title: str
    content: str
    caption: str


class PostResponse(BaseModel):
    """Schema for post response"""
    id: int
    title: str
    content: str
    caption: str

    class Config: 
        from_attributes = True # this is for returning id along with data when user makes post request

class FilePost(BaseModel):
    """Schema for file post response"""
    id: int
    caption: str
    file_url: str
    file_name: str
    created_At: date
    
    class Config: 
        from_attributes = True 


# ==================== USER SCHEMAS ====================

class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data"""
    name: str
    organization_type: str
    parent_organization_id: Optional[uuid.UUID] = None



class UserCreate(schemas.BaseUserCreate):
    """Schema for creating a user"""
    name: str  # Required: used as organization name
    organization_type: str = "customer"  # Default to customer for self-registration



class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating a user"""
    name: Optional[str] = None


# ==================== ASSETWATCH TYPE DEFINITIONS ====================

# All valid asset types from Wanaware
# These match exactly what's in the Wanaware frontend
ASSET_TYPES = Literal[
    # Circuit - Internet types (different connection technologies)
    "Circuit-Internet-Cable Broadband",
    "Circuit-Internet-Fiber Broadband",
    "Circuit-Internet-Copper Broadband",
    "Circuit-Internet-Wireless Broadband",
    "Circuit-Internet-Wireless 4G Broadband",
    "Circuit-Internet-Wireless 5G Broadband",
    "Circuit-Internet-Satellite Broadband",
    "Circuit-Internet-Dedicated Internet Access",
    # Circuit - Enterprise connection types
    "Circuit-MPLS",
    "Circuit-Private Line",
    "Circuit-PRI",
    "Circuit-POTS",
    "Circuit-SIP",
    # Network Assets (physical/virtual network equipment)
    "Network Asset-IP Block",
    "Network Asset-Router",
    "Network Asset-SD-WAN",
    "Network Asset-Switch",
    "Network Asset-Wireless Access Point (WAP)",
    "Network Asset-Load Balancer",
    # Security Assets (security infrastructure)
    "Security Asset-Firewall",
    "Security Asset-Intrusion Detection System (IDS)",
    "Security Asset-Intrusion Prevention System (IPS)",
    "Security Asset-Network Detection & Response (NDR)",
    "Security Asset-Web Application Firewall (WAF)",
    # Compute Assets (servers and endpoints)
    "Compute Asset-Server",
    "Compute Asset-Laptop",
    "Compute Asset-Desktop",
    # Storage Assets
    "Storage Asset-Storage Area Network (SAN)",
]

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


# ==================== STANDALONE MONITOR SCHEMAS (UptimeRobot-style) ====================

# Monitor types for standalone monitors
STANDALONE_MONITOR_TYPE = Literal["http", "ping", "port", "dns"]

# Check interval options
STANDALONE_CHECK_INTERVAL = Literal["30s", "1m", "5m", "15m", "30m", "1hr", "12hr"]

# DNS Record types
DNS_RECORD_TYPE = Literal["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA"]


class StandaloneMonitorBase(BaseModel):
    """Base schema for all standalone monitor types"""
    friendly_name: str = Field(..., min_length=1, max_length=255, description="Display name for the monitor")
    tags: Optional[list[str]] = Field(default=[], description="Tags for organizing monitors")
    notify_email: bool = Field(default=True, description="Whether to send email notifications")
    check_interval: str = Field(default="5m", description="Check interval (30s, 1m, 5m, 15m, 30m, 1hr, 12hr)")


class HTTPMonitorCreate(StandaloneMonitorBase):
    """Schema for creating an HTTP(S) monitor"""
    monitor_type: Literal["http"] = "http"
    url: str = Field(..., description="URL to monitor (must start with http:// or https://)")


class PingMonitorCreate(StandaloneMonitorBase):
    """Schema for creating a Ping monitor"""
    monitor_type: Literal["ping"] = "ping"
    host: str = Field(..., description="IP address or hostname to ping")


class PortMonitorCreate(StandaloneMonitorBase):
    """Schema for creating a Port monitor"""
    monitor_type: Literal["port"] = "port"
    host: str = Field(..., description="URL, IP address or hostname to monitor")
    port: int = Field(..., ge=1, le=65535, description="TCP port number to monitor")
    port_name: Optional[str] = Field(None, description="Name of the port service (e.g., 'HTTP', 'SSH')")


class DNSMonitorCreate(StandaloneMonitorBase):
    """Schema for creating a DNS monitor"""
    monitor_type: Literal["dns"] = "dns"
    hostname: str = Field(..., description="Hostname to resolve")
    dns_server: Optional[str] = Field(None, description="DNS server to query (optional)")
    record_type: str = Field(default="A", description="DNS record type to check")
    expected_value: Optional[str] = Field(None, description="Expected DNS response value")


class StandaloneMonitorUpdate(BaseModel):
    """Schema for updating a standalone monitor"""
    friendly_name: Optional[str] = Field(None, min_length=1, max_length=255)
    tags: Optional[list[str]] = None
    notify_email: Optional[bool] = None
    check_interval: Optional[str] = None
    is_active: Optional[bool] = None
    
    # Type-specific fields (for updating target)
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    port_name: Optional[str] = None
    hostname: Optional[str] = None
    dns_server: Optional[str] = None
    record_type: Optional[str] = None
    expected_value: Optional[str] = None


class StandaloneMonitorResponse(BaseModel):
    """Schema for standalone monitor response"""
    id: str
    user_id: str
    monitor_type: str
    friendly_name: str
    target: str  # The URL/host/hostname depending on type
    tags: list[str]
    notify_email: bool
    check_interval: str
    check_interval_seconds: int
    is_active: bool
    current_status: str  # "up" | "down" | "unknown" | "paused"
    last_check_at: Optional[str] = None
    response_time: Optional[float] = None
    uptime_percentage: Optional[float] = None
    created_at: str
    updated_at: str
    
    # Type-specific fields
    port: Optional[int] = None
    port_name: Optional[str] = None
    dns_server: Optional[str] = None
    record_type: Optional[str] = None
    expected_value: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaginatedStandaloneMonitorsResponse(BaseModel):
    """Schema for paginated standalone monitors list response"""
    data: list[StandaloneMonitorResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class StandaloneMonitorStats(BaseModel):
    """Overview stats for standalone monitors"""
    total: int
    up: int
    down: int
    paused: int
    unknown: int


class StandaloneMonitorMetricResponse(BaseModel):
    """Schema for standalone monitor metric response"""
    id: str
    monitor_id: str
    status: str
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    resolved_value: Optional[str] = None
    timestamp: str
    
    class Config:
        from_attributes = True