# db.py
"""
AssetWatch Database Models

This module defines all SQLAlchemy models for the AssetWatch system.
Based on Wanaware's asset management architecture.

Models:
- Organization: Multi-tenant organization model with hierarchical support
- Post: Simple blog posts (kept for backwards compatibility)
- User: User authentication via fastapi-users (now with organization membership)
- FilePost: File uploads linked to users
- Asset: Network/compute/security assets to monitor
- Monitor: Performance or Availability monitors attached to assets
- PerformanceMetric: CPU, Memory, Disk I/O, Latency data
- AvailabilityMetric: Status, Response Time, Uptime data

Organization Types & Permissions:
- assetwatch: Super admin - can CRUD all organizations
- reseller: Can CRUD their own reseller_customers, read/update self
- customer: Direct customer - can read/update self only
- reseller_customer: Reseller's customer - can read/update self only
"""

import uuid
from datetime import datetime
from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy import Column, ForeignKey, String, DateTime, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
# For user authentication
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID


# Async SQLite URL
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Engine with echo=True for SQL logging (disable in production)
engine = create_async_engine(DATABASE_URL, echo=True)
# Session maker for async database operations
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# Base class for all models (SQLAlchemy 2.0 style)
class Base(DeclarativeBase):
    pass


# ==================== ORGANIZATION MODEL (for multi-tenant RBAC) ====================

class Organization(Base):
    """
    Organization model for multi-tenant RBAC (Role-Based Access Control).
    
    This is the core model for permission management. Each user belongs to an organization,
    and the organization type determines their permissions.
    
    Organization Types:
    - assetwatch: Super admin organization (only one should exist)
                  Can CRUD all customers, resellers, and their data
    - reseller: Partner organization that can manage their own customers
                Can CRUD their own reseller_customers, read/update self
    - customer: Direct customer of AssetWatch
                Can read/update self only
    - reseller_customer: Customer created by a reseller
                         Can read/update self only
    
    Hierarchy:
    - assetwatch (top level, parent_organization_id = null)
      ├── customer (parent_organization_id = null, direct customer)
      └── reseller (parent_organization_id = null)
          └── reseller_customer (parent_organization_id = reseller.id)
    """
    __tablename__ = "organizations"

    # Primary key - UUID for better security
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Organization type determines permissions
    # Valid values: "assetwatch", "customer", "reseller", "reseller_customer"
    organization_type = Column(
        String, 
        nullable=False,
        index=True,
        comment="One of: assetwatch, customer, reseller, reseller_customer"
    )
    
    # Human-readable organization name
    organization_name = Column(String, nullable=False, index=True)
    
    # Contact email for the organization (must be unique)
    organization_email = Column(String, nullable=False, unique=True)
    
    # Parent organization for hierarchy support
    # - null for assetwatch, customer, reseller (top-level orgs)
    # - reseller.id for reseller_customer (child of reseller)
    parent_organization_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("organizations.id"), 
        nullable=True,
        comment="Parent org ID - set for reseller_customer, null for others"
    )
    
    # Timestamps for auditing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referential relationship for parent/children
    parent = relationship(
        "Organization", 
        remote_side=[id], 
        backref="children",
        foreign_keys=[parent_organization_id]
    )
    
    # NOTE: User IS now the organization, so no users relationship needed here


# ==================== EXISTING MODELS (kept for backwards compatibility) ====================

class Post(Base):
    """Simple blog post model - kept for backwards compatibility"""
    __tablename__ = "posts"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    caption = Column(String)


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    User model - User IS the Organization.
    user.id = org_id, user.email = org_email, user.name = org_name
    """
    # Display name (also serves as organization_name)
    name = Column(String, nullable=False, default="")
    
    # Role: assetwatch, customer, reseller, reseller_customer
    organization_type = Column(String, nullable=False, default="customer", index=True)
    
    # Parent org (for reseller_customer → points to reseller's user.id)
    parent_organization_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    
    # Profile image URL (stored via ImageKit)
    profile_image_url = Column(String, nullable=True)
    
    # Relationships
    File_Posts = relationship("FilePost", back_populates="user")
    assets = relationship("Asset", back_populates="user")
    standalone_monitors = relationship("StandaloneMonitor", back_populates="user", cascade="all, delete-orphan")
    

class FilePost(Base):
    """File upload model linked to users"""
    __tablename__ = "file_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    caption = Column(Text)
    url = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="File_Posts")


# ==================== ASSETWATCH MODELS ====================

class Asset(Base):
    """
    Represents a network/compute/security asset that can be monitored.
    
    Asset types are based on Wanaware categories:
    - Circuit types: Internet (Cable, Fiber, Wireless, etc.), MPLS, Private Line, PRI, POTS, SIP
    - Network Assets: IP Block, Router, SD-WAN, Switch, WAP, Load Balancer
    - Security Assets: Firewall, IDS, IPS, NDR, WAF
    - Compute Assets: Server, Laptop, Desktop
    - Storage Assets: SAN
    
    An asset can have multiple monitors attached (both performance and availability).
    """
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Basic asset information
    name = Column(String, nullable=False, index=True)  # User-friendly name (e.g., "Main Office Router")
    asset_type = Column(String, nullable=False)  # One of the Wanaware asset types
    description = Column(Text, nullable=True)  # Optional description
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Owner relationship
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    user = relationship("User", back_populates="assets")
    
    # Monitors attached to this asset (cascading delete)
    monitors = relationship("Monitor", back_populates="asset", cascade="all, delete-orphan")


class Monitor(Base):
    """
    A monitor attached to an asset. Each monitor has its own target configuration.
    
    Monitor Types:
    - "performance": Tracks CPU, Memory, Disk I/O, Latency using SNMP/ICMP
    - "availability": Tracks uptime, response time, status using ping/HTTP
    
    Target Configuration:
    - target: IP address or hostname to monitor
    - target_type: "ip" or "hostname"
    - port: Optional port number for specific service monitoring
    
    For Performance monitors:
    - protocol: "icmp" | "http" | "https"
    - check_interval: 60 (1min), 300 (5min), 900 (15min) seconds
    
    For Availability monitors:
    - circuit_type: "dia" (Dedicated Internet Access) | "broadband"
    - check_interval: 30, 60, 300, 900 seconds
    """
    __tablename__ = "monitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    monitor_type = Column(String, nullable=False)  # "performance" | "availability"
    
    # Target configuration - what to monitor
    target = Column(String, nullable=False)  # IP address or hostname
    target_type = Column(String, nullable=False)  # "ip" | "hostname"
    port = Column(Integer, nullable=True)  # Optional port number (1-65535)
    
    # Protocol/Circuit type (depends on monitor_type)
    protocol = Column(String, nullable=True)  # For performance: "icmp" | "http" | "https"
    circuit_type = Column(String, nullable=True)  # For availability: "dia" | "broadband"
    
    # Check interval in seconds
    check_interval = Column(Integer, nullable=False, default=300)  # Default 5 minutes
    
    # Status tracking
    is_active = Column(Integer, default=1)  # 1 = active, 0 = paused
    last_check_at = Column(DateTime, nullable=True)  # When was last check performed
    current_status = Column(String, default="unknown")  # "up" | "down" | "unknown"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    asset = relationship("Asset", back_populates="monitors")
    performance_metrics = relationship("PerformanceMetric", back_populates="monitor", cascade="all, delete-orphan")
    availability_metrics = relationship("AvailabilityMetric", back_populates="monitor", cascade="all, delete-orphan")


class PerformanceMetric(Base):
    """
    Stores performance metrics collected from a performance monitor.
    
    Metrics collected (would use SNMP in production, simulated for now):
    - cpu_usage: CPU utilization percentage (0-100)
    - memory_usage: Memory utilization percentage (0-100)
    - disk_io: Disk I/O throughput in MB/s
    - latency: Network latency to target in milliseconds
    
    Each record represents a single data point at a specific timestamp.
    """
    __tablename__ = "performance_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id"), nullable=False)
    
    # Performance data points
    cpu_usage = Column(Float, nullable=False)  # Percentage (0-100)
    memory_usage = Column(Float, nullable=False)  # Percentage (0-100)
    disk_io = Column(Float, nullable=False)  # MB/s
    latency = Column(Float, nullable=False)  # Milliseconds
    
    # When this metric was recorded
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    monitor = relationship("Monitor", back_populates="performance_metrics")


class AvailabilityMetric(Base):
    """
    Stores availability metrics collected from an availability monitor.
    
    Metrics collected:
    - status: Current status "UP" or "DOWN"
    - response_time: Time taken to get response in milliseconds
    - uptime_percentage: Calculated uptime over recent checks
    - packet_loss: Percentage of packets lost (for ICMP checks)
    
    Each record represents a single check at a specific timestamp.
    """
    __tablename__ = "availability_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id"), nullable=False)
    
    # Availability data points
    status = Column(String, nullable=False)  # "UP" | "DOWN"
    response_time = Column(Float, nullable=False)  # Milliseconds
    uptime_percentage = Column(Float, nullable=False)  # Percentage over check period
    packet_loss = Column(Float, nullable=True, default=0.0)  # Percentage of packets lost
    
    # When this metric was recorded
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    monitor = relationship("Monitor", back_populates="availability_metrics")


# ==================== STANDALONE MONITOR MODELS (UptimeRobot-style) ====================

class StandaloneMonitor(Base):
    """
    Standalone monitors for the Monitoring tab (UptimeRobot-style).
    Unlike asset-attached monitors, these are independent and user-owned directly.
    
    Monitor Types:
    - "http": HTTP(S) website/API monitoring
    - "ping": ICMP ping monitoring
    - "port": TCP port monitoring  
    - "dns": DNS record monitoring
    
    These monitors are NOT attached to assets - they exist independently
    and are designed for simple uptime/availability checking.
    """
    __tablename__ = "standalone_monitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    
    # Monitor type: http, ping, port, dns
    monitor_type = Column(String, nullable=False, index=True)
    
    # User-friendly display name
    friendly_name = Column(String, nullable=False)
    
    # Target to monitor (URL for http, IP/hostname for ping/port, hostname for dns)
    target = Column(String, nullable=False)
    
    # Port monitoring specific fields
    port = Column(Integer, nullable=True)  # TCP port number (1-65535)
    port_name = Column(String, nullable=True)  # Service name e.g., "HTTP", "SSH", "MySQL"
    
    # DNS monitoring specific fields
    dns_server = Column(String, nullable=True)  # DNS server to query (optional)
    record_type = Column(String, nullable=True)  # A, AAAA, CNAME, MX, TXT, NS, SOA
    expected_value = Column(String, nullable=True)  # Expected DNS response value
    
    # Notification settings
    notify_email = Column(Integer, default=1)  # 1=enabled, 0=disabled
    
    # Check interval: 30s, 1m, 5m, 15m, 30m, 1hr, 12hr
    check_interval = Column(String, default="5m", nullable=False)
    
    # Status tracking
    is_active = Column(Integer, default=1)  # 1=active, 0=paused
    current_status = Column(String, default="unknown")  # up, down, unknown
    last_check_at = Column(DateTime, nullable=True)
    response_time = Column(Float, nullable=True)  # Last response time in ms
    
    # Worker scheduling fields
    next_check_at = Column(DateTime, nullable=True)  # When worker should check next
    consecutive_failures = Column(Integer, default=0)  # Track failures before marking down
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="standalone_monitors")
    tags = relationship("MonitorTag", back_populates="monitor", cascade="all, delete-orphan")
    metrics = relationship("StandaloneMonitorMetric", back_populates="monitor", cascade="all, delete-orphan")


class MonitorTag(Base):
    """
    Tags for organizing standalone monitors.
    Many-to-one relationship: each tag belongs to one monitor,
    but a monitor can have many tags.
    """
    __tablename__ = "monitor_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("standalone_monitors.id"), nullable=False)
    
    # Tag value (e.g., "production", "critical", "api")
    tag = Column(String, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    monitor = relationship("StandaloneMonitor", back_populates="tags")


class StandaloneMonitorMetric(Base):
    """
    Stores check history/metrics for standalone monitors.
    
    Each record represents a single check at a specific timestamp.
    Used for calculating uptime percentage and response time trends.
    """
    __tablename__ = "standalone_monitor_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("standalone_monitors.id"), nullable=False)
    
    # Check result
    status = Column(String, nullable=False)  # "up" | "down"
    response_time = Column(Float, nullable=True)  # Response time in ms
    
    # Error details (if down)
    error_message = Column(Text, nullable=True)
    
    # DNS specific - actual resolved value
    resolved_value = Column(String, nullable=True)
    
    # When this check was performed
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    monitor = relationship("StandaloneMonitor", back_populates="metrics")
    
    
# call this on app startup
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)
    
    
