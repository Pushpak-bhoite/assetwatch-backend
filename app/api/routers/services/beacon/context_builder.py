"""
Beacon Context Builder

Builds context from user's database (assets, monitors, metrics)
for personalized responses.
"""

from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.db import Asset, Monitor, PerformanceMetric, AvailabilityMetric


class ContextBuilder:
    """
    Builds context from user's data for Beacon responses.
    
    Queries the database to get relevant information about the user's
    assets, monitors, and recent metrics.
    """
    
    def __init__(self, db: AsyncSession, user_id: UUID):
        """
        Initialize context builder.
        
        Args:
            db: Database session
            user_id: Current user's ID
        """
        self.db = db
        self.user_id = user_id
    
    async def build_summary_context(self) -> str:
        """
        Build a summary context of all user's data.
        
        Returns:
            Formatted string with user's asset and monitor summary
        """
        context_parts = []
        
        # Get all assets
        assets_result = await self.db.execute(
            select(Asset).where(Asset.user_id == self.user_id)
        )
        assets = assets_result.scalars().all()
        
        if not assets:
            return "User has no assets configured yet."
        
        # Build asset summary
        context_parts.append(f"## User's Assets Summary")
        context_parts.append(f"Total Assets: {len(assets)}")
        
        # Group by type
        asset_types = {}
        for asset in assets:
            asset_type = asset.asset_type.split("-")[0] if "-" in asset.asset_type else asset.asset_type
            asset_types[asset_type] = asset_types.get(asset_type, 0) + 1
        
        context_parts.append("\nAsset Types:")
        for atype, count in asset_types.items():
            context_parts.append(f"- {atype}: {count}")
        
        # Get all monitors
        asset_ids = [a.id for a in assets]
        monitors_result = await self.db.execute(
            select(Monitor).where(Monitor.asset_id.in_(asset_ids))
        )
        monitors = monitors_result.scalars().all()
        
        context_parts.append(f"\n## Monitors Summary")
        context_parts.append(f"Total Monitors: {len(monitors)}")
        
        if monitors:
            # Count by status
            up_count = sum(1 for m in monitors if m.current_status == "up")
            down_count = sum(1 for m in monitors if m.current_status == "down")
            unknown_count = sum(1 for m in monitors if m.current_status == "unknown")
            
            context_parts.append(f"- UP: {up_count}")
            context_parts.append(f"- DOWN: {down_count}")
            context_parts.append(f"- Unknown: {unknown_count}")
            
            # Count by type
            perf_count = sum(1 for m in monitors if m.monitor_type == "performance")
            avail_count = sum(1 for m in monitors if m.monitor_type == "availability")
            context_parts.append(f"\nMonitor Types:")
            context_parts.append(f"- Performance: {perf_count}")
            context_parts.append(f"- Availability: {avail_count}")
        
        # Asset details
        context_parts.append(f"\n## Asset Details")
        for asset in assets[:10]:  # Limit to 10 for context size
            asset_monitors = [m for m in monitors if m.asset_id == asset.id]
            status_str = ""
            if asset_monitors:
                statuses = [m.current_status for m in asset_monitors]
                if "down" in statuses:
                    status_str = "⚠️ Has DOWN monitors"
                elif all(s == "up" for s in statuses):
                    status_str = "✅ All UP"
                else:
                    status_str = "⏳ Mixed status"
            
            context_parts.append(f"\n**{asset.name}** ({asset.asset_type})")
            context_parts.append(f"  - Monitors: {len(asset_monitors)} {status_str}")
            if asset.description:
                context_parts.append(f"  - Description: {asset.description[:100]}")
        
        if len(assets) > 10:
            context_parts.append(f"\n... and {len(assets) - 10} more assets")
        
        return "\n".join(context_parts)
    
    async def build_asset_context(self, asset_name: Optional[str] = None) -> str:
        """
        Build detailed context for a specific asset or all assets.
        
        Args:
            asset_name: Optional asset name to filter by
            
        Returns:
            Formatted string with asset details
        """
        query = select(Asset).where(Asset.user_id == self.user_id)
        
        if asset_name:
            query = query.where(Asset.name.ilike(f"%{asset_name}%"))
        
        result = await self.db.execute(query)
        assets = result.scalars().all()
        
        if not assets:
            return f"No assets found{' matching: ' + asset_name if asset_name else ''}"
        
        context_parts = []
        
        for asset in assets[:5]:  # Limit for context size
            context_parts.append(f"\n## Asset: {asset.name}")
            context_parts.append(f"Type: {asset.asset_type}")
            context_parts.append(f"Description: {asset.description or 'None'}")
            context_parts.append(f"Created: {asset.created_at.strftime('%Y-%m-%d')}")
            
            # Get monitors
            monitors_result = await self.db.execute(
                select(Monitor).where(Monitor.asset_id == asset.id)
            )
            monitors = monitors_result.scalars().all()
            
            if monitors:
                context_parts.append(f"\nMonitors ({len(monitors)}):")
                for m in monitors:
                    last_check = m.last_check_at.strftime('%Y-%m-%d %H:%M') if m.last_check_at else "Never"
                    context_parts.append(
                        f"- {m.monitor_type.title()} → {m.target} | "
                        f"Status: {m.current_status.upper()} | "
                        f"Last Check: {last_check}"
                    )
        
        return "\n".join(context_parts)
    
    async def build_metrics_context(self, days: int = 1) -> str:
        """
        Build context with recent metrics data.
        
        Args:
            days: Number of days of metrics to include
            
        Returns:
            Formatted string with recent metrics
        """
        # Get user's assets and monitors
        assets_result = await self.db.execute(
            select(Asset).where(Asset.user_id == self.user_id)
        )
        assets = assets_result.scalars().all()
        
        if not assets:
            return "No assets to show metrics for."
        
        asset_ids = [a.id for a in assets]
        monitors_result = await self.db.execute(
            select(Monitor).where(Monitor.asset_id.in_(asset_ids))
        )
        monitors = monitors_result.scalars().all()
        
        if not monitors:
            return "No monitors configured yet."
        
        context_parts = [f"## Recent Metrics (Last {days} day(s))"]
        date_filter = datetime.utcnow() - timedelta(days=days)
        
        # Performance metrics summary
        perf_monitors = [m for m in monitors if m.monitor_type == "performance"]
        if perf_monitors:
            perf_ids = [m.id for m in perf_monitors]
            perf_result = await self.db.execute(
                select(PerformanceMetric)
                .where(
                    PerformanceMetric.monitor_id.in_(perf_ids),
                    PerformanceMetric.timestamp >= date_filter
                )
            )
            perf_metrics = perf_result.scalars().all()
            
            if perf_metrics:
                cpu_values = [m.cpu_usage for m in perf_metrics]
                mem_values = [m.memory_usage for m in perf_metrics]
                lat_values = [m.latency for m in perf_metrics]
                
                context_parts.append(f"\n**Performance Metrics** ({len(perf_metrics)} data points)")
                context_parts.append(f"- CPU: Avg {sum(cpu_values)/len(cpu_values):.1f}%, Max {max(cpu_values):.1f}%")
                context_parts.append(f"- Memory: Avg {sum(mem_values)/len(mem_values):.1f}%, Max {max(mem_values):.1f}%")
                context_parts.append(f"- Latency: Avg {sum(lat_values)/len(lat_values):.1f}ms, Max {max(lat_values):.1f}ms")
        
        # Availability metrics summary
        avail_monitors = [m for m in monitors if m.monitor_type == "availability"]
        if avail_monitors:
            avail_ids = [m.id for m in avail_monitors]
            avail_result = await self.db.execute(
                select(AvailabilityMetric)
                .where(
                    AvailabilityMetric.monitor_id.in_(avail_ids),
                    AvailabilityMetric.timestamp >= date_filter
                )
            )
            avail_metrics = avail_result.scalars().all()
            
            if avail_metrics:
                up_count = sum(1 for m in avail_metrics if m.status == "UP")
                total = len(avail_metrics)
                uptime = (up_count / total) * 100 if total > 0 else 0
                
                context_parts.append(f"\n**Availability Metrics** ({total} checks)")
                context_parts.append(f"- Uptime: {uptime:.2f}%")
                context_parts.append(f"- UP checks: {up_count}")
                context_parts.append(f"- DOWN checks: {total - up_count}")
        
        return "\n".join(context_parts)
    
    async def build_full_context(self) -> str:
        """
        Build comprehensive context combining summary, assets, and metrics.
        
        Returns:
            Full context string for the LLM
        """
        summary = await self.build_summary_context()
        metrics = await self.build_metrics_context(days=1)
        
        return f"{summary}\n\n{metrics}"
