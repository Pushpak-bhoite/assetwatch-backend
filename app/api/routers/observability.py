"""
Observability API Router

Provides endpoints for the observability dashboard with aggregated
asset and monitor data for AG Grid server-side row model.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Literal
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

from app.core.db import Asset, Monitor, User, get_db
from app.users import current_active_user
from app.api.dependencies import check_permission
from app.api.routers.models.observability_models import (PaginatedObservabilityResponse, MonitorSummary, ObservabilityAssetItem, MonitorDetailItem)

router = APIRouter(prefix="/observability", tags=["observability"])


# ==================== ENDPOINTS ====================

@router.get("/assets", response_model=PaginatedObservabilityResponse)
async def get_observability_assets(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    sort_by: str = Query("name", description="Field to sort by"),
    order: Literal["asc", "desc"] = Query("asc", description="Sort order"),
    search: Optional[str] = Query(None, description="Search term for asset name"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    status: Optional[str] = Query(None, description="Filter by monitor status (up, down, unknown)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get assets with aggregated monitor data for observability dashboard.
    
    Returns assets with:
    - Monitor counts by type (performance, availability)
    - Status counts (up, down, unknown)
    - Active/Paused counts
    - Last check timestamp
    
    Designed for AG Grid server-side row model with master-detail.
    """
    
    # Map sortable fields
    sortable_fields = {
        "name": Asset.name,
        "asset_type": Asset.asset_type,
        "created_at": Asset.created_at,
        "updated_at": Asset.updated_at,
    }
    
    # Base query
    query = select(Asset).where(Asset.user_id == current_user.id)
    count_query = select(func.count(Asset.id)).where(Asset.user_id == current_user.id)
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.where(Asset.name.ilike(search_filter))
        count_query = count_query.where(Asset.name.ilike(search_filter))
    
    # Apply asset_type filter
    if asset_type:
        query = query.where(Asset.asset_type == asset_type)
        count_query = count_query.where(Asset.asset_type == asset_type)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply sorting
    sort_column = sortable_fields.get(sort_by, Asset.name)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    assets = result.scalars().all()
    
    # Build response with monitor aggregations
    response_items = []
    for asset in assets:
        # Get all monitors for this asset
        monitors_result = await db.execute(
            select(Monitor).where(Monitor.asset_id == asset.id)
        )
        monitors = monitors_result.scalars().all()
        
        # Calculate aggregations
        monitor_summary = MonitorSummary(
            total=len(monitors),
            performance_count=sum(1 for m in monitors if m.monitor_type == "performance"),
            availability_count=sum(1 for m in monitors if m.monitor_type == "availability"),
            up_count=sum(1 for m in monitors if m.current_status == "up"),
            down_count=sum(1 for m in monitors if m.current_status == "down"),
            unknown_count=sum(1 for m in monitors if m.current_status == "unknown"),
            active_count=sum(1 for m in monitors if m.is_active),
            paused_count=sum(1 for m in monitors if not m.is_active),
        )
        
        # Get most recent check timestamp
        last_check = None
        for m in monitors:
            if m.last_check_at:
                if last_check is None or m.last_check_at > last_check:
                    last_check = m.last_check_at
        
        # Apply status filter if specified
        if status:
            if status == "up" and monitor_summary.up_count == 0:
                continue
            elif status == "down" and monitor_summary.down_count == 0:
                continue
            elif status == "unknown" and monitor_summary.unknown_count == 0:
                continue
        
        response_items.append(ObservabilityAssetItem(
            id=str(asset.id),
            name=asset.name,
            asset_type=asset.asset_type,
            description=asset.description,
            monitor_summary=monitor_summary,
            last_check_at=last_check.isoformat() if last_check else None,
            created_at=asset.created_at.isoformat(),
            updated_at=asset.updated_at.isoformat(),
        ))
    
    # Calculate total pages
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return PaginatedObservabilityResponse(
        data=response_items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.get("/assets/{asset_id}/monitors", response_model=list[MonitorDetailItem])
async def get_asset_monitors(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Get all monitors for a specific asset.
    
    Used for the detail row expansion in AG Grid master-detail.
    """
    # Verify asset exists and belongs to user
    asset_result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == current_user.id)
    )
    asset = asset_result.scalars().first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get monitors
    monitors_result = await db.execute(
        select(Monitor).where(Monitor.asset_id == asset_id).order_by(Monitor.created_at.desc())
    )
    monitors = monitors_result.scalars().all()
    
    return [
        MonitorDetailItem(
            id=str(m.id),
            asset_id=str(m.asset_id),
            monitor_type=m.monitor_type,
            target=m.target,
            target_type=m.target_type,
            port=m.port,
            protocol=m.protocol,
            circuit_type=m.circuit_type,
            check_interval=m.check_interval,
            is_active=bool(m.is_active),
            current_status=m.current_status,
            last_check_at=m.last_check_at.isoformat() if m.last_check_at else None,
            created_at=m.created_at.isoformat(),
            updated_at=m.updated_at.isoformat(),
        )
        for m in monitors
    ]


@router.patch("/monitors/{monitor_id}/toggle")
async def toggle_monitor_status(
    monitor_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user),
):
    """
    Toggle monitor active/paused status.
    """
    # Get monitor and verify ownership
    monitor_result = await db.execute(
        select(Monitor).where(Monitor.id == monitor_id)
    )
    monitor = monitor_result.scalars().first()
    
    if not monitor:
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Verify asset belongs to user
    asset_result = await db.execute(
        select(Asset).where(Asset.id == monitor.asset_id, Asset.user_id == current_user.id)
    )
    if not asset_result.scalars().first():
        raise HTTPException(status_code=404, detail="Monitor not found")
    
    # Toggle status
    monitor.is_active = 0 if monitor.is_active else 1
    await db.commit()
    await db.refresh(monitor)
    
    return {
        "id": str(monitor.id),
        "is_active": bool(monitor.is_active),
        "message": f"Monitor {'resumed' if monitor.is_active else 'paused'} successfully"
    }
