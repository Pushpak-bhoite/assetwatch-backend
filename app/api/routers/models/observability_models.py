
# ==================== RESPONSE SCHEMAS ====================

from pydantic import BaseModel, Field
from typing import Literal, Optional

class MonitorSummary(BaseModel):
    """Summary of monitors for an asset"""
    total: int = 0
    performance_count: int = 0
    availability_count: int = 0
    up_count: int = 0
    down_count: int = 0
    unknown_count: int = 0
    active_count: int = 0
    paused_count: int = 0


class ObservabilityAssetItem(BaseModel):
    """Schema for observability asset list item"""
    id: str
    name: str
    asset_type: str
    description: Optional[str] = None
    monitor_summary: MonitorSummary
    last_check_at: Optional[str] = None
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class PaginatedObservabilityResponse(BaseModel):
    """Schema for paginated observability list response"""
    data: list[ObservabilityAssetItem]
    total: int
    page: int
    limit: int
    total_pages: int


class MonitorDetailItem(BaseModel):
    """Schema for monitor detail in expanded row"""
    id: str
    asset_id: str
    monitor_type: str
    target: str
    target_type: str
    port: Optional[int] = None
    protocol: Optional[str] = None
    circuit_type: Optional[str] = None
    check_interval: int
    is_active: bool
    current_status: str
    last_check_at: Optional[str] = None
    created_at: str
    updated_at: str

