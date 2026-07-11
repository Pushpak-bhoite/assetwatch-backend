# 🚀 AssetWatch - Real-Time Monitoring Platform

> A powerful, intelligent website monitoring platform with real-time alerts, AI-powered analytics, and comprehensive uptime tracking. Monitor your infrastructure like UptimeRobot, with advanced features.

**[🌐 Live Demo](https://assetwatch-frontend.bhoitepushpak6.workers.dev)** | **[Frontend Repo](https://github.com/Pushpak-bhoite/assetwatch-frontend)**

---

## ✨ Core Features

- 🔍 **4 Monitor Types**
  - HTTP/HTTPS Monitoring - Track website uptime & response times
  - DNS Monitoring - Monitor domain resolution
  - TCP/Port Monitoring - Verify service availability
  - SSL Certificate Monitoring - Track certificate expiration

- 📊 **Real-Time Dashboard** - Live status visualization with performance metrics
- 📈 **Advanced Analytics** - Detailed uptime reports, response time trends, and insights
- 🤖 **AI Assistant (Beacon)** - RAG-powered intelligent recommendations & anomaly detection
- 👥 **4 User Roles** - Admin, Operator, Viewer, and Restricted access levels
- 🔔 **Real-Time Alerts** - Instant notifications for downtime & status changes
- 📝 **Batch Operations** - Manage multiple monitors efficiently
- 🔐 **OAuth2 Authentication** - Secure, industry-standard auth via FastAPI's built-in system
- 📱 **Responsive UI** - Works seamlessly on desktop and mobile
- ⚡ **High Performance** - Optimized for reliability and speed

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.10+) - High-performance async framework
- **Database**: SQLite (currently) → PostgreSQL (planned migration)
- **Package Manager**: `uv` - Lightning-fast Python package management
- **Authentication**: OAuth2 with FastAPI's built-in security
- **AI/ML**: RAG (Retrieval-Augmented Generation) for Beacon AI
- **Real-Time**: WebSockets for live monitor updates
- **API Documentation**: Auto-generated OpenAPI/Swagger UI
- **Testing**: Pytest

### Frontend
- **React.js** - Modern UI library with hooks
- **TypeScript** - Type-safe development
- **Vite** - Next-generation build tool
- **ShadcnUI** - High-quality React components
- **TailwindCSS** - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
- **TanStack Router** - Modern React routing
- **Recharts** - Data visualization

### DevOps
- **Cloudflare Workers** - Edge computing deployment
- **Docker** - Container orchestration
- **Git** - Version control

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js (v16+)
- `uv` package manager

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/Pushpak-bhoite/assetwatch-backend.git
cd assetwatch-backend

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies with uv
uv pip install -r requirements.txt

# Set up environment variables
cat > .env << EOF
DATABASE_URL=sqlite:///./assetwatch.db
# FUTURE: DATABASE_URL=postgresql://user:password@localhost/assetwatch
SECRET_KEY=your_super_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
PORT=8000
BEACON_API_KEY=your_api_key
EOF

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API available at `http://localhost:8000`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Frontend Setup

```bash
# Clone the repository
git clone https://github.com/Pushpak-bhoite/assetwatch-frontend.git
cd assetwatch-frontend

# Install dependencies
pnpm install

# Set environment variables
echo "VITE_API_URL=http://localhost:8000" > .env.local
echo "VITE_WS_URL=ws://localhost:8000" >> .env.local

# Start development server
pnpm run dev
```

App available at `http://localhost:5173`

---

## 📊 Monitor Types Explained

### 1. **HTTP/HTTPS Monitoring**
- Monitor website uptime and response times
- Track status code changes (2xx, 3xx, 4xx, 5xx)
- Performance metrics: latency, throughput
- Custom headers and request body support

### 2. **DNS Monitoring**
- Verify domain name resolution
- Monitor DNS response times
- Track DNS record changes
- Multi-region DNS checking

