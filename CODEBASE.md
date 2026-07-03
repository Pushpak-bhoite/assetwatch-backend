# AssetWatch Backend - Codebase Documentation

> **For Developers & LLM Agents**: This document provides a complete overview of the AssetWatch backend codebase. Use this as your primary reference to understand the architecture, folder structure, and how components interact.

---

## Quick Summary

**AssetWatch** is a network infrastructure monitoring platform (mini Wanaware.com) with:
- **FastAPI** backend with async SQLAlchemy
- **Multi-tenant RBAC** via Permit.io
- **Background worker** for scheduled monitoring checks
- **Beacon AI chatbot** with RAG using Gemini + ChromaDB

**Tech Stack**: Python 3.12+ | FastAPI | SQLAlchemy (async) | SQLite/PostgreSQL | APScheduler | LangChain | ChromaDB | Permit.io | SendGrid

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ASSETWATCH SYSTEM                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐     ┌──────────────────┐                     │
│  │   FastAPI App    │     │  Background      │                     │
│  │   (app.app:app)  │     │  Worker          │                     │
│  │                  │     │  (worker.main)   │                     │
│  │  - REST API      │     │                  │                     │
│  │  - Auth (JWT)    │     │  - APScheduler   │                     │
│  │  - Beacon Chat   │     │  - Checkers      │                     │
│  └────────┬─────────┘     └────────┬─────────┘                     │
│           │                        │                               │
│           └────────────┬───────────┘                               │
│                        ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     SQLite/PostgreSQL                        │   │
│  │  - Users (with org roles)  - Assets        - Monitors        │   │
│  │  - StandaloneMonitors      - Metrics       - Incidents       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  External Services:                                                │
│  - Permit.io (RBAC)  - SendGrid (Email)  - Gemini (AI)  - ImageKit │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure (Essential Files Only)

```
assetwatch-backend/
│
├── main.py                    # Dev entry point (runs uvicorn with reload)
├── pyproject.toml             # Dependencies & project config (uv/poetry)
├── .env                       # Environment variables (not committed)
│
├── app/                       # 🎯 MAIN APPLICATION
│   ├── app.py                 # FastAPI app initialization, lifespan, CORS
│   ├── users.py               # FastAPI-Users config (auth, JWT, user manager)
│   ├── images.py              # ImageKit client for profile images
│   │
│   ├── api/                   # API Layer
│   │   ├── main.py            # Router aggregator (includes all routers)
│   │   ├── dependencies.py    # Shared dependencies (permission checks)
│   │   │
│   │   └── routers/           # 📡 API Endpoints
│   │       ├── users.py       # Auth endpoints (register, login, verify)
│   │       ├── users_list.py  # Admin: list/manage users
│   │       ├── profile.py     # Profile image upload/delete
│   │       ├── assets.py      # Asset CRUD + asset-attached monitors
│   │       ├── monitors.py    # Standalone monitors (UptimeRobot-style)
│   │       ├── dashboard.py   # Dashboard stats & charts
│   │       ├── observability.py # AG Grid observability data
│   │       ├── beacon.py      # Beacon AI chatbot endpoint
│   │       │
│   │       ├── models/        # 📋 Pydantic Request/Response Models
│   │       │   ├── users_models.py
│   │       │   ├── assets_models.py
│   │       │   ├── monitors_models.py
│   │       │   ├── dashboard_models.py
│   │       │   └── ...
│   │       │
│   │       └── services/      # 🔧 Business Logic Services
│   │           ├── monitor_services.py   # Monitor helper functions
│   │           ├── dashboard_services.py # Dashboard data aggregation
│   │           │
│   │           └── beacon/    # 🤖 Beacon AI Chatbot
│   │               ├── __init__.py       # Exports BeaconChatService
│   │               ├── chat_service.py   # Main orchestrator
│   │               ├── rag_service.py    # ChromaDB RAG retrieval
│   │               ├── context_builder.py # Builds user data context
│   │               ├── prompts.py        # System prompts
│   │               └── knowledge/        # 📚 Knowledge base docs
│   │                   └── assetwatch_docs.md
│   │
│   └── core/                  # 🏗️ Core Infrastructure
│       ├── config.py          # Pydantic Settings (env vars)
│       ├── db.py              # SQLAlchemy models & session
│       ├── security.py        # Password hashing utilities
│       ├── permit_service.py  # Permit.io RBAC integration
│       ├── email_service.py   # SendGrid email (verification, reset)
│       └── constants.py       # App constants
│
├── worker/                    # ⏰ BACKGROUND WORKER (separate process)
│   ├── __init__.py
│   ├── main.py                # Worker entry point
│   ├── scheduler.py           # APScheduler config (10s interval)
│   ├── engine.py              # Orchestrates checks, updates DB
│   │
│   └── checkers/              # 🔍 Protocol-specific Checkers
│       ├── __init__.py        # Checker registry & run_check()
│       ├── base.py            # CheckResult dataclass, BaseChecker ABC
│       ├── http.py            # HTTP/HTTPS checker
│       ├── ping.py            # ICMP ping checker
│       ├── port.py            # TCP port checker
│       └── dns.py             # DNS record checker
│
├── data/                      # 📦 Local Data Storage
│   └── chromadb/              # Vector store for RAG (gitignored)
│
└── scripts/                   # 🛠️ Utility Scripts
    ├── setup_initial_org.py   # Create initial organization
    └── debug_permit_check.py  # Debug Permit.io permissions
```

