"""
AssetWatch - Asset and Monitor Management Router

This module handles all API endpoints for the AssetWatch system (mini Wanaware.com).

=== OVERVIEW ===

Assets are network/compute/security infrastructure that you want to monitor.
Monitors are attached to assets to track either Performance or Availability.

=== ASSET TYPES (from Wanaware) ===

Circuit Types:
- Circuit-Internet-Cable Broadband, Fiber Broadband, Copper Broadband
- Circuit-Internet-Wireless Broadband (4G, 5G)
- Circuit-Internet-Satellite Broadband, Dedicated Internet Access
- Circuit-MPLS, Private Line, PRI, POTS, SIP

Network Assets:
- IP Block, Router, SD-WAN, Switch, WAP, Load Balancer

Security Assets:
- Firewall, IDS, IPS, NDR, WAF

Compute Assets:
- Server, Laptop, Desktop

Storage Assets:
- Storage Area Network (SAN)

=== MONITOR TYPES ===

1. Performance Monitor:
   - Tracks: CPU Usage, Memory Usage, Disk I/O, Latency
   - Protocol: ICMP | HTTP | HTTPS
   - Intervals: 1min | 5min | 15min
   - In production: Uses SNMP for metrics
   - Currently: Simulates realistic values

2. Availability Monitor:
   - Tracks: Status (UP/DOWN), Response Time, Uptime %, Packet Loss
   - Circuit Type: DIA | Broadband
   - Intervals: 30sec | 1min | 5min | 15min
   - Uses: ICMP ping for checks

=== ENDPOINTS ===

Assets:
- POST   /api/assets/              - Create new asset
- GET    /api/assets/              - List all assets
- GET    /api/assets/{id}          - Get asset with monitors
- PUT    /api/assets/{id}          - Update asset
- DELETE /api/assets/{id}          - Delete asset (cascades to monitors)

Monitors:
- POST   /api/assets/{id}/monitors/performance   - Add performance monitor
- POST   /api/assets/{id}/monitors/availability  - Add availability monitor
- GET    /api/assets/{id}/monitors               - List monitors for asset
- GET    /api/assets/{id}/monitors/{mid}         - Get monitor details
- PUT    /api/assets/{id}/monitors/{mid}         - Update monitor
- DELETE /api/assets/{id}/monitors/{mid}         - Delete monitor

Metrics:
- POST   /api/assets/{id}/monitors/{mid}/collect                - Trigger collection
- GET    /api/assets/{id}/monitors/{mid}/metrics/performance    - Get perf metrics
- GET    /api/assets/{id}/monitors/{mid}/metrics/availability   - Get avail metrics

Dashboard:
- GET    /api/assets/{id}/summary         - Get asset monitoring summary
- GET    /api/assets/dashboard/stats      - Get overall dashboard stats
- GET    /api/assets/types/list           - Get all asset types (for forms)
"""

import uuid
from uuid import UUID
from datetime import datetime, timedelta
import random
import asyncio
import platform

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import httpx

from app.core.db import (
    Asset, User, get_db, Monitor, 
    PerformanceMetric, AvailabilityMetric
)
from app.users import current_active_user
from app.api.dependencies import check_permission
from app.schemas import (
    AssetCreate, AssetResponse, AssetUpdate, AssetDetailResponse,
    PerformanceMonitorCreate, AvailabilityMonitorCreate,
    MonitorResponse, MonitorUpdate,
    PerformanceMetricResponse, AvailabilityMetricResponse,
)

# Create router with prefix and tags for API documentation
router = APIRouter(prefix="/assets", tags=["AssetWatch"])


# ==================== HELPER FUNCTIONS ====================
# These functions perform the actual monitoring checks

async def ping_host(host: str, timeout: int = 2) -> tuple[bool, float]:
    """
    Ping a host and return (is_up, response_time_ms).
    
    Uses the system's ping command for cross-platform compatibility.
    This is the core function for availability checks.
    
    Args:
        host: IP address or hostname to ping (e.g., "192.168.1.1" or "google.com")
        timeout: Maximum seconds to wait for response
        
    Returns:
        Tuple of (is_reachable: bool, response_time_in_ms: float)
        If unreachable, response_time will be 0.0
        
    Example:
        is_up, latency = await ping_host("8.8.8.8")
        if is_up:
            print(f"Host is up with {latency}ms latency")
    """
    try:
        # Determine ping command parameters based on OS
        # Windows uses -n for count and -w for timeout (in ms)
        # Linux/Mac use -c for count and -W for timeout (in seconds)
        param = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
        
        # Run ping command asynchronously (non-blocking)
        start_time = datetime.now()
        process = await asyncio.create_subprocess_exec(
            "ping", param, "1", timeout_param, str(timeout), host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for ping to complete with timeout protection
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), 
            timeout=timeout + 1
        )
        end_time = datetime.now()
        
        # Calculate actual response time
        response_time = (end_time - start_time).total_seconds() * 1000
        
        # Return code 0 means ping was successful
        is_up = process.returncode == 0
        return is_up, response_time if is_up else 0.0
        
    except asyncio.TimeoutError:
        # Ping took too long
        print(f"Ping timeout for {host}")
        return False, 0.0
    except Exception as e:
        # Any other error (e.g., ping command not found)
        print(f"Ping failed for {host}: {e}")
        return False, 0.0


async def http_check(url: str, timeout: int = 5) -> tuple[bool, float]:
    """
    Check if an HTTP(S) endpoint is reachable and responding.
    
    Makes a GET request to the URL and checks for successful response.
    Used for HTTP/HTTPS protocol performance monitoring.
    
    Args:
        url: Full URL to check (must include http:// or https://)
        timeout: Maximum seconds to wait for response
        
    Returns:
        Tuple of (is_reachable: bool, response_time_in_ms: float)
        
    Example:
        is_up, latency = await http_check("https://google.com")
    """
    try:
        start_time = datetime.now()
        
        # Use httpx for async HTTP requests
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            end_time = datetime.now()
            
            # Calculate response time
            response_time = (end_time - start_time).total_seconds() * 1000
            
            # Consider 2xx and 3xx status codes as "up"
            is_up = 200 <= response.status_code < 400
            
            return is_up, response_time
            
    except httpx.TimeoutException:
        print(f"HTTP timeout for {url}")
        return False, 0.0
    except Exception as e:
        print(f"HTTP check failed for {url}: {e}")
        return False, 0.0