### 3. **TCP/Port Monitoring**
- Monitor service availability on specific ports
- Connection timeout detection
- Service health verification
- Support for custom protocols

### 4. **SSL Certificate Monitoring**
- Track SSL/TLS certificate expiration
- Certificate validity verification
- Early warning system for renewals
- Chain validation and trust analysis

---

## 👥 User Roles & Permissions

| Role | Create Monitors | Edit All | View Reports | Manage Users | Alerts |
|------|-----------------|----------|-------------|--------------|--------|
| **Admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Operator** | ✅ | Own only | ✅ | ❌ | ✅ |
| **Viewer** | ❌ | ❌ | ✅ | ❌ | View only |
| **Restricted** | ❌ | ❌ | Limited | ❌ | Specific |

---

## 🤖 Beacon AI Assistant

RAG-powered intelligent assistant providing:
- **Anomaly Detection** - Identify unusual uptime patterns
- **Root Cause Analysis** - Suggest why services went down
- **Performance Insights** - Recommendations to improve uptime
- **Predictive Alerts** - Alert before predicted outages
- **Natural Language Queries** - Ask questions about your infrastructure

Example:
```
User: "Why did my website go down yesterday?"
Beacon: "Your site experienced 2 outages:
  - 14:32 UTC: DB connection timeout (2 min)
  - 15:45 UTC: High CPU usage spike (5 min)
  Recommendation: Add connection pooling & auto-scaling"
```

---

## 🔌 API Endpoints

### Authentication (OAuth2)

```
POST   /api/auth/token              - Get access token
POST   /api/auth/refresh            - Refresh token
GET    /api/auth/me                 - Current user info
```

### Monitors

```
GET    /api/monitors                - List all monitors
POST   /api/monitors                - Create new monitor
GET    /api/monitors/{id}           - Get monitor details
PUT    /api/monitors/{id}           - Update monitor
DELETE /api/monitors/{id}           - Delete monitor
POST   /api/monitors/batch          - Batch operations

GET    /api/monitors/{id}/status    - Get current status
GET    /api/monitors/{id}/history   - Uptime history
GET    /api/monitors/{id}/stats     - Analytics & stats
```

### Alerts

```
GET    /api/alerts                  - List alerts
POST   /api/alerts                  - Create alert rule
GET    /api/alerts/{id}             - Alert details
PUT    /api/alerts/{id}             - Update alert
DELETE /api/alerts/{id}             - Delete alert
```

### Analytics & AI

```
GET    /api/analytics/dashboard     - Dashboard metrics
GET    /api/analytics/reports       - Detailed reports
POST   /api/analytics/beacon        - Ask Beacon AI
GET    /api/analytics/trends        - Trend analysis
```

### Users (Admin)

```
GET    /api/users                   - List users
POST   /api/users                   - Create user
PUT    /api/users/{id}              - Update user
DELETE /api/users/{id}              - Delete user
PUT    /api/users/{id}/role         - Change user role
```

---

## 📁 Project Structure

```
assetwatch-backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── monitors.py         # Monitor endpoints
│   │   │   ├── auth.py             # OAuth2 auth
│   │   │   ├── alerts.py           # Alert rules
│   │   │   ├── users.py            # User management
│   │   │   └── analytics.py        # Analytics & Beacon AI
│   │   └── dependencies.py         # Dependency injection
│   ├── models/
│   │   ├── monitor.py              # Monitor schema
│   │   ├── user.py                 # User schema
│   │   ├── alert.py                # Alert schema
│   │   └── schemas.py              # Pydantic models
│   ├── core/
│   │   ├── config.py               # Configuration
│   │   ├── security.py             # OAuth2 & security
│   │   └── exceptions.py           # Custom exceptions
│   ├── db/
│   │   ├── session.py              # DB session
│   │   └── base.py                 # Base models
│   ├── services/
│   │   ├── monitor_service.py      # Monitor logic
│   │   ├── beacon_service.py       # RAG AI logic
│   │   └── alert_service.py        # Alert logic
│   └── ws/
│       └── websocket.py            # WebSocket handlers
├── tests/
│   ├── test_monitors.py
│   ├── test_auth.py
│   └── test_alerts.py
├── requirements.txt
├── main.py
└── README.md
```

