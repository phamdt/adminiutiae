# Hybrid Go/Python Microservices Architecture

A comprehensive implementation of a hybrid microservices architecture where **Go handles external API interactions and concurrent processing**, while **Python manages the REST API and simple database operations**. Complex data fetching is offloaded from Python to Go via direct HTTP communication.

## 🏗️ Architecture Overview

```
┌─────────────────┐    HTTP POST     ┌─────────────────┐
│   Python API    │ ──────────────► │   Go Worker     │
│   (FastAPI)     │                 │   (Gin + Jobs)  │
└─────────────────┘                 └─────────────────┘
         │                                   │
         │                                   │
         ▼                                   ▼
┌─────────────────┐    Optional      ┌─────────────────┐
│   PostgreSQL    │ ◄─────────────── │     Redis       │
│   (Job Status)  │    Pub/Sub       │  (Notifications)│
└─────────────────┘                  └─────────────────┘
```

## ✨ Key Features

### 🔄 **Celery-Free Design**
- **Direct HTTP Communication**: Python → Go via simple HTTP POST
- **No Message Broker Complexity**: Eliminates Celery overhead
- **Maximum Interoperability**: Native HTTP in both languages

### 🚀 **Service Responsibilities**
- **Python (FastAPI)**: REST API, authentication, simple database operations
- **Go (Gin)**: External API calls, concurrent processing, background jobs
- **Shared Database**: Single source of truth for job state

### 🐳 **Optimized Docker**
- **Multi-stage builds** for minimal image sizes
- **Layer caching** for fast rebuilds
- **Development & production** configurations

## 📦 Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Python API** | FastAPI | 0.115.0 |
| **Go Worker** | Gin | 1.10.0 |
| **Database** | PostgreSQL | 16+ |
| **Cache/PubSub** | Redis | 8.2+ |
| **Container** | Docker | 25.0+ |
| **Language** | Python | 3.13 |
| **Language** | Go | 1.22 |

## 🚀 Quick Start

### Prerequisites
```bash
# Required
docker >= 25.0
docker-compose >= 2.0
python >= 3.13
go >= 1.22

# Optional (for development)
alembic (for database migrations)
```

### 1. Clone and Setup
```bash
git clone <repository>
cd hybrid-microservices

# Copy environment configuration
cp .env.example .env
```

### 2. Start Development Environment
```bash
# One-command startup
./start_dev.sh

# Or manually with Docker Compose
cd docker-compose
docker-compose up --build
```

### 3. Verify Services
```bash
# Check Python API
curl http://localhost:8000/health

# Check Go Worker
curl http://localhost:8080/health

# View API documentation
open http://localhost:8000/docs
```

## 📊 Service Endpoints

### Python API (Port 8000)
```bash
# User Management
POST /api/v1/users/              # Create user
POST /api/v1/auth/login          # Login
GET  /api/v1/users/me            # Get current user

# Job Management  
POST /api/v1/users/{id}/external-data  # Create external data job
GET  /api/v1/jobs/{id}                  # Get job status
GET  /api/v1/users/{id}/jobs            # List user jobs
POST /api/v1/jobs/{id}/cancel           # Cancel job
GET  /api/v1/jobs/{id}/results          # Get job results

# System
GET  /health                     # Health check
GET  /docs                       # API documentation
```

### Go Worker (Port 8080)
```bash
# Job Processing (Internal)
POST /api/v1/jobs/process        # Process job (called by Python)
GET  /api/v1/jobs/{id}/status    # Get job status

# System
GET  /health                     # Health check
GET  /ready                      # Readiness check
```

## 💼 Example Usage

### 1. Create a User
```bash
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "username": "johndoe",
    "password": "securepassword123"
  }'
```

### 2. Login and Get Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "password": "securepassword123"
  }'
```

### 3. Create External Data Job
```bash
curl -X POST http://localhost:8000/api/v1/users/1/external-data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "data_sources": [
      "https://jsonplaceholder.typicode.com/posts/1",
      "https://jsonplaceholder.typicode.com/users/1"
    ],
    "filters": {
      "category": "example"
    }
  }'
```

### 4. Check Job Status
```bash
curl http://localhost:8000/api/v1/jobs/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔄 Job Processing Flow

1. **Client Request**: POST to Python API with external data request
2. **Job Creation**: Python creates job record in database (status: "queued")
3. **Go Delegation**: Python sends HTTP POST to Go service with job details
4. **Async Processing**: Go processes job in background goroutine
5. **External API Calls**: Go makes concurrent calls to external APIs
6. **Result Storage**: Go updates job in database with results (status: "completed")
7. **Client Polling**: Client checks job status via Python API