**Files to Ignore**: `Basics/`, `Notes.text`, `Prompts.text`, `test.db`, `data/chromadb/`, `__pycache__/`

---

## Core Components Deep Dive

### 1. FastAPI Application (`app/app.py`)

The main FastAPI app with:
- **Lifespan**: Creates DB tables on startup
- **CORS**: Configured via `settings.all_cors_origins`
- **API Routes**: Mounted at `/api` prefix
- **Docs**: Available at `/api/docs` (Swagger UI)

```python
# Key initialization
app = FastAPI(lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(api_router, prefix=settings.API_BASE)  # /api
```

### 2. Database Models (`app/core/db.py`)

SQLAlchemy async models with key entities:

| Model | Description |
|-------|-------------|
| `User` | FastAPI-Users base + org fields (User IS the Organization) |
| `Organization` | Multi-tenant org model (legacy, kept for reference) |
| `Asset` | Network/compute/security assets to monitor |
| `Monitor` | Attached to assets (performance/availability) |
| `StandaloneMonitor` | Independent monitors (UptimeRobot-style) |
| `StandaloneMonitorMetric` | Check results with timestamps |
| `MonitorIncident` | Down/up incidents for tracking |
| `MonitorTag` | Tags for organizing monitors |
| `FilePost` | File uploads linked to users |

**Organization Types** (multi-tenant RBAC):
- `assetwatch` - Super admin (CRUD all)
- `reseller` - Partner (manage own customers)
- `customer` - Direct customer (read/update self)
- `reseller_customer` - Reseller's customer

### 3. Authentication (`app/users.py`)

Uses **fastapi-users** with JWT bearer tokens:

```python
# Key components
- UserManager: Handles registration, password reset, verification
- auth_backend: JWT strategy with bearer transport
- current_active_user: Dependency for protected routes
```

**Lifecycle hooks**:
- `on_after_register`: Syncs user/org to Permit.io, sends verification email
- `on_after_forgot_password`: Sends reset email via SendGrid
- `on_after_request_verify`: Sends verification email

### 4. API Routers

| Router | Prefix | Purpose |
|--------|--------|---------|
| `users.py` | `/auth` | Register, login, verify, reset password |
| `users_list.py` | `/users` | Admin list/manage users |
| `profile.py` | `/profile` | Profile image upload/delete |
| `assets.py` | `/assets` | Asset CRUD + asset-attached monitors |
| `monitors.py` | `/monitors` | Standalone monitors (HTTP, Ping, Port, DNS) |
| `dashboard.py` | `/dashboard` | Dashboard stats, trends, warnings |
| `observability.py` | `/observability` | AG Grid data for observability tab |
| `beacon.py` | `/beacon` | AI chatbot endpoint |

### 5. Standalone Monitors (`app/api/routers/monitors.py`)

UptimeRobot-style monitoring with:

**Monitor Types**:
- `http` - HTTP/HTTPS website/API checks
- `ping` - ICMP ping checks
- `port` - TCP port checks
- `dns` - DNS record checks

**Check Intervals**: 30s, 1m, 5m, 15m, 30m, 1hr, 12hr

**Status Flow**: `unknown` → `up`/`down` (requires 3 consecutive failures for down)

### 6. Background Worker (`worker/`)

Separate process that runs monitoring checks:

```
worker/main.py          # Entry: python -m worker.main
    ↓
worker/scheduler.py     # APScheduler (10s interval)
    ↓
worker/engine.py        # check_due_monitors() → get monitors due → run checks → update DB
    ↓
worker/checkers/        # Protocol-specific: HTTP, Ping, Port, DNS
```

**Key flow**:
1. Scheduler triggers `check_due_monitors()` every 10 seconds
2. Engine queries monitors where `next_check_at <= now`
3. Runs checks concurrently (max 50 parallel)
4. Updates status, metrics, incidents in DB

### 7. Beacon AI Chatbot (`app/api/routers/services/beacon/`)

RAG-powered assistant using Gemini:

```
User Message
    ↓
chat_service.py (orchestrator)
    ↓
┌─────────────────────────────┐
│  1. Classify query          │  → documentation / user_data / both / out_of_scope
│  2. Get RAG context         │  → ChromaDB semantic search
│  3. Get user data context   │  → DB queries (assets, monitors, metrics)
│  4. Generate response       │  → Gemini with combined context
└─────────────────────────────┘
    ↓
Response
```

**Components**:
- `chat_service.py` - Main orchestrator
- `rag_service.py` - ChromaDB vector store + embeddings
- `context_builder.py` - Builds context from user's data
- `prompts.py` - System and classification prompts
- `knowledge/` - Markdown docs indexed for RAG

### 8. Authorization (`app/core/permit_service.py`)

Permit.io integration for RBAC:

```python
# Key functions
sync_user_to_permit()         # Create user + assign role in tenant
sync_organization_to_permit() # Create tenant (org)
check_permission()            # permit.check(user, action, resource, tenant)
```

**Permission Model**:
- Users belong to tenants (organizations)
- Roles: assetwatch, reseller, customer, reseller_customer
- Resources: organization, asset, monitor
- Actions: create, read, update, delete

---

## API Endpoints Summary

### Auth (`/api/auth`)
```
POST /register              # Create account
POST /login                 # Get JWT token
POST /forgot-password       # Request reset email
POST /reset-password        # Reset with token
POST /request-verify-token  # Request verification email
POST /verify                # Verify email with token
```

### Monitors (`/api/monitors`)
```
GET    /stats               # Up/down/paused counts
GET    /tags                # All unique tags
GET    /                    # List with pagination, filters
POST   /http                # Create HTTP monitor
POST   /ping                # Create Ping monitor
POST   /port                # Create Port monitor
POST   /dns                 # Create DNS monitor
GET    /{id}                # Monitor details + metrics
PUT    /{id}                # Update monitor
DELETE /{id}                # Delete monitor
POST   /{id}/toggle         # Pause/resume monitor
```

### Dashboard (`/api/dashboard`)
```
GET    /                    # Full dashboard data
GET    /overview            # Stats only
GET    /activity            # Recent activity
GET    /trend               # Response time trend
GET    /uptime-by-type      # Uptime by monitor type
GET    /warnings            # Active warnings
```

### Assets (`/api/assets`)
```
POST   /                    # Create asset
GET    /                    # List assets
GET    /{id}                # Asset with monitors
PUT    /{id}                # Update asset
DELETE /{id}                # Delete asset (cascades)
POST   /{id}/monitors/...   # Add monitor to asset
GET    /{id}/monitors       # List monitors for asset
```

### Beacon (`/api/beacon`)
```
POST   /chat                # Chat with Beacon AI
```

---

## Environment Variables

```env
# Required
PROJECT_NAME=AssetWatch
SECRET_KEY=your-secret-key
FRONTEND_HOST=http://localhost:5173
BACKEND_CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Database (PostgreSQL for production)
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=assetwatch

# Permit.io (RBAC)
PERMIT_IO_KEY=your-permit-api-key

# SendGrid (Email)
SENDGRID_API_KEY=your-sendgrid-key
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME=AssetWatch

# Gemini (Beacon AI)
GEMINI_API_KEY=your-gemini-api-key

# ImageKit (Profile images)
IMAGEKIT_PUBLIC_KEY=...
IMAGEKIT_PRIVATE_KEY=...
IMAGEKIT_URL_ENDPOINT=...
```

---

## Running the Application

### Development

```bash
# Terminal 1: FastAPI server
uv run uvicorn app.app:app --reload --port 5000

# Terminal 2: Background worker (optional, for monitoring)
uv run python -m worker.main
```

### Production (Render)

**Build Command**:
```bash
uv sync --frozen && uv cache prune --ci
```

**Start Command**:
```bash
uv run uvicorn app.app:app --host 0.0.0.0 --port $PORT
```

**Note**: Worker needs to run separately (Render Background Worker or separate service)

---

## Key Design Patterns

1. **Dependency Injection**: FastAPI `Depends()` for DB sessions, auth, permissions
2. **Service Layer**: Business logic in `services/` separate from routes
3. **Async Throughout**: All DB operations are async (SQLAlchemy AsyncSession)
4. **Pydantic Models**: Request/response validation in `models/`
5. **Singleton RAGService**: Single ChromaDB instance for efficiency
6. **Strategy Pattern**: Checkers implement `BaseChecker` interface

---

## Common Tasks

### Add a New API Endpoint

1. Create/update router in `app/api/routers/`
2. Add Pydantic models in `models/`
3. Add business logic in `services/` if complex
4. Include router in `app/api/main.py`

### Add a New Monitor Type

1. Create checker in `worker/checkers/` (extend `BaseChecker`)
2. Register in `worker/checkers/__init__.py` CHECKERS dict
3. Add create endpoint in `app/api/routers/monitors.py`
4. Add Pydantic models in `monitors_models.py`

### Add Knowledge to Beacon

1. Add/update markdown files in `app/api/routers/services/beacon/knowledge/`
2. Delete `data/chromadb/` to force re-indexing
3. Restart the server

---

## Database Migrations

Currently using auto-create on startup (`create_db_and_tables()`). For production, consider Alembic migrations.

---

*Last updated: 2026-07-02*
