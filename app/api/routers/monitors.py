"""
Standalone Monitors API Router

Provides endpoints for the Monitoring tab (UptimeRobot-style monitoring).
Supports HTTP(S), Ping, Port, and DNS monitor types.

Unlike asset-attached monitors, these are independent and user-owned directly.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Literal
from datetime import datetime, timedelta
from uuid import UUID
import re

from app.core.db import User, StandaloneMonitor, MonitorTag, StandaloneMonitorMetric, get_db
from app.users import current_active_user
from app.api.routers.models.monitors_models import (
    HTTPMonitorCreate,
    PingMonitorCreate,
    PortMonitorCreate,
    DNSMonitorCreate,
    StandaloneMonitorUpdate,
    StandaloneMonitorResponse,
    PaginatedStandaloneMonitorsResponse,
    StandaloneMonitorStats,
    StandaloneMonitorMetricResponse,
)
from app.api.routers.services.monitor_services import (
    # Constants
    INTERVAL_OPTIONS,
    TCP_PORTS,
    DNS_RECORD_TYPES,
    # Validators
    validate_url,
    validate_host,
    validate_interval,
    validate_record_type,
    clean_host,
    # Service functions
    build_monitor_response,
    create_tags,
    update_tags,
)

router = APIRouter(prefix="/monitors", tags=["Standalone Monitors"])


# ==================== ENDPOINTS ====================

@router.get("/stats", response_model=StandaloneMonitorStats)
async def get_monitor_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Get overview statistics for all standalone monitors"""
    result = await db.execute(
        select(StandaloneMonitor).where(StandaloneMonitor.user_id == current_user.id)
    )
    monitors = result.scalars().all()
    
    return StandaloneMonitorStats(
        total=len(monitors),
        up=sum(1 for m in monitors if m.current_status == "up" and m.is_active),
        down=sum(1 for m in monitors if m.current_status == "down" and m.is_active),
        paused=sum(1 for m in monitors if not m.is_active),
        unknown=sum(1 for m in monitors if m.current_status == "unknown" and m.is_active),
    )


@router.get("/tags", response_model=list[str])
async def get_all_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Get all unique tags used by the current user's monitors"""
    tags_result = await db.execute(
        select(MonitorTag.tag)
        .join(StandaloneMonitor, MonitorTag.monitor_id == StandaloneMonitor.id)
        .where(StandaloneMonitor.user_id == current_user.id)
        .distinct()
        .order_by(MonitorTag.tag)
    )
    return [row[0] for row in tags_result.fetchall()]