def simulate_performance_metrics(base_latency: float = 100.0) -> dict:
    """
    Simulate realistic performance metrics.
    
    In production, these would be collected via SNMP polling from the device.
    SNMP (Simple Network Management Protocol) can query devices for:
    - CPU utilization via HOST-RESOURCES-MIB
    - Memory usage via HOST-RESOURCES-MIB
    - Disk I/O via various vendor MIBs
    
    For now, we generate realistic random values with some variance.
    
    Args:
        base_latency: Base latency value from ping (affects simulated values)
        
    Returns:
        Dict with keys: cpu_usage, memory_usage, disk_io, latency
        
    TODO: Implement actual SNMP polling with pysnmp library:
        from pysnmp.hlapi.asyncio import *
        # Poll OIDs for CPU, memory, disk from device
    """
    # Add realistic variation using gaussian distribution
    # Values cluster around a mean with standard deviation
    return {
        # CPU typically varies between 15-85% on active servers
        "cpu_usage": round(
            max(0, min(100, random.uniform(15, 85) + random.gauss(0, 5))), 
            2
        ),
        # Memory tends to be more stable, 30-80% range
        "memory_usage": round(
            max(0, min(100, random.uniform(30, 80) + random.gauss(0, 3))), 
            2
        ),
        # Disk I/O varies widely, 50-250 MB/s typical for SSDs
        "disk_io": round(
            max(0, random.uniform(50, 250) + random.gauss(0, 20)), 
            2
        ),
        # Latency based on actual ping + some variation
        "latency": round(
            max(0, base_latency + random.uniform(-20, 50) + random.gauss(0, 10)), 
            2
        )
    }


def calculate_uptime_percentage(
    up_count: int, 
    total_count: int, 
    current_status: bool
) -> float:
    """
    Calculate uptime percentage based on historical checks.
    
    Uptime is calculated as: (successful_checks / total_checks) * 100
    
    This is a rolling calculation that includes the current check.
    For example, if we had 99 UP and 1 DOWN out of 100 checks,
    and current check is UP, uptime would be ~99.01%
    
    Args:
        up_count: Number of successful (UP) checks in history
        total_count: Total number of historical checks
        current_status: Whether the current check was successful
        
    Returns:
        Uptime percentage as float (0-100)
    """
    if total_count == 0:
        # No history, use current status
        return 100.0 if current_status else 0.0
    
    # Include current check in calculation
    weighted_up = up_count + (1 if current_status else 0)
    weighted_total = total_count + 1
    
    return round((weighted_up / weighted_total) * 100, 2)


# ==================== ASSET CRUD ENDPOINTS ====================


@router.post(
    "/",
    response_model=AssetResponse,
    status_code=201,
    dependencies=[Depends(check_permission("create", "asset"))]
)
async def create_asset(
    asset: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Create a new asset.
    
    Assets represent network/compute/security infrastructure to monitor.
    After creating an asset, attach Performance or Availability monitors to it.
    
    Request Body (AssetCreate):
    - name (required): User-friendly name, e.g., "Main Office Router"
    - asset_type (required): One of the Wanaware asset types
    - description (optional): Additional details
    
    Returns:
        Created asset with ID and timestamps
        
    Example:
        POST /api/assets/
        {
            "name": "HQ Firewall",
            "asset_type": "Security Asset-Firewall",
            "description": "Main perimeter firewall at headquarters"
        }
    """
    # Create new asset instance
    db_asset = Asset(
        name=asset.name,
        asset_type=asset.asset_type,
        description=asset.description,
        user_id=user.id  # Associate with current user
    )
    
    # Save to database
    db.add(db_asset)
    await db.commit()
    await db.refresh(db_asset)  # Get generated ID and timestamps
    
    # Return formatted response
    return {
        "id": str(db_asset.id),
        "name": db_asset.name,
        "asset_type": db_asset.asset_type,
        "description": db_asset.description,
        "created_at": db_asset.created_at.isoformat(),
        "updated_at": db_asset.updated_at.isoformat(),
        "monitor_count": 0  # New asset has no monitors
    }


@router.get(
    "/",
    dependencies=[Depends(check_permission("read", "asset"))]
)
async def get_all_assets(
    page: int = Query(None, ge=1, description="Page number (1-indexed) - if not provided, returns all assets"),
    limit: int = Query(None, ge=1, le=100, description="Number of items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    search: str = Query(None, description="Search term for asset name"),
    asset_type: str = Query(None, description="Filter by asset type"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get all assets for the current user with optional pagination.
    
    If page and limit are provided, returns paginated results.
    Otherwise, returns all assets (backward compatible).
    
    Query Parameters:
    - page: Page number (1-indexed)
    - limit: Items per page (default 10, max 100)
    - sort_by: Field to sort by (name, asset_type, created_at, updated_at)
    - order: Sort order (asc, desc)
    - search: Search term for asset name
    - asset_type: Filter by asset type
    
    Returns:
        Paginated response or list of AssetResponse objects
    """
    from sqlalchemy import asc, desc as sql_desc
    
    # Map sortable fields
    sortable_fields = {
        "name": Asset.name,
        "asset_type": Asset.asset_type,
        "created_at": Asset.created_at,
        "updated_at": Asset.updated_at,
    }
    
    # Base query
    query = select(Asset).where(Asset.user_id == user.id)
    count_query = select(func.count(Asset.id)).where(Asset.user_id == user.id)
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.where(Asset.name.ilike(search_filter))
        count_query = count_query.where(Asset.name.ilike(search_filter))
    
    # Apply asset_type filter
    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
        count_query = count_query.where(Asset.asset_type == asset_type)
    
    # Get total count (for pagination)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_column = sortable_fields.get(sort_by, Asset.created_at)
    if order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(sql_desc(sort_column))
    
    # Apply pagination if page and limit are provided
    is_paginated = page is not None and limit is not None
    if is_paginated:
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    assets = result.scalars().all()
    
    # Build response with monitor counts
    response_items = []
    for asset in assets:
        # Count monitors attached to this asset
        monitor_count_result = await db.execute(
            select(func.count(Monitor.id)).where(Monitor.asset_id == asset.id)
        )
        monitor_count = monitor_count_result.scalar() or 0
        
        response_items.append({
            "id": str(asset.id),
            "name": asset.name,
            "asset_type": asset.asset_type,
            "description": asset.description,
            "created_at": asset.created_at.isoformat(),
            "updated_at": asset.updated_at.isoformat(),
            "monitor_count": monitor_count
        })
    
    # Return paginated response or list based on request
    if is_paginated:
        total_pages = (total + limit - 1) // limit if total > 0 else 1
        return {
            "data": response_items,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }
    
    # Backward compatible: return list if no pagination params
    return response_items


@router.get("/types/list")
async def get_asset_types():
    """
    Get list of all available asset types and configuration options.
    
    Use this endpoint to populate dropdown menus in the frontend.
    Returns all asset types organized by category, plus monitor options.
    
    Returns:
        - asset_types: List of categories with their types
        - monitor_types: ["performance", "availability"]
        - performance_protocols: ["icmp", "http", "https"]
        - circuit_types: ["dia", "broadband"]
        - check_intervals: Available intervals for each monitor type
    """
    return {
        "asset_types": [
            # Circuit - Internet connection types
            {
                "category": "Circuit-Internet", 
                "types": [
                    "Circuit-Internet-Cable Broadband",
                    "Circuit-Internet-Fiber Broadband",
                    "Circuit-Internet-Copper Broadband",
                    "Circuit-Internet-Wireless Broadband",
                    "Circuit-Internet-Wireless 4G Broadband",
                    "Circuit-Internet-Wireless 5G Broadband",
                    "Circuit-Internet-Satellite Broadband",
                    "Circuit-Internet-Dedicated Internet Access",
                ]
            },
            # Circuit - Enterprise connection types
            {
                "category": "Circuit-Enterprise", 
                "types": [
                    "Circuit-MPLS",
                    "Circuit-Private Line",
                    "Circuit-PRI",
                    "Circuit-POTS",
                    "Circuit-SIP",
                ]
            },
            # Network infrastructure assets
            {
                "category": "Network Asset", 
                "types": [
                    "Network Asset-IP Block",
                    "Network Asset-Router",
                    "Network Asset-SD-WAN",
                    "Network Asset-Switch",
                    "Network Asset-Wireless Access Point (WAP)",
                    "Network Asset-Load Balancer",
                ]
            },
            # Security infrastructure
            {
                "category": "Security Asset", 
                "types": [
                    "Security Asset-Firewall",
                    "Security Asset-Intrusion Detection System (IDS)",
                    "Security Asset-Intrusion Prevention System (IPS)",
                    "Security Asset-Network Detection & Response (NDR)",
                    "Security Asset-Web Application Firewall (WAF)",
                ]
            },
            # Compute endpoints and servers
            {
                "category": "Compute Asset", 
                "types": [
                    "Compute Asset-Server",
                    "Compute Asset-Laptop",
                    "Compute Asset-Desktop",
                ]
            },
            # Storage infrastructure
            {
                "category": "Storage Asset", 
                "types": [
                    "Storage Asset-Storage Area Network (SAN)",
                ]
            },
        ],
        # Monitor configuration options
        "monitor_types": ["performance", "availability"],
        "performance_protocols": ["icmp", "http", "https"],
        "circuit_types": ["dia", "broadband"],
        "target_types": ["ip", "hostname"],
        "check_intervals": {
            "performance": [
                {"value": 60, "label": "1 minute"},
                {"value": 300, "label": "5 minutes"},
                {"value": 900, "label": "15 minutes"},
            ],
            "availability": [
                {"value": 30, "label": "30 seconds"},
                {"value": 60, "label": "1 minute"},
                {"value": 300, "label": "5 minutes"},
                {"value": 900, "label": "15 minutes"},
            ]
        }
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get overall dashboard statistics for the current user.
    
    Provides a bird's-eye view of all assets and their monitoring status.
    
    Returns:
        - total_assets: Count of all assets
        - total_monitors: Count of all monitors
        - active_monitors: Count of monitors that are active
        - assets_up: Monitors with "up" status
        - assets_down: Monitors with "down" status  
        - assets_unknown: Monitors with "unknown" status
        - avg_uptime: Average uptime % across availability monitors (24h)
        - recent_alerts: Last 10 DOWN status events
    """
    # Get all assets for user
    assets_result = await db.execute(
        select(Asset).where(Asset.user_id == user.id)
    )
    assets = assets_result.scalars().all()
    total_assets = len(assets)
    
    # Get all monitors for user's assets
    asset_ids = [a.id for a in assets]
    if asset_ids:
        monitors_result = await db.execute(
            select(Monitor).where(Monitor.asset_id.in_(asset_ids))
        )
        monitors = monitors_result.scalars().all()
    else:
        monitors = []
    
    # Calculate statistics
    total_monitors = len(monitors)
    active_monitors = sum(1 for m in monitors if m.is_active)
    
    # Count by status
    assets_up = sum(1 for m in monitors if m.current_status == "up")
    assets_down = sum(1 for m in monitors if m.current_status == "down")
    assets_unknown = sum(1 for m in monitors if m.current_status == "unknown")
    
    # Calculate average uptime from availability monitors (last 24 hours)
    avail_monitors = [m for m in monitors if m.monitor_type == "availability"]
    avg_uptime = 0.0
    
    if avail_monitors:
        avail_ids = [m.id for m in avail_monitors]
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        metrics_result = await db.execute(
            select(AvailabilityMetric)
            .where(
                AvailabilityMetric.monitor_id.in_(avail_ids),
                AvailabilityMetric.timestamp >= yesterday
            )
        )
        metrics = metrics_result.scalars().all()
        
        if metrics:
            up_count = sum(1 for m in metrics if m.status == "UP")
            avg_uptime = round((up_count / len(metrics)) * 100, 2)
    
    # Get recent alerts (DOWN statuses in last 24 hours)
    recent_alerts = []
    if avail_monitors:
        avail_ids = [m.id for m in avail_monitors]
        yesterday = datetime.utcnow() - timedelta(hours=24)
        
        down_metrics_result = await db.execute(
            select(AvailabilityMetric)
            .where(
                AvailabilityMetric.monitor_id.in_(avail_ids),
                AvailabilityMetric.status == "DOWN",
                AvailabilityMetric.timestamp >= yesterday
            )
            .order_by(AvailabilityMetric.timestamp.desc())
            .limit(10)
        )
        down_metrics = down_metrics_result.scalars().all()
        
        # Build alerts with context
        for dm in down_metrics:
            monitor = next((m for m in monitors if m.id == dm.monitor_id), None)
            if monitor:
                asset = next((a for a in assets if a.id == monitor.asset_id), None)
                if asset:
                    recent_alerts.append({
                        "asset_name": asset.name,
                        "asset_type": asset.asset_type,
                        "monitor_target": monitor.target,
                        "timestamp": dm.timestamp.isoformat(),
                        "response_time": dm.response_time
                    })
    
    return {
        "total_assets": total_assets,
        "total_monitors": total_monitors,
        "active_monitors": active_monitors,
        "assets_up": assets_up,
        "assets_down": assets_down,
        "assets_unknown": assets_unknown,
        "avg_uptime": avg_uptime,
        "recent_alerts": recent_alerts
    }


@router.get(
    "/{asset_id}",
    response_model=AssetDetailResponse,
    dependencies=[Depends(check_permission("read", "asset"))]
)
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get detailed information about a single asset, including its monitors.
    
    Path Parameters:
        asset_id: UUID of the asset
        
    Returns:
        AssetDetailResponse with full asset info and list of monitors
        
    Raises:
        404: Asset not found or doesn't belong to user
    """
    # Find asset by ID and verify ownership
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = result.scalars().first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get all monitors for this asset
    monitors_result = await db.execute(
        select(Monitor).where(Monitor.asset_id == asset_id)
    )
    monitors = monitors_result.scalars().all()
    
    # Format monitor responses
    monitors_response = [
        {
            "id": str(m.id),
            "asset_id": str(m.asset_id),
            "monitor_type": m.monitor_type,
            "target": m.target,
            "target_type": m.target_type,
            "port": m.port,
            "protocol": m.protocol,
            "circuit_type": m.circuit_type,
            "check_interval": m.check_interval,
            "is_active": bool(m.is_active),
            "current_status": m.current_status,
            "last_check_at": m.last_check_at.isoformat() if m.last_check_at else None,
            "created_at": m.created_at.isoformat(),
            "updated_at": m.updated_at.isoformat()
        }
        for m in monitors
    ]
    
    return {
        "id": str(asset.id),
        "name": asset.name,
        "asset_type": asset.asset_type,
        "description": asset.description,
        "created_at": asset.created_at.isoformat(),
        "updated_at": asset.updated_at.isoformat(),
        "monitor_count": len(monitors),
        "monitors": monitors_response
    }


@router.put(
    "/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(check_permission("update", "asset"))]
)
async def update_asset(
    asset_id: UUID,
    asset_update: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Update an existing asset.
    
    Only updates fields that are provided (partial update).
    
    Path Parameters:
        asset_id: UUID of the asset to update
        
    Request Body (AssetUpdate):
        All fields optional - only provided fields are updated
        - name: New name for the asset
        - asset_type: New asset type
        - description: New description
        
    Returns:
        Updated asset
        
    Raises:
        404: Asset not found
    """
    # Find asset
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = result.scalars().first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Update only provided fields (exclude_unset=True ignores None values)
    update_data = asset_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(asset, key, value)
    
    # Save changes
    await db.commit()
    await db.refresh(asset)
    
    # Get updated monitor count
    monitor_count_result = await db.execute(
        select(func.count(Monitor.id)).where(Monitor.asset_id == asset.id)
    )
    monitor_count = monitor_count_result.scalar() or 0
    
    return {
        "id": str(asset.id),
        "name": asset.name,
        "asset_type": asset.asset_type,
        "description": asset.description,
        "created_at": asset.created_at.isoformat(),
        "updated_at": asset.updated_at.isoformat(),
        "monitor_count": monitor_count
    }


@router.delete(
    "/{asset_id}",
    status_code=204,
    dependencies=[Depends(check_permission("delete", "asset"))]
)
async def delete_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Delete an asset and all its associated monitors and metrics.
    
    This is a CASCADING DELETE - all related data will be permanently removed:
    - The asset itself
    - All monitors attached to the asset
    - All performance metrics from those monitors
    - All availability metrics from those monitors
    
    Path Parameters:
        asset_id: UUID of the asset to delete
        
    Returns:
        204 No Content on success
        
    Raises:
        404: Asset not found
    """
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = result.scalars().first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Delete asset (cascades to monitors and metrics via relationship config)
    await db.delete(asset)
    await db.commit()


# ==================== MONITOR CRUD ENDPOINTS ====================


@router.post("/{asset_id}/monitors/performance", response_model=MonitorResponse, status_code=201)
async def create_performance_monitor(
    asset_id: UUID,
    monitor: PerformanceMonitorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Create a Performance Monitor for an asset.
    
    Performance monitors track system metrics:
    - CPU Usage (%) - Processor utilization
    - Memory Usage (%) - RAM utilization  
    - Disk I/O (MB/s) - Storage throughput
    - Latency (ms) - Network response time
    
    Form Fields (from Wanaware):
    1. Select Asset - From URL path parameter
    2. Monitor Type - Set to "performance"
    3. Enter Target - IP address or hostname to monitor
    4. Target Type - "ip" or "hostname"
    5. Port - Optional port number
    6. Protocol - ICMP (ping), HTTP, or HTTPS
    7. Check Interval - 1min (60), 5min (300), or 15min (900)
    
    Path Parameters:
        asset_id: UUID of the asset to attach monitor to
        
    Request Body (PerformanceMonitorCreate):
        - target: IP or hostname (e.g., "192.168.1.1" or "server.local")
        - target_type: "ip" or "hostname"
        - port: Optional port number (1-65535)
        - protocol: "icmp", "http", or "https"
        - check_interval: 60, 300, or 900 (seconds)
        
    Returns:
        Created monitor with ID
        
    Raises:
        404: Asset not found
        400: Duplicate monitor for same target
    """
    # Verify asset exists and belongs to user
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = asset_result.scalars().first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Check for duplicate (same asset + target + monitor_type)
    existing = await db.execute(
        select(Monitor).where(
            Monitor.asset_id == asset_id,
            Monitor.monitor_type == "performance",
            Monitor.target == monitor.target
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400, 
            detail="A performance monitor for this target already exists on this asset"
        )
    
    # Create the monitor
    db_monitor = Monitor(
        asset_id=asset_id,
        monitor_type="performance",
        target=monitor.target,
        target_type=monitor.target_type,
        port=monitor.port,
        protocol=monitor.protocol,
        check_interval=monitor.check_interval
    )
    db.add(db_monitor)
    await db.commit()
    await db.refresh(db_monitor)
    
    return {
        "id": str(db_monitor.id),
        "asset_id": str(db_monitor.asset_id),
        "monitor_type": db_monitor.monitor_type,
        "target": db_monitor.target,
        "target_type": db_monitor.target_type,
        "port": db_monitor.port,
        "protocol": db_monitor.protocol,
        "circuit_type": db_monitor.circuit_type,
        "check_interval": db_monitor.check_interval,
        "is_active": bool(db_monitor.is_active),
        "current_status": db_monitor.current_status,
        "last_check_at": None,
        "created_at": db_monitor.created_at.isoformat(),
        "updated_at": db_monitor.updated_at.isoformat()
    }


@router.post("/{asset_id}/monitors/availability", response_model=MonitorResponse, status_code=201)
async def create_availability_monitor(
    asset_id: UUID,
    monitor: AvailabilityMonitorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Create an Availability Monitor for an asset.
    
    Availability monitors track uptime and connectivity:
    - Status - UP or DOWN
    - Response Time (ms) - How long to get response
    - Uptime (%) - Calculated over check period
    - Packet Loss (%) - For ICMP checks
    
    Form Fields (from Wanaware):
    1. Select Asset - From URL path parameter
    2. Monitor Type - Set to "availability"
    3. Enter Target - IP address or hostname
    4. Target Type - "ip" or "hostname"
    5. Port - Optional port number
    6. Circuit Type - "dia" (Dedicated Internet Access) or "broadband"
    7. Check Interval - 30sec, 1min, 5min, or 15min
    
    Circuit Types explained:
    - DIA: Dedicated Internet Access - enterprise-grade, higher SLA expectations
    - Broadband: Consumer-grade connectivity - lower SLA expectations
    
    Path Parameters:
        asset_id: UUID of the asset to attach monitor to
        
    Request Body (AvailabilityMonitorCreate):
        - target: IP or hostname
        - target_type: "ip" or "hostname"
        - port: Optional port number
        - circuit_type: "dia" or "broadband"
        - check_interval: 30, 60, 300, or 900 (seconds)
        
    Returns:
        Created monitor with ID
        
    Raises:
        404: Asset not found
        400: Duplicate monitor
    """
    # Verify asset exists and belongs to user
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = asset_result.scalars().first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Check for duplicate
    existing = await db.execute(
        select(Monitor).where(
            Monitor.asset_id == asset_id,
            Monitor.monitor_type == "availability",
            Monitor.target == monitor.target
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400, 
            detail="An availability monitor for this target already exists on this asset"
        )
    
    # Create the monitor
    db_monitor = Monitor(
        asset_id=asset_id,
        monitor_type="availability",
        target=monitor.target,
        target_type=monitor.target_type,
        port=monitor.port,
        circuit_type=monitor.circuit_type,
        check_interval=monitor.check_interval
    )
    db.add(db_monitor)
    await db.commit()
    await db.refresh(db_monitor)
    
    return {
        "id": str(db_monitor.id),
        "asset_id": str(db_monitor.asset_id),
        "monitor_type": db_monitor.monitor_type,
        "target": db_monitor.target,
        "target_type": db_monitor.target_type,
        "port": db_monitor.port,
        "protocol": db_monitor.protocol,
        "circuit_type": db_monitor.circuit_type,
        "check_interval": db_monitor.check_interval,
        "is_active": bool(db_monitor.is_active),
        "current_status": db_monitor.current_status,
        "last_check_at": None,
        "created_at": db_monitor.created_at.isoformat(),
        "updated_at": db_monitor.updated_at.isoformat()
    }


@router.get("/{asset_id}/monitors", response_model=list[MonitorResponse])
async def get_asset_monitors(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get all monitors attached to an asset.
    
    Path Parameters:
        asset_id: UUID of the asset
        
    Returns:
        List of MonitorResponse objects
        
    Raises:
        404: Asset not found
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    if not asset_result.scalars().first():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get monitors
    monitors_result = await db.execute(
        select(Monitor)
        .where(Monitor.asset_id == asset_id)
        .order_by(Monitor.created_at.desc())
    )
    monitors = monitors_result.scalars().all()
    
    return [
        {
            "id": str(m.id),
            "asset_id": str(m.asset_id),
            "monitor_type": m.monitor_type,
            "target": m.target,
            "target_type": m.target_type,
            "port": m.port,
            "protocol": m.protocol,
            "circuit_type": m.circuit_type,
            "check_interval": m.check_interval,
            "is_active": bool(m.is_active),
            "current_status": m.current_status,
            "last_check_at": m.last_check_at.isoformat() if m.last_check_at else None,
            "created_at": m.created_at.isoformat(),
            "updated_at": m.updated_at.isoformat()
        }
        for m in monitors
    ]


@router.get("/{asset_id}/monitors/{monitor_id}", response_model=MonitorResponse)
async def get_monitor(
    asset_id: UUID,
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get details of a specific monitor.
    
    Path Parameters:
        asset_id: UUID of the asset
        monitor_id: UUID of the monitor
        
    Returns:
        MonitorResponse with full monitor details
        
    Raises:
        404: Asset or monitor not found
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    if not asset_result.scalars().first():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get monitor
    monitor_result = await db.execute(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.asset_id == asset_id)
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    return {
        "id": str(monitor.id),
        "asset_id": str(monitor.asset_id),
        "monitor_type": monitor.monitor_type,
        "target": monitor.target,
        "target_type": monitor.target_type,
        "port": monitor.port,
        "protocol": monitor.protocol,
        "circuit_type": monitor.circuit_type,
        "check_interval": monitor.check_interval,
        "is_active": bool(monitor.is_active),
        "current_status": monitor.current_status,
        "last_check_at": monitor.last_check_at.isoformat() if monitor.last_check_at else None,
        "created_at": monitor.created_at.isoformat(),
        "updated_at": monitor.updated_at.isoformat()
    }


@router.put("/{asset_id}/monitors/{monitor_id}", response_model=MonitorResponse)
async def update_monitor(
    asset_id: UUID,
    monitor_id: UUID,
    monitor_update: MonitorUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Update a monitor's configuration.
    
    Only updates fields that are provided (partial update).
    
    Path Parameters:
        asset_id: UUID of the asset
        monitor_id: UUID of the monitor to update
        
    Request Body (MonitorUpdate):
        All fields optional:
        - target: New target IP/hostname
        - target_type: "ip" or "hostname"
        - port: New port number
        - protocol: New protocol (performance only)
        - circuit_type: New circuit type (availability only)
        - check_interval: New interval in seconds
        - is_active: Enable/disable the monitor
        
    Returns:
        Updated monitor
        
    Raises:
        404: Asset or monitor not found
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    if not asset_result.scalars().first():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get monitor
    monitor_result = await db.execute(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.asset_id == asset_id)
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Update only provided fields
    update_data = monitor_update.model_dump(exclude_unset=True)
    
    # Convert is_active bool to int for SQLite storage
    if "is_active" in update_data:
        update_data["is_active"] = 1 if update_data["is_active"] else 0
    
    for key, value in update_data.items():
        setattr(monitor, key, value)
    
    await db.commit()
    await db.refresh(monitor)
    
    return {
        "id": str(monitor.id),
        "asset_id": str(monitor.asset_id),
        "monitor_type": monitor.monitor_type,
        "target": monitor.target,
        "target_type": monitor.target_type,
        "port": monitor.port,
        "protocol": monitor.protocol,
        "circuit_type": monitor.circuit_type,
        "check_interval": monitor.check_interval,
        "is_active": bool(monitor.is_active),
        "current_status": monitor.current_status,
        "last_check_at": monitor.last_check_at.isoformat() if monitor.last_check_at else None,
        "created_at": monitor.created_at.isoformat(),
        "updated_at": monitor.updated_at.isoformat()
    }


@router.delete("/{asset_id}/monitors/{monitor_id}", status_code=204)
async def delete_monitor(
    asset_id: UUID,
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Delete a monitor and all its associated metrics.
    
    This permanently removes:
    - The monitor itself
    - All performance metrics (if performance monitor)
    - All availability metrics (if availability monitor)
    
    Path Parameters:
        asset_id: UUID of the asset
        monitor_id: UUID of the monitor to delete
        
    Returns:
        204 No Content on success
        
    Raises:
        404: Asset or monitor not found
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    if not asset_result.scalars().first():
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get monitor
    monitor_result = await db.execute(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.asset_id == asset_id)
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Delete (cascades to metrics via relationship config)
    await db.delete(monitor)
    await db.commit()


# ==================== METRIC COLLECTION ENDPOINTS ====================


@router.post("/{asset_id}/monitors/{monitor_id}/collect")
async def collect_metrics(
    asset_id: UUID,
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Trigger metric collection for a monitor.
    
    This is the core monitoring function that:
    1. Performs the actual check (ping/HTTP) against the target
    2. Collects or simulates metrics based on monitor type
    3. Stores the metrics in the database
    4. Updates the monitor's current status
    
    For PERFORMANCE monitors:
    - Performs ping/HTTP check to measure latency
    - Simulates CPU, Memory, Disk I/O (would use SNMP in production)
    - Returns: cpu_usage, memory_usage, disk_io, latency
    
    For AVAILABILITY monitors:
    - Performs ICMP ping to determine UP/DOWN status
    - Measures actual response time
    - Calculates uptime % from historical data
    - Returns: status, response_time, uptime_percentage, packet_loss
    
    Path Parameters:
        asset_id: UUID of the asset
        monitor_id: UUID of the monitor to collect from
        
    Returns:
        Collected metric data with monitor status
        
    Raises:
        404: Asset or monitor not found
        400: Monitor is not active
        
    Example Response (Performance):
        {
            "monitor_id": "...",
            "monitor_type": "performance",
            "status": "up",
            "metric": {
                "cpu_usage": 73.2,
                "memory_usage": 62.5,
                "disk_io": 120.3,
                "latency": 132.1,
                "timestamp": "2024-01-15T10:30:00"
            }
        }
        
    Example Response (Availability):
        {
            "monitor_id": "...",
            "monitor_type": "availability", 
            "status": "up",
            "metric": {
                "status": "UP",
                "response_time": 245.3,
                "uptime_percentage": 99.98,
                "packet_loss": 0.0,
                "timestamp": "2024-01-15T10:30:00"
            }
        }
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = asset_result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get monitor
    monitor_result = await db.execute(
        select(Monitor).where(Monitor.id == monitor_id, Monitor.asset_id == asset_id)
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Check if monitor is active
    if not monitor.is_active:
        raise HTTPException(status_code=400, detail="Monitor is not active")
    
    # === PERFORMANCE MONITOR COLLECTION ===
    if monitor.monitor_type == "performance":
        # Step 1: Perform connectivity check based on protocol
        if monitor.protocol == "icmp":
            # Use ping for ICMP protocol
            is_up, response_time = await ping_host(monitor.target)
        elif monitor.protocol in ["http", "https"]:
            # Build URL for HTTP/HTTPS protocol
            url = f"{monitor.protocol}://{monitor.target}"
            if monitor.port:
                url += f":{monitor.port}"
            is_up, response_time = await http_check(url)
        else:
            # Fallback - shouldn't happen with validated input
            is_up, response_time = True, random.uniform(50, 200)
        
        # Step 2: Generate performance metrics
        # In production, this would be SNMP polling to the device
        # For now, we simulate realistic values based on response time
        perf_data = simulate_performance_metrics(
            response_time if is_up else 500  # Higher latency if down
        )
        
        # Step 3: Store metric in database
        metric = PerformanceMetric(
            monitor_id=monitor_id,
            cpu_usage=max(0, min(100, perf_data["cpu_usage"])),  # Clamp 0-100
            memory_usage=max(0, min(100, perf_data["memory_usage"])),
            disk_io=max(0, perf_data["disk_io"]),
            latency=max(0, perf_data["latency"])
        )
        db.add(metric)
        
        # Step 4: Update monitor status
        monitor.current_status = "up" if is_up else "down"
        monitor.last_check_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(metric)
        
        return {
            "monitor_id": str(monitor_id),
            "monitor_type": "performance",
            "status": monitor.current_status,
            "metric": {
                "id": str(metric.id),
                "cpu_usage": metric.cpu_usage,
                "memory_usage": metric.memory_usage,
                "disk_io": metric.disk_io,
                "latency": metric.latency,
                "timestamp": metric.timestamp.isoformat()
            }
        }
    
    # === AVAILABILITY MONITOR COLLECTION ===
    elif monitor.monitor_type == "availability":
        # Step 1: Perform ICMP ping check
        is_up, response_time = await ping_host(monitor.target)
        
        # Step 2: Get historical data for uptime calculation (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        history_result = await db.execute(
            select(AvailabilityMetric)
            .where(
                AvailabilityMetric.monitor_id == monitor_id,
                AvailabilityMetric.timestamp >= yesterday
            )
        )
        history = history_result.scalars().all()
        
        # Count UP statuses in history
        up_count = sum(1 for m in history if m.status == "UP")
        total_count = len(history)
        
        # Step 3: Calculate uptime percentage
        uptime = calculate_uptime_percentage(up_count, total_count, is_up)
        
        # Step 4: Calculate packet loss
        # If up, 0% loss. If down, simulate some packet loss
        packet_loss = 0.0 if is_up else random.uniform(10, 100)
        
        # Step 5: Store metric in database
        metric = AvailabilityMetric(
            monitor_id=monitor_id,
            status="UP" if is_up else "DOWN",
            response_time=response_time if is_up else 0.0,
            uptime_percentage=uptime,
            packet_loss=packet_loss
        )
        db.add(metric)
        
        # Step 6: Update monitor status
        monitor.current_status = "up" if is_up else "down"
        monitor.last_check_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(metric)
        
        return {
            "monitor_id": str(monitor_id),
            "monitor_type": "availability",
            "status": monitor.current_status,
            "metric": {
                "id": str(metric.id),
                "status": metric.status,
                "response_time": metric.response_time,
                "uptime_percentage": metric.uptime_percentage,
                "packet_loss": metric.packet_loss,
                "timestamp": metric.timestamp.isoformat()
            }
        }


# ==================== METRIC RETRIEVAL ENDPOINTS ====================

@router.get("/{asset_id}/monitors/{monitor_id}/metrics/performance")
async def get_performance_metrics(
    asset_id: UUID,
    monitor_id: UUID,
    days: int = Query(default=7, ge=1, le=365, description="Number of days of data to retrieve"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get performance metrics for a monitor within the specified time range.
    
    Returns historical data for graphing and analysis:
    - CPU usage over time
    - Memory usage over time
    - Disk I/O over time
    - Latency over time
    
    Path Parameters:
        asset_id: UUID of the asset
        monitor_id: UUID of the performance monitor
        
    Query Parameters:
        days: Number of days of historical data (1-365, default 7)
              - days=1: Last 24 hours
              - days=7: Last week
              - days=30: Last month
              - days=365: Last year
              
    Returns:
        - monitor_id, asset_id, asset_name: Context
        - days: Number of days requested
        - total_records: Count of data points
        - data: Array of PerformanceMetricResponse
        
    Raises:
        404: Asset or monitor not found
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = asset_result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Verify it's a performance monitor
    monitor_result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id, 
            Monitor.asset_id == asset_id,
            Monitor.monitor_type == "performance"
        )
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Performance monitor not found")
    
    # Calculate date filter
    date_filter = datetime.utcnow() - timedelta(days=days)
    
    # Query metrics within date range, ordered by time
    metrics_result = await db.execute(
        select(PerformanceMetric)
        .where(
            PerformanceMetric.monitor_id == monitor_id,
            PerformanceMetric.timestamp >= date_filter
        )
        .order_by(PerformanceMetric.timestamp)
    )
    metrics = metrics_result.scalars().all()
    
    return {
        "monitor_id": str(monitor_id),
        "asset_id": str(asset_id),
        "asset_name": asset.name,
        "monitor_type": "performance",
        "days": days,
        "total_records": len(metrics),
        "data": [
            {
                "id": str(m.id),
                "cpu_usage": m.cpu_usage,
                "memory_usage": m.memory_usage,
                "disk_io": m.disk_io,
                "latency": m.latency,
                "timestamp": m.timestamp.isoformat()
            }
            for m in metrics
        ]
    }


@router.get("/{asset_id}/monitors/{monitor_id}/metrics/availability")
async def get_availability_metrics(
    asset_id: UUID,
    monitor_id: UUID,
    days: int = Query(default=7, ge=1, le=365, description="Number of days of data to retrieve"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get availability metrics for a monitor within the specified time range.
    
    Returns historical data for uptime tracking:
    - Status history (UP/DOWN)
    - Response time over time
    - Uptime percentage trend
    - Packet loss data
    
    Path Parameters:
        asset_id: UUID of the asset
        monitor_id: UUID of the availability monitor
        
    Query Parameters:
        days: Number of days of historical data (1-365, default 7)
        
    Returns:
        - monitor_id, asset_id, asset_name: Context
        - days: Number of days requested
        - total_records: Count of data points
        - data: Array of AvailabilityMetricResponse
        
    Raises:
        404: Asset or monitor not found
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = asset_result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Verify it's an availability monitor
    monitor_result = await db.execute(
        select(Monitor).where(
            Monitor.id == monitor_id, 
            Monitor.asset_id == asset_id,
            Monitor.monitor_type == "availability"
        )
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Availability monitor not found")
    
    # Calculate date filter
    date_filter = datetime.utcnow() - timedelta(days=days)
    
    # Query metrics within date range
    metrics_result = await db.execute(
        select(AvailabilityMetric)
        .where(
            AvailabilityMetric.monitor_id == monitor_id,
            AvailabilityMetric.timestamp >= date_filter
        )
        .order_by(AvailabilityMetric.timestamp)
    )
    metrics = metrics_result.scalars().all()
    
    return {
        "monitor_id": str(monitor_id),
        "asset_id": str(asset_id),
        "asset_name": asset.name,
        "monitor_type": "availability",
        "days": days,
        "total_records": len(metrics),
        "data": [
            {
                "id": str(m.id),
                "status": m.status,
                "response_time": m.response_time,
                "uptime_percentage": m.uptime_percentage,
                "packet_loss": m.packet_loss,
                "timestamp": m.timestamp.isoformat()
            }
            for m in metrics
        ]
    }


# ==================== SUMMARY ENDPOINTS ====================


@router.get("/{asset_id}/summary")
async def get_asset_monitoring_summary(
    asset_id: UUID,
    days: int = Query(default=7, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user)
):
    """
    Get a complete monitoring summary for an asset.
    
    Aggregates data from ALL monitors attached to the asset and provides
    summary statistics for dashboards and reports.
    
    Performance Summary (if performance monitors exist):
    - CPU: {avg, min, max, current}
    - Memory: {avg, min, max, current}
    - Disk I/O: {avg, min, max, current}
    - Latency: {avg, min, max, current}
    
    Availability Summary (if availability monitors exist):
    - current_status: Latest status
    - uptime_percentage: Overall uptime
    - avg_response_time: Average response time
    - total_checks: Total number of checks
    - up_count: Successful checks
    - down_count: Failed checks
    - last_downtime: When was the last outage
    
    Path Parameters:
        asset_id: UUID of the asset
        
    Query Parameters:
        days: Number of days to include (default 7)
        
    Returns:
        MonitoringSummaryResponse with performance and availability summaries
    """
    # Verify asset
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user.id)
    )
    asset = asset_result.scalars().first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    date_filter = datetime.utcnow() - timedelta(days=days)
    
    # Get all monitors for this asset
    monitors_result = await db.execute(
        select(Monitor).where(Monitor.asset_id == asset_id)
    )
    monitors = monitors_result.scalars().all()
    
    # === PERFORMANCE SUMMARY ===
    perf_monitor_ids = [m.id for m in monitors if m.monitor_type == "performance"]
    perf_summary = None
    
    if perf_monitor_ids:
        # Get all performance metrics from all performance monitors
        perf_result = await db.execute(
            select(PerformanceMetric)
            .where(
                PerformanceMetric.monitor_id.in_(perf_monitor_ids),
                PerformanceMetric.timestamp >= date_filter
            )
            .order_by(PerformanceMetric.timestamp.desc())
        )
        perf_metrics = perf_result.scalars().all()
        
        if perf_metrics:
            # Extract values for aggregation
            cpu_values = [m.cpu_usage for m in perf_metrics]
            memory_values = [m.memory_usage for m in perf_metrics]
            disk_values = [m.disk_io for m in perf_metrics]
            latency_values = [m.latency for m in perf_metrics]
            
            # Calculate statistics for each metric
            perf_summary = {
                "cpu": {
                    "avg": round(sum(cpu_values) / len(cpu_values), 2),
                    "min": round(min(cpu_values), 2),
                    "max": round(max(cpu_values), 2),
                    "current": round(cpu_values[0], 2)  # Most recent (desc order)
                },
                "memory": {
                    "avg": round(sum(memory_values) / len(memory_values), 2),
                    "min": round(min(memory_values), 2),
                    "max": round(max(memory_values), 2),
                    "current": round(memory_values[0], 2)
                },
                "disk_io": {
                    "avg": round(sum(disk_values) / len(disk_values), 2),
                    "min": round(min(disk_values), 2),
                    "max": round(max(disk_values), 2),
                    "current": round(disk_values[0], 2)
                },
                "latency": {
                    "avg": round(sum(latency_values) / len(latency_values), 2),
                    "min": round(min(latency_values), 2),
                    "max": round(max(latency_values), 2),
                    "current": round(latency_values[0], 2)
                }
            }
    
    # === AVAILABILITY SUMMARY ===
    avail_monitor_ids = [m.id for m in monitors if m.monitor_type == "availability"]
    avail_summary = None
    
    if avail_monitor_ids:
        # Get all availability metrics from all availability monitors
        avail_result = await db.execute(
            select(AvailabilityMetric)
            .where(
                AvailabilityMetric.monitor_id.in_(avail_monitor_ids),
                AvailabilityMetric.timestamp >= date_filter
            )
            .order_by(AvailabilityMetric.timestamp.desc())
        )
        avail_metrics = avail_result.scalars().all()
        
        if avail_metrics:
            # Count statuses
            up_count = sum(1 for m in avail_metrics if m.status == "UP")
            down_count = sum(1 for m in avail_metrics if m.status == "DOWN")
            total_count = len(avail_metrics)
            
            # Get response times (only from UP checks)
            response_times = [m.response_time for m in avail_metrics if m.response_time > 0]
            
            # Find last downtime
            last_downtime = None
            for m in avail_metrics:
                if m.status == "DOWN":
                    last_downtime = m.timestamp.isoformat()
                    break  # First one is most recent (desc order)
            
            avail_summary = {
                "current_status": avail_metrics[0].status,  # Most recent
                "uptime_percentage": round((up_count / total_count) * 100, 2) if total_count > 0 else 0,
                "avg_response_time": round(sum(response_times) / len(response_times), 2) if response_times else 0,
                "total_checks": total_count,
                "up_count": up_count,
                "down_count": down_count,
                "last_downtime": last_downtime
            }
    
    return {
        "asset_id": str(asset_id),
        "asset_name": asset.name,
        "asset_type": asset.asset_type,
        "days": days,
        "performance": perf_summary,
        "availability": avail_summary
    }
