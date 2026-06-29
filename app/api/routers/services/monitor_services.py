
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from uuid import UUID

import re
from app.core.db import User, StandaloneMonitor, MonitorTag, StandaloneMonitorMetric, get_db
from app.users import current_active_user
from app.api.routers.models.monitors_models import (
    StandaloneMonitorResponse,
)

# ==================== CONSTANTS ====================

# Check intervals in seconds
INTERVAL_OPTIONS = {
    "30s": 30,
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1hr": 3600,
    "12hr": 43200,
}

# TCP Port options for Port monitoring
TCP_PORTS = {
    "FTP": 21,
    "SSH/SFTP": 22,
    "SMTP": 25,
    "DNS": 53,
    "HTTP": 80,
    "POP3": 110,
    "IMAP": 143,
    "HTTPS": 443,
    "SMTP-SSL": 465,
    "SMTP-TLS": 587,
    "IMAP-SSL": 993,
    "POP3-SSL": 995,
    "MySQL": 3306,
}

# DNS Record types
DNS_RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "TXT", "NS", "SOA"]




# ==================== HELPER FUNCTIONS ====================

def validate_url(url: str) -> str:
    """Validate and return URL"""
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must start with http:// or https://")
    return url


def validate_host(host: str) -> str:
    """Validate IP address or hostname"""
    ip_regex = r'^(\d{1,3}\.){3}\d{1,3}$'
    hostname_regex = r'^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$'
    if not (re.match(ip_regex, host) or re.match(hostname_regex, host) or len(host) >= 2):
        raise ValueError("Enter a valid IP address or hostname")
    return host


def validate_interval(interval: str) -> str:
    """Validate check interval"""
    if interval not in INTERVAL_OPTIONS:
        raise ValueError(f"Invalid interval. Must be one of: {', '.join(INTERVAL_OPTIONS.keys())}")
    return interval


def validate_record_type(record_type: str) -> str:
    """Validate DNS record type"""
    if record_type.upper() not in DNS_RECORD_TYPES:
        raise ValueError(f"Invalid record type. Must be one of: {', '.join(DNS_RECORD_TYPES)}")
    return record_type.upper()


def clean_host(host: str) -> str:
    """Remove protocol prefix if present"""
    if host.startswith(('http://', 'https://')):
        host = host.replace('http://', '').replace('https://', '').split('/')[0]
    return host


async def get_tags_list(monitor_id: UUID, db: AsyncSession) -> list[str]:
    """Get list of tags for a monitor"""
    result = await db.execute(
        select(MonitorTag.tag).where(MonitorTag.monitor_id == monitor_id)
    )
    return [row[0] for row in result.fetchall()]


async def calculate_uptime_percentage(
    monitor_id: UUID,
    db: AsyncSession,
    days: int = 30
) -> Optional[float]:
    """Calculate uptime percentage from metrics"""
    since = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(StandaloneMonitorMetric).where(
            StandaloneMonitorMetric.monitor_id == monitor_id,
            StandaloneMonitorMetric.timestamp >= since
        )
    )
    metrics = result.scalars().all()
    
    if not metrics:
        return None
    
    up_count = sum(1 for m in metrics if m.status == "up")
    return round((up_count / len(metrics)) * 100, 2)


async def build_monitor_response(
    monitor: StandaloneMonitor,
    db: AsyncSession
) -> StandaloneMonitorResponse:
    """Build response object for a monitor"""
    tags = await get_tags_list(monitor.id, db)
    uptime = await calculate_uptime_percentage(monitor.id, db)
    
    return StandaloneMonitorResponse(
        id=str(monitor.id),
        user_id=str(monitor.user_id),
        monitor_type=monitor.monitor_type,
        friendly_name=monitor.friendly_name,
        target=monitor.target,
        tags=tags,
        notify_email=bool(monitor.notify_email),
        check_interval=monitor.check_interval,
        check_interval_seconds=INTERVAL_OPTIONS.get(monitor.check_interval, 300),
        is_active=bool(monitor.is_active),
        current_status=monitor.current_status if monitor.is_active else "paused",
        last_check_at=monitor.last_check_at.isoformat() if monitor.last_check_at else None,
        response_time=monitor.response_time,
        uptime_percentage=uptime,
        created_at=monitor.created_at.isoformat(),
        updated_at=monitor.updated_at.isoformat(),
        port=monitor.port,
        port_name=monitor.port_name,
        dns_server=monitor.dns_server,
        record_type=monitor.record_type,
        expected_value=monitor.expected_value,
    )


async def create_tags(monitor_id: UUID, tags: list[str], db: AsyncSession):
    """Create tags for a monitor"""
    for tag in tags:
        if tag.strip():  # Skip empty tags
            db_tag = MonitorTag(
                monitor_id=monitor_id,
                tag=tag.strip()
            )
            db.add(db_tag)


async def update_tags(monitor_id: UUID, tags: list[str], db: AsyncSession):
    """Replace all tags for a monitor"""
    # Delete existing tags
    existing_tags = await db.execute(
        select(MonitorTag).where(MonitorTag.monitor_id == monitor_id)
    )
    for tag in existing_tags.scalars().all():
        await db.delete(tag)
    
    # Create new tags
    await create_tags(monitor_id, tags, db)
