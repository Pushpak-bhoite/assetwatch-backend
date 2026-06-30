

# ==================== STANDALONE MONITOR SCHEMAS (UptimeRobot-style) ====================

from pydantic import BaseModel, Field
from typing import Literal, Optional
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


class SparklinePoint(BaseModel):
    """Single data point for sparkline visualization"""
    response_time: Optional[float] = None  # null = failed/timeout
    status: str  # "up" | "down"
    timestamp: str


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
    
    # Sparkline data for response time visualization
    sparkline_data: list[SparklinePoint] = []
    sparkline_period: Optional[str] = None  # e.g., "last 15 mins", "last 2.5 hrs"
    
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