## 🏗️ Project Structure

```
├── python-service/           # FastAPI REST API
│   ├── app/
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Configuration
│   │   ├── db/              # Database connection
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Database migrations
│   ├── tests/               # Python tests
│   └── Dockerfile
├── go-service/              # Go worker service
│   ├── cmd/worker/          # Main application
│   ├── internal/
│   │   ├── config/          # Configuration
│   │   ├── handlers/        # HTTP handlers
│   │   ├── services/        # External API service
│   │   └── workers/         # Job processors
│   ├── pkg/
│   │   ├── database/        # Database client
│   │   ├── logger/          # Logging
│   │   └── redis/           # Redis client
│   └── Dockerfile
├── docker-compose/          # Container orchestration
│   ├── docker-compose.yml   # Development
│   ├── docker-compose.prod.yml
│   └── nginx.conf           # Load balancer
├── tests/                   # E2E tests
└── config/                  # Environment configs
```

## 🧪 Testing

### Run Tests
```bash
# Python tests
cd python-service
pytest tests/ -v

# Go tests  
cd go-service
go test ./tests/... -v

# Integration tests
./run_tests.sh integration

# All tests
./run_tests.sh all
```

### Test Coverage
```bash
# Python coverage
cd python-service
pytest --cov=app --cov-report=html

# Go coverage
cd go-service
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

## 🚀 Production Deployment

### 1. Production Environment
```bash
# Use production compose file
cp .env.example .env.prod
# Edit .env.prod with production values

cd docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Environment Variables
```bash
# Required for production
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_password  
SECRET_KEY=your-256-bit-secret-key
ENVIRONMENT=production
```

### 3. Scaling Services
```bash
# Scale Python API
docker-compose -f docker-compose.prod.yml up -d --scale python-api=3

# Scale Go workers
docker-compose -f docker-compose.prod.yml up -d --scale go-worker=5
```

## 📊 Monitoring

### Health Checks
```bash
# Service health
curl http://localhost:8000/health
curl http://localhost:8080/health

# Load balancer health (production)
curl http://localhost/nginx-health
```

### Logs
```bash
# View all logs
docker-compose -f docker-compose/docker-compose.yml logs -f

# Specific service logs
docker-compose -f docker-compose/docker-compose.yml logs -f python-api
docker-compose -f docker-compose/docker-compose.yml logs -f go-worker
```

### Metrics (Production)
- **Prometheus metrics** exposed on both services
- **Database connection pools** monitored
- **Job processing metrics** tracked
- **External API call success rates** measured

## 🔧 Development

### Local Development
```bash
# Python service (with hot reload)
cd python-service
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Go service (with auto-restart)
cd go-service  
go run cmd/worker/main.go

# Database migrations
cd python-service
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Adding New Endpoints

**Python (REST API):**
1. Add schema in `python-service/app/schemas/`
2. Add endpoint in `python-service/app/api/endpoints.py`
3. Add business logic in `python-service/app/services/`

**Go (Background Jobs):**
1. Add job type in `go-service/internal/models/job.go`
2. Add processor in `go-service/internal/workers/`
3. Add handler in `go-service/internal/handlers/`

## 🐛 Troubleshooting

### Common Issues

**Database Connection Errors:**
```bash
# Check database is running
docker ps | grep postgres

# Check connection
psql "postgresql://postgres:postgres@localhost:5432/appdb" -c "SELECT 1;"
```

**Service Communication Errors:**
```bash
# Check service URLs in docker-compose
# Ensure GO_SERVICE_URL points to correct container name
GO_SERVICE_URL=http://go-worker:8080  # Not localhost!
```

**Job Processing Failures:**
```bash
# Check Go worker logs
docker-compose logs -f go-worker

# Check external API connectivity
curl -v https://jsonplaceholder.typicode.com/posts/1
```

### Performance Tuning

**Database:**
- Adjust connection pool sizes in `database.py` and `postgres.go`
- Add indexes for frequently queried columns
- Monitor slow queries

**Go Service:**
- Adjust HTTP timeout and retry settings
- Monitor goroutine count
- Use connection pooling for external APIs

**Python Service:**
- Use async/await for I/O operations
- Implement response caching where appropriate
- Monitor memory usage

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Gin Web Framework](https://gin-gonic.com/)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)
- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes
4. Ensure all tests pass (`./run_tests.sh all`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using Go 1.22 and Python 3.13**