@router.get("", response_model=PaginatedStandaloneMonitorsResponse)
async def get_monitors(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    search: Optional[str] = Query(None, description="Search term for friendly name"),
    monitor_type: Optional[str] = Query(None, description="Filter by monitor type"),
    status: Optional[str] = Query(None, description="Filter by status (up, down, unknown, paused)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get all standalone monitors for the current user with pagination, filtering, and sorting.
    """
    # Map sortable fields
    sortable_fields = {
        "friendly_name": StandaloneMonitor.friendly_name,
        "monitor_type": StandaloneMonitor.monitor_type,
        "target": StandaloneMonitor.target,
        "current_status": StandaloneMonitor.current_status,
        "created_at": StandaloneMonitor.created_at,
        "updated_at": StandaloneMonitor.updated_at,
    }
    
    # Base query
    query = select(StandaloneMonitor).where(StandaloneMonitor.user_id == current_user.id)
    count_query = select(func.count(StandaloneMonitor.id)).where(
        StandaloneMonitor.user_id == current_user.id
    )
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.where(StandaloneMonitor.friendly_name.ilike(search_filter))
        count_query = count_query.where(StandaloneMonitor.friendly_name.ilike(search_filter))
    
    # Apply monitor_type filter
    if monitor_type:
        query = query.where(StandaloneMonitor.monitor_type == monitor_type)
        count_query = count_query.where(StandaloneMonitor.monitor_type == monitor_type)
    
    # Apply status filter
    if status:
        if status == "paused":
            query = query.where(StandaloneMonitor.is_active == 0)
            count_query = count_query.where(StandaloneMonitor.is_active == 0)
        else:
            query = query.where(
                StandaloneMonitor.current_status == status,
                StandaloneMonitor.is_active == 1
            )
            count_query = count_query.where(
                StandaloneMonitor.current_status == status,
                StandaloneMonitor.is_active == 1
            )
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_column = sortable_fields.get(sort_by, StandaloneMonitor.created_at)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    monitors = result.scalars().all()
    
    # Build response
    response_items = []
    for monitor in monitors:
        response_items.append(await build_monitor_response(monitor, db))
    
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return PaginatedStandaloneMonitorsResponse(
        data=response_items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.post("/http", response_model=StandaloneMonitorResponse, status_code=201)
async def create_http_monitor(
    monitor: HTTPMonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Create a new HTTP(S) monitor"""
    # Validate URL
    try:
        validate_url(monitor.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate interval
    try:
        validate_interval(monitor.check_interval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create monitor
    db_monitor = StandaloneMonitor(
        user_id=current_user.id,
        monitor_type="http",
        friendly_name=monitor.friendly_name,
        target=monitor.url,
        notify_email=1 if monitor.notify_email else 0,
        check_interval=monitor.check_interval,
        is_active=1,
        current_status="unknown",
    )
    
    db.add(db_monitor)
    await db.commit()
    await db.refresh(db_monitor)
    
    # Create tags
    if monitor.tags:
        await create_tags(db_monitor.id, monitor.tags, db)
        await db.commit()
        await db.refresh(db_monitor)
    
    return await build_monitor_response(db_monitor, db)


@router.post("/ping", response_model=StandaloneMonitorResponse, status_code=201)
async def create_ping_monitor(
    monitor: PingMonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Create a new Ping monitor"""
    # Validate host
    try:
        validate_host(monitor.host)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate interval
    try:
        validate_interval(monitor.check_interval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create monitor
    db_monitor = StandaloneMonitor(
        user_id=current_user.id,
        monitor_type="ping",
        friendly_name=monitor.friendly_name,
        target=monitor.host,
        notify_email=1 if monitor.notify_email else 0,
        check_interval=monitor.check_interval,
        is_active=1,
        current_status="unknown",
    )
    
    db.add(db_monitor)
    await db.commit()
    await db.refresh(db_monitor)
    
    # Create tags
    if monitor.tags:
        await create_tags(db_monitor.id, monitor.tags, db)
        await db.commit()
        await db.refresh(db_monitor)
    
    return await build_monitor_response(db_monitor, db)


@router.post("/port", response_model=StandaloneMonitorResponse, status_code=201)
async def create_port_monitor(
    monitor: PortMonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Create a new Port monitor"""
    # Clean host (remove protocol if present)
    host = clean_host(monitor.host)
    
    # Validate interval
    try:
        validate_interval(monitor.check_interval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create monitor
    db_monitor = StandaloneMonitor(
        user_id=current_user.id,
        monitor_type="port",
        friendly_name=monitor.friendly_name,
        target=host,
        port=monitor.port,
        port_name=monitor.port_name,
        notify_email=1 if monitor.notify_email else 0,
        check_interval=monitor.check_interval,
        is_active=1,
        current_status="unknown",
    )
    
    db.add(db_monitor)
    await db.commit()
    await db.refresh(db_monitor)
    
    # Create tags
    if monitor.tags:
        await create_tags(db_monitor.id, monitor.tags, db)
        await db.commit()
        await db.refresh(db_monitor)
    
    return await build_monitor_response(db_monitor, db)


@router.post("/dns", response_model=StandaloneMonitorResponse, status_code=201)
async def create_dns_monitor(
    monitor: DNSMonitorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Create a new DNS monitor"""
    # Validate record type
    try:
        record_type = validate_record_type(monitor.record_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate interval
    try:
        validate_interval(monitor.check_interval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Create monitor
    db_monitor = StandaloneMonitor(
        user_id=current_user.id,
        monitor_type="dns",
        friendly_name=monitor.friendly_name,
        target=monitor.hostname,
        dns_server=monitor.dns_server,
        record_type=record_type,
        expected_value=monitor.expected_value,
        notify_email=1 if monitor.notify_email else 0,
        check_interval=monitor.check_interval,
        is_active=1,
        current_status="unknown",
    )
    
    db.add(db_monitor)
    await db.commit()
    await db.refresh(db_monitor)
    
    # Create tags
    if monitor.tags:
        await create_tags(db_monitor.id, monitor.tags, db)
        await db.commit()
        await db.refresh(db_monitor)
    
    return await build_monitor_response(db_monitor, db)


@router.get("/{monitor_id}", response_model=StandaloneMonitorResponse)
async def get_monitor(
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Get a specific monitor by ID"""
    result = await db.execute(
        select(StandaloneMonitor).where(
            StandaloneMonitor.id == monitor_id,
            StandaloneMonitor.user_id == current_user.id
        )
    )
    monitor = result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    return await build_monitor_response(monitor, db)


@router.patch("/{monitor_id}", response_model=StandaloneMonitorResponse)
async def update_monitor(
    monitor_id: UUID,
    update: StandaloneMonitorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Update a monitor"""
    result = await db.execute(
        select(StandaloneMonitor).where(
            StandaloneMonitor.id == monitor_id,
            StandaloneMonitor.user_id == current_user.id
        )
    )
    monitor = result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Update fields that are provided
    update_data = update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        if key == "tags":
            # Handle tags separately
            await update_tags(monitor.id, value, db)
        elif key == "url" and monitor.monitor_type == "http":
            monitor.target = value
        elif key == "host" and monitor.monitor_type in ["ping", "port"]:
            monitor.target = clean_host(value) if monitor.monitor_type == "port" else value
        elif key == "hostname" and monitor.monitor_type == "dns":
            monitor.target = value
        elif key == "notify_email":
            monitor.notify_email = 1 if value else 0
        elif key == "is_active":
            monitor.is_active = 1 if value else 0
            if not value:
                monitor.current_status = "paused"
        elif key == "check_interval":
            try:
                validate_interval(value)
                monitor.check_interval = value
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        elif key == "record_type":
            try:
                monitor.record_type = validate_record_type(value)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
        elif hasattr(monitor, key):
            setattr(monitor, key, value)
    
    await db.commit()
    await db.refresh(monitor)
    
    return await build_monitor_response(monitor, db)


@router.patch("/{monitor_id}/toggle")
async def toggle_monitor(
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Toggle monitor active/paused status"""
    result = await db.execute(
        select(StandaloneMonitor).where(
            StandaloneMonitor.id == monitor_id,
            StandaloneMonitor.user_id == current_user.id
        )
    )
    monitor = result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Toggle status
    monitor.is_active = 0 if monitor.is_active else 1
    
    if not monitor.is_active:
        monitor.current_status = "paused"
    else:
        monitor.current_status = "unknown"  # Will be updated on next check
    
    await db.commit()
    await db.refresh(monitor)
    
    return {
        "id": str(monitor.id),
        "is_active": bool(monitor.is_active),
        "message": f"Monitor {'resumed' if monitor.is_active else 'paused'} successfully"
    }


@router.delete("/{monitor_id}", status_code=204)
async def delete_monitor(
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Delete a monitor"""
    result = await db.execute(
        select(StandaloneMonitor).where(
            StandaloneMonitor.id == monitor_id,
            StandaloneMonitor.user_id == current_user.id
        )
    )
    monitor = result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Delete monitor (cascades to tags and metrics)
    await db.delete(monitor)
    await db.commit()


# ==================== METRICS ENDPOINTS ====================

@router.get("/{monitor_id}/metrics", response_model=list[StandaloneMonitorMetricResponse])
async def get_monitor_metrics(
    monitor_id: UUID,
    days: int = Query(default=7, ge=1, le=365, description="Number of days of data"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """Get check history/metrics for a monitor"""
    # Verify monitor exists and belongs to user
    monitor_result = await db.execute(
        select(StandaloneMonitor).where(
            StandaloneMonitor.id == monitor_id,
            StandaloneMonitor.user_id == current_user.id
        )
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Get metrics
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(StandaloneMonitorMetric)
        .where(
            StandaloneMonitorMetric.monitor_id == monitor_id,
            StandaloneMonitorMetric.timestamp >= since
        )
        .order_by(desc(StandaloneMonitorMetric.timestamp))
    )
    metrics = result.scalars().all()
    
    return [
        StandaloneMonitorMetricResponse(
            id=str(m.id),
            monitor_id=str(m.monitor_id),
            status=m.status,
            response_time=m.response_time,
            error_message=m.error_message,
            resolved_value=m.resolved_value,
            timestamp=m.timestamp.isoformat(),
        )
        for m in metrics
    ]


# ==================== CONFIG ENDPOINTS ====================

@router.get("/config/intervals")
async def get_interval_options():
    """Get available check interval options"""
    return {
        "intervals": [
            {"value": "30s", "label": "30 seconds", "seconds": 30},
            {"value": "1m", "label": "1 minute", "seconds": 60},
            {"value": "5m", "label": "5 minutes", "seconds": 300},
            {"value": "15m", "label": "15 minutes", "seconds": 900},
            {"value": "30m", "label": "30 minutes", "seconds": 1800},
            {"value": "1hr", "label": "1 hour", "seconds": 3600},
            {"value": "12hr", "label": "12 hours", "seconds": 43200},
        ]
    }


@router.get("/config/ports")
async def get_port_options():
    """Get available TCP port options for Port monitoring"""
    return {
        "ports": [
            {"name": name, "port": port}
            for name, port in TCP_PORTS.items()
        ]
    }


@router.get("/config/dns-record-types")
async def get_dns_record_types():
    """Get available DNS record types"""
    return {
        "record_types": DNS_RECORD_TYPES
    }
