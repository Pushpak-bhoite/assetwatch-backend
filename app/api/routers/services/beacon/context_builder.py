"""
Beacon Context Builder

Builds context from user's database (monitors, metrics, dashboard data)
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
    monitors, metrics, and dashboard data.
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
        Build a summary context of user's monitoring data.
        
        Returns:
            Formatted string with user's monitor summary (primary focus)
        """
        context_parts = []
        
        # Get all assets (needed to fetch monitors)
        assets_result = await self.db.execute(
            select(Asset).where(Asset.user_id == self.user_id)
        )
        assets = assets_result.scalars().all()
        
        if not assets:
            return "User has no monitors configured yet. They can start by creating a monitor to track their services."
        
        # Get all monitors
        asset_ids = [a.id for a in assets]
        monitors_result = await self.db.execute(
            select(Monitor).where(Monitor.asset_id.in_(asset_ids))
        )
        monitors = monitors_result.scalars().all()
        
        # Monitors Summary (Primary Focus)
        context_parts.append(f"## Monitors Summary")
        context_parts.append(f"Total Monitors: {len(monitors)}")
        
        if monitors:
            # Count by status
            up_count = sum(1 for m in monitors if m.current_status == "up")
            down_count = sum(1 for m in monitors if m.current_status == "down")
            unknown_count = sum(1 for m in monitors if m.current_status == "unknown")
            
            context_parts.append(f"- ✅ UP: {up_count}")
            context_parts.append(f"- ⚠️ DOWN: {down_count}")
            if unknown_count > 0:
                context_parts.append(f"- Unknown: {unknown_count}")
            
            # Count by type
            perf_count = sum(1 for m in monitors if m.monitor_type == "performance")
            avail_count = sum(1 for m in monitors if m.monitor_type == "availability")
            context_parts.append(f"\nMonitor Types:")
            context_parts.append(f"- Performance Monitors: {perf_count}")
            context_parts.append(f"- Availability Monitors: {avail_count}")
            
            # List monitors with issues first
            down_monitors = [m for m in monitors if m.current_status == "down"]
            if down_monitors:
                context_parts.append(f"\n## Monitors Needing Attention")
                for m in down_monitors[:5]:
                    asset = next((a for a in assets if a.id == m.asset_id), None)
                    asset_name = asset.name if asset else "Unknown"
                    last_check = m.last_check_at.strftime('%Y-%m-%d %H:%M') if m.last_check_at else "Never"
                    context_parts.append(
                        f"- **{m.target}** ({m.monitor_type}) - DOWN since {last_check}"
                    )
            
            # List healthy monitors
            up_monitors = [m for m in monitors if m.current_status == "up"]
            if up_monitors:
                context_parts.append(f"\n## Healthy Monitors")
                for m in up_monitors[:5]:
                    context_parts.append(f"- {m.target} ({m.monitor_type}) - UP")
                if len(up_monitors) > 5:
                    context_parts.append(f"  ... and {len(up_monitors) - 5} more")
        else:
            context_parts.append("No monitors configured yet.")
        
        return "\n".join(context_parts)
    
    async def build_monitor_context(self, target: Optional[str] = None) -> str:
        """
        Build detailed context for monitors.
        
        Args:
            target: Optional target/URL to filter by
            
        Returns:
            Formatted string with monitor details
        """
        # Get all assets for this user
        assets_result = await self.db.execute(
            select(Asset).where(Asset.user_id == self.user_id)
        )
        assets = assets_result.scalars().all()
        
        if not assets:
            return "No monitors found. Create a monitor to start tracking your services."
        
        asset_ids = [a.id for a in assets]
        query = select(Monitor).where(Monitor.asset_id.in_(asset_ids))
        
        if target:
            query = query.where(Monitor.target.ilike(f"%{target}%"))
        
        result = await self.db.execute(query)
        monitors = result.scalars().all()
        
        if not monitors:
            return f"No monitors found{' matching: ' + target if target else ''}"
        
        context_parts = []
        context_parts.append(f"## Monitor Details ({len(monitors)} total)")
        
        for m in monitors[:10]:  # Limit for context size
            asset = next((a for a in assets if a.id == m.asset_id), None)
            last_check = m.last_check_at.strftime('%Y-%m-%d %H:%M') if m.last_check_at else "Never"
            status_icon = "✅" if m.current_status == "up" else "⚠️" if m.current_status == "down" else "❓"
            
            context_parts.append(f"\n**{m.target}**")
            context_parts.append(f"  - Type: {m.monitor_type.title()}")
            context_parts.append(f"  - Status: {status_icon} {m.current_status.upper()}")
            context_parts.append(f"  - Last Check: {last_check}")
            context_parts.append(f"  - Check Interval: {m.check_interval}s")
        
        if len(monitors) > 10:
            context_parts.append(f"\n... and {len(monitors) - 10} more monitors")
        
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
            return "No monitors to show metrics for."
        
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
        Build comprehensive context combining monitor summary and metrics.
        
        Returns:
            Full context string for the LLM (monitors-focused)
        """
        summary = await self.build_summary_context()
        metrics = await self.build_metrics_context(days=1)
        
        return f"{summary}\n\n{metrics}"