---

## 🔐 OAuth2 Authentication

Secure authentication using FastAPI's built-in OAuth2 implementation:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=pass"

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}

# Use token in requests
curl http://localhost:8000/api/monitors \
  -H "Authorization: Bearer <access_token>"
```

---

## 🌐 Real-Time Updates via WebSocket

```python
# Connect to WebSocket
ws://localhost:8000/ws/monitors/{user_id}

# Receive events
{
  "type": "monitor_status_change",
  "monitor_id": "...",
  "status": "down",
  "response_time": 5000,
  "timestamp": "2024-01-15T10:30:00Z"
}

{
  "type": "alert_triggered",
  "monitor_id": "...",
  "message": "Website down for 2 minutes",
  "severity": "critical"
}
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_monitors.py -v

# Run specific test
pytest tests/test_monitors.py::test_create_monitor -v
```

---

## 🚢 Deployment

### Docker

```bash
# Build image
docker build -t assetwatch-backend .

# Run container
docker run -p 8000:8000 --env-file .env assetwatch-backend
```

### Environment Variables

```env
# Database (SQLite for now, PostgreSQL later)
DATABASE_URL=sqlite:///./assetwatch.db
# DATABASE_URL=postgresql://user:pass@localhost/assetwatch

# Security
SECRET_KEY=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=False
PORT=8000
CORS_ORIGINS=["https://assetwatch-frontend.bhoitepushpak6.workers.dev"]

# AI Services
BEACON_API_KEY=your_api_key
OPENAI_API_KEY=for_rag_embeddings

# Monitoring
MAX_MONITORS_PER_USER=100
CHECK_INTERVAL_SECONDS=60
```

---

## 🔧 Development

### Install with uv

```bash
# Install all dependencies
uv pip install -r requirements.txt

# Add new dependency
uv pip install package_name
```

### Code Quality

```bash
# Format with Black
black app/

# Lint with Flake8
flake8 app/

# Type checking with Mypy
mypy app/
```

### Database Migrations (when on PostgreSQL)

```bash
# Install Alembic
uv pip install alembic

# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head
```

---

## 📈 Performance Optimization

- ✅ Async/await throughout for concurrent monitor checks
- ✅ Connection pooling for database
- ✅ Caching with Redis (future)
- ✅ Background tasks with Celery (future)
- ✅ Batch database operations
- ✅ Lazy loading and pagination

---

## 🐛 Troubleshooting

### Database Issues
```bash
# Check SQLite database
sqlite3 assetwatch.db ".tables"

# Future: PostgreSQL connection
psql -h localhost -U user -d assetwatch
```

### OAuth2 Token Errors
- Verify SECRET_KEY is set
- Check token expiration (default: 30 min)
- Ensure `Authorization: Bearer <token>` format

### Monitor Check Failures
- Verify internet connectivity
- Check firewall rules for outbound connections
- Review monitor configuration in dashboard

---

## 🤝 Contributing

Contributions welcome! Process:

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new features
4. Run all tests: `pytest`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 👨‍💻 Author

**Pushpak Bhoite**
- GitHub: [@Pushpak-bhoite](https://github.com/Pushpak-bhoite)
- Email: bhoitepushpak6@gmail.com

---

## 📞 Support & Feedback

- 🐛 Found a bug? Open an issue
- 💡 Have ideas? Start a discussion
- 📧 Questions? Email me

⭐ If you like this project, please star the repository!

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com) - Modern async web framework
- [SQLite](https://www.sqlite.org) / [PostgreSQL](https://www.postgresql.org) - Databases
- [UptimeRobot](https://uptimerobot.com) - Inspiration
- [Pydantic](https://pydantic-docs.helpmanual.io) - Data validation
