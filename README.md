# 🚀 AssetWatch Backend - REST API Server

> A high-performance backend API for the AssetWatch asset management system, built with FastAPI and Python. Handles real-time data streaming, AI-powered analytics, and robust asset management.

**[Frontend Repo](https://github.com/Pushpak-bhoite/assetwatch-frontend)**

---

## ✨ Features

- ⚡ **High Performance** - Built with FastAPI for async request handling
- 🔐 **Secure Authentication** - JWT token-based authorization
- 📊 **Real-Time Data** - WebSocket support for live updates
- 🤖 **AI Integration** - Beacon AI assistant for insights
- 📈 **Asset Management** - Complete CRUD operations for assets
- 🔔 **Alert System** - Real-time price change notifications
- 📝 **Batch Operations** - Efficient bulk asset processing
- 📚 **API Documentation** - Auto-generated Swagger UI
- 🗄️ **MongoDB** - Flexible data storage
- 🧪 **Testing** - Comprehensive test coverage

---

## 🛠️ Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **Database**: MongoDB
- **Authentication**: JWT (PyJWT)
- **Password Hashing**: Bcrypt
- **ORM**: Motor (async MongoDB driver)
- **API Documentation**: Swagger UI / OpenAPI
- **WebSockets**: FastAPI WebSockets
- **Task Queue**: Celery (optional)
- **Testing**: Pytest

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- MongoDB 4.0+
- pip or conda

### Installation

```bash
# Clone the repository
git clone https://github.com/Pushpak-bhoite/assetwatch-backend.git

# Navigate to project directory
cd assetwatch-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
MONGODB_URI=mongodb://localhost:27017/assetwatch
JWT_SECRET=your_super_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
PORT=8000
EOF

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📁 Project Structure

```
assetwatch-backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── assets.py        # Asset endpoints
│   │   │   ├── auth.py          # Authentication endpoints
│   │   │   ├── users.py         # User management
│   │   │   └── analytics.py     # Analytics & AI
│   │   └── dependencies.py       # Dependency injection
│   ├── models/
│   │   ├── asset.py             # Asset schema
│   │   ├── user.py              # User schema
│   │   └── schemas.py           # Pydantic models
│   ├── core/
│   │   ├── config.py            # Configuration
│   │   ├── security.py          # JWT & Auth
│   │   └── exceptions.py        # Custom exceptions
│   ├── db/
│   │   ├── mongodb.py           # DB connection
│   │   └── models.py            # DB models
│   └── ws/
│       └── websocket.py         # WebSocket handlers
├── tests/
│   ├── test_api.py
│   ├── test_auth.py
│   └── test_assets.py
├── requirements.txt
├── main.py
└── README.md
```

---

## 🔌 API Endpoints

### Authentication

```
POST   /api/auth/register          - Register new user
POST   /api/auth/login             - Login with credentials
POST   /api/auth/refresh           - Refresh access token
POST   /api/auth/logout            - Logout user
GET    /api/auth/me                - Get current user profile
```

### Assets

```
GET    /api/assets                 - List all assets
POST   /api/assets                 - Create new asset
GET    /api/assets/{id}            - Get asset details
PUT    /api/assets/{id}            - Update asset
DELETE /api/assets/{id}            - Delete asset
POST   /api/assets/batch           - Batch create/update assets
```

### Users

```
GET    /api/users                  - List all users (admin only)
GET    /api/users/{id}             - Get user details
PUT    /api/users/{id}             - Update user profile
DELETE /api/users/{id}             - Delete user (admin)
```

### Analytics & AI

```
GET    /api/analytics/portfolio    - Portfolio analysis
GET    /api/analytics/trends       - Market trends
POST   /api/analytics/beacon       - Get AI insights
GET    /api/analytics/alerts       - Get price alerts
```

---

## 📊 Data Models

### User Schema

```python
{
  "id": "ObjectId",
  "username": "string",
  "email": "string",
  "password_hash": "string",
  "first_name": "string",
  "last_name": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "is_active": "boolean"
}
```

### Asset Schema

```python
{
  "id": "ObjectId",
  "user_id": "ObjectId",
  "name": "string",
  "symbol": "string",
  "quantity": "float",
  "purchase_price": "float",
  "current_price": "float",
  "category": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

---

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication:

```bash
# Get access token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}

# Use token in requests
curl http://localhost:8000/api/assets \
  -H "Authorization: Bearer <access_token>"
```

---

## 🌐 WebSocket Events

Real-time data streaming via WebSocket:

```python
# Connect to WebSocket
ws://localhost:8000/ws/stream/{user_id}

# Receive events
{
  "type": "price_update",
  "asset_id": "...",
  "price": 1234.56,
  "timestamp": "2024-01-15T10:30:00Z"
}

{
  "type": "alert",
  "asset_id": "...",
  "message": "Price increased by 5%",
  "timestamp": "2024-01-15T10:30:00Z"
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
pytest tests/test_api.py -v

# Run with markers
pytest -m "auth"
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
# Database
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/assetwatch

# Security
JWT_SECRET=your_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=False
PORT=8000
CORS_ORIGINS=["https://assetwatch-frontend.com"]

# External Services
AI_API_KEY=your_api_key
PRICE_API_KEY=your_api_key
```

---

## 🔧 Development

### Install development dependencies

```bash
pip install -r requirements-dev.txt
```

### Code formatting

```bash
# Format with Black
black app/

# Check with Flake8
flake8 app/

# Type checking with Mypy
mypy app/
```

### Run with auto-reload

```bash
uvicorn main:app --reload
```

---

## 📈 Performance Tips

- Database indexes on frequently queried fields
- Caching with Redis for expensive operations
- Async database operations with Motor
- Query optimization and pagination
- Lazy loading of related data

---

## 🐛 Troubleshooting

### MongoDB Connection Issues
```bash
# Check MongoDB is running
mongod --version

# Test connection
python -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017')"
```

### JWT Token Errors
- Verify JWT_SECRET is set correctly
- Check token expiration time
- Ensure Authorization header format: `Bearer <token>`

### CORS Errors
- Update CORS_ORIGINS in environment
- Check frontend URL matches configuration

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write tests for new features
5. Run tests to ensure everything passes
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch
8. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

## 👨‍💻 Author

**Pushpak Bhoite**
- GitHub: [@Pushpak-bhoite](https://github.com/Pushpak-bhoite)

---

## 📞 Support

Need help? 
- Check API documentation at `/docs`
- Open an issue on GitHub
- Review existing issues for solutions

---

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com) - Modern web framework
- [MongoDB](https://www.mongodb.com) - Document database
- [Pydantic](https://pydantic-docs.helpmanual.io) - Data validation

---

⭐ If you found this helpful, please star the repository!
