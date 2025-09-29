# Hybrid Go/Python Microservices Architecture - Technical Specification

## Overview

This specification outlines a microservices architecture where:
- **Go services** handle all external API interactions, concurrency, and heavy processing
- **Python services** provide REST APIs and handle simple database operations
- **Python APIs** can delegate complex data fetching to Go background jobs via message queues

## Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Load Balancer │    │   API Gateway   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         │                                               │
         ▼                                               ▼
┌─────────────────┐                            ┌─────────────────┐
│  Python REST    │◄──────── Message ────────►│   Go Worker     │
│     API         │           Queue            │    Service      │
│  (FastAPI)      │                            │                 │
└─────────────────┘                            └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐                            ┌─────────────────┐
│   PostgreSQL    │                            │  External APIs  │
│   Database      │                            │  (3rd Party)    │
└─────────────────┘                            └─────────────────┘
```

## Service Responsibilities

### Python REST API Service
- **Primary Role**: HTTP API endpoints, request validation, simple CRUD operations
- **Database Operations**: Direct database queries for simple operations (single table queries, basic joins)
- **Job Delegation**: Delegate complex data fetching tasks to Go services via HTTP
- **Response Handling**: Aggregate results from database and Go services

### Go Worker Service
- **Primary Role**: External API interactions, concurrent processing, background jobs
- **External APIs**: All third-party API calls (REST, GraphQL, gRPC)
- **Concurrency**: Parallel processing, goroutines, worker pools
- **Job Processing**: Receive HTTP job requests, process asynchronously
- **Data Processing**: Heavy computational tasks, data transformation

## Celery-Free Job Architecture

### Direct HTTP Communication
We eliminate Celery entirely and use direct HTTP communication:

**Python Side:**
- Receives HTTP requests from clients
- Creates job records in PostgreSQL
- Sends HTTP POST to Go service (fire-and-forget)
- Provides job status endpoints

**Go Side:**
- Receives job requests via HTTP
- Processes jobs asynchronously with goroutines
- Updates job status directly in PostgreSQL
- Handles all external API interactions

**Benefits:**
- **Maximum Interoperability**: Simple HTTP between Go and Python
- **Minimal Dependencies**: No message brokers or complex queues
- **Easy Testing**: Services can be tested independently
- **Operational Simplicity**: Only 2 services to manage
- **Natural Scaling**: Scale Python API and Go workers independently

## Technology Stack

### Python Service Stack
- **Framework**: FastAPI (async/await support)
- **Database ORM**: SQLAlchemy with asyncpg driver
- **Cache/PubSub Client**: Redis client (redis-py, optional)
- **Validation**: Pydantic models
- **HTTP Client**: httpx (for Go service communication)
- **Monitoring**: Prometheus client, structlog

### Go Service Stack
- **Framework**: Gin (HTTP server for job processing)
- **Database Driver**: pgx (PostgreSQL driver)
- **Cache/PubSub**: go-redis for Redis (optional notifications)
- **HTTP Client**: net/http with custom retry logic
- **Concurrency**: Goroutines, worker pools, context cancellation
- **Monitoring**: Prometheus metrics, zerolog

### Infrastructure
- **Database**: PostgreSQL 16+
- **Cache/PubSub**: Redis 8.2+ (optional for notifications)
- **Container Platform**: Docker 25.0+
- **Container Orchestration**: Docker Compose (dev), Kubernetes (prod)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Centralized logging with ELK stack

## Dependencies and Versions

### Python Dependencies (`requirements.txt`)
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.35
asyncpg==0.30.0
alembic==1.13.3
pydantic==2.9.2
redis==6.2.0
httpx==0.27.2
prometheus-client==0.21.0
structlog==24.4.0
python-multipart==0.0.12
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pytest==8.3.3
pytest-asyncio==0.24.0
```

### Go Dependencies (`go.mod`)
```go
module github.com/company/go-worker

go 1.22

require (
    github.com/gin-gonic/gin v1.10.0
    github.com/jackc/pgx/v5 v5.7.1
    github.com/redis/go-redis/v9 v9.7.0
    github.com/prometheus/client_golang v1.20.4
    github.com/rs/zerolog v1.33.0
    github.com/spf13/viper v1.19.0
    github.com/stretchr/testify v1.9.0
    golang.org/x/sync v0.8.0
    golang.org/x/time v0.6.0
)
```

## Docker Configuration

### Python Service Dockerfile
```dockerfile
# Multi-stage build for Python service
FROM python:3.13-slim as python-base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies (separate layer for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM python-base as development
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM python-base as production
COPY . .
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Go Service Dockerfile
```dockerfile
# Multi-stage build for Go service
FROM golang:1.22-alpine AS builder

# Install git and ca-certificates
RUN apk add --no-cache git ca-certificates

# Set working directory
WORKDIR /app

# Copy go mod files (separate layer for dependency caching)
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o main ./cmd/worker

# Production stage
FROM alpine:3.18 as production

# Install ca-certificates for HTTPS requests
RUN apk --no-cache add ca-certificates

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/main .

# Create non-root user
RUN addgroup -S app && adduser -S app -G app
USER app

CMD ["./main"]
```

### Docker Compose Configuration
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:8.2-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  python-api:
    build:
      context: ./python-service
      target: development
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/appdb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./python-service:/app

  go-worker:
    build:
      context: ./go-service
      target: production
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/appdb
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./go-service:/app

volumes:
  postgres_data:
```

## Implementation Steps for Junior Engineer

### Phase 1: Project Setup (Days 1-2)

#### Step 1.1: Initialize Project Structure
```bash
mkdir hybrid-microservices
cd hybrid-microservices

# Create service directories
mkdir python-service go-service

# Create shared configuration
mkdir config docker-compose
```

#### Step 1.2: Python Service Setup
```bash
cd python-service

# Create Python project structure
mkdir -p app/{api,core,db,models,schemas,services}
touch app/__init__.py
touch app/main.py
touch app/api/__init__.py
touch app/api/endpoints.py
touch app/core/__init__.py
touch app/core/config.py
touch app/db/__init__.py
touch app/db/database.py
touch app/models/__init__.py
touch app/models/user.py
touch app/schemas/__init__.py
touch app/schemas/user.py
touch app/services/__init__.py
touch app/services/job_service.py

# Create requirements.txt (copy from dependencies section above)
# Create Dockerfile (copy from Docker section above)
```

#### Step 1.3: Go Service Setup
```bash
cd ../go-service

# Initialize Go module
go mod init github.com/company/go-worker

# Create Go project structure
mkdir -p cmd/worker
mkdir -p internal/{config,handlers,services,workers}
mkdir -p pkg/{database,redis,logger}

# Create main files
touch cmd/worker/main.go
touch internal/config/config.go
touch internal/handlers/health.go
touch internal/services/external_api.go
touch internal/workers/job_processor.go
touch pkg/database/postgres.go
touch pkg/redis/client.go
touch pkg/logger/logger.go

# Create go.mod dependencies (copy from dependencies section above)
```

### Phase 2: Core Infrastructure (Days 3-5)

#### Step 2.1: Database Setup
1. **Create database models** in Python using SQLAlchemy
2. **Set up Alembic** for database migrations
3. **Configure connection pooling** for both Python and Go services
4. **Create initial migration** for user and job tables

#### Step 2.2: HTTP Job Communication Setup
1. **Configure HTTP client** in Python service
2. **Set up job delegation** via HTTP POST to Go service
3. **Implement job processing handlers** in Go service
4. **Create job request/response schemas**

#### Step 2.3: Basic Service Communication
1. **Implement health check endpoints** in both services
2. **Create HTTP job delegation** in Python
3. **Implement job processing** in Go
4. **Add error handling and retries**

### Phase 3: API Development (Days 6-10)

#### Step 3.1: Python REST API
```python
# Example endpoint structure
@router.post("/users/{user_id}/external-data")
async def fetch_external_data(
    user_id: int,
    request: ExternalDataRequest,
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    # Simple database check
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Create job record in database
    job = Job(
        user_id=user_id,
        job_type="external_data",
        status="queued",
        parameters=json.dumps(request.dict())
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Queue job to Redis stream
    job_data = {
        "job_id": job.id,
        "user_id": user_id,
        "job_type": "external_data",
        "parameters": request.dict()
    }
    
    await redis_client.xadd("job_queue", job_data)
    
    return {"job_id": job.id, "status": "queued"}
```

#### Step 3.2: Go Background Workers
```go
// Example Redis stream consumer
func (w *Worker) StartJobConsumer(ctx context.Context) error {
    for {
        // Read from Redis stream
        streams, err := w.redisClient.XRead(ctx, &redis.XReadArgs{
            Streams: []string{"job_queue", "$"},
            Block:   time.Second,
        }).Result()
        
        if err != nil {
            continue
        }
        
        for _, stream := range streams {
            for _, message := range stream.Messages {
                // Process job in goroutine
                go w.processJob(ctx, message)
            }
        }
    }
}

func (w *Worker) processJob(ctx context.Context, msg redis.XMessage) {
    jobData := msg.Values
    
    // Update job status to processing
    jobID := jobData["job_id"].(string)
    w.updateJobStatus(ctx, jobID, "processing")
    
    // Concurrent external API calls
    var wg sync.WaitGroup
    results := make(chan APIResult, 3)
    
    apis := []string{"api1", "api2", "api3"}
    for _, api := range apis {
        wg.Add(1)
        go func(apiURL string) {
            defer wg.Done()
            result := w.callExternalAPI(ctx, apiURL)
            results <- result
        }(api)
    }
    
    // Collect results
    go func() {
        wg.Wait()
        close(results)
    }()
    
    // Aggregate and store results
    w.aggregateAndStore(ctx, jobID, results)
    
    // Acknowledge message
    w.redisClient.XAck(ctx, "job_queue", "workers", msg.ID)
}
```

### Phase 4: Testing and Monitoring (Days 11-12)

#### Step 4.1: Testing Setup
1. **Unit tests** for both services
2. **Integration tests** for service communication
3. **Load testing** for concurrent processing
4. **API contract testing**

#### Step 4.2: Monitoring and Logging
1. **Prometheus metrics** in both services
2. **Structured logging** with correlation IDs
3. **Health check endpoints**
4. **Performance monitoring**

## Docker Cache Optimization Strategies

### 1. Layer Ordering
- **Dependencies first**: Copy dependency files before source code
- **Least changing layers first**: System packages → dependencies → source code
- **Multi-stage builds**: Separate build and runtime environments

### 2. Python Optimization
```dockerfile
# Good: Dependencies cached separately
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Bad: Dependencies reinstalled on every code change
COPY . .
RUN pip install -r requirements.txt
```

### 3. Go Optimization
```dockerfile
# Good: Go modules cached separately
COPY go.mod go.sum ./
RUN go mod download
COPY . .

# Bad: Dependencies downloaded on every build
COPY . .
RUN go mod download
```

### 4. Build Context Optimization
Create `.dockerignore` files:
```
# Python service .dockerignore
__pycache__/
*.pyc
.pytest_cache/
.coverage
.git/

# Go service .dockerignore
*.exe
*.exe~
*.dll
*.so
*.dylib
.git/
```

## Deployment Considerations

### Development Environment
- Use `docker-compose` for local development
- Mount source code as volumes for hot reloading
- Use development Docker targets

### Production Environment
- Use multi-stage builds for smaller images
- Implement proper health checks
- Configure resource limits and requests
- Use secrets management for sensitive data
- Implement graceful shutdown handling

## Security Best Practices

1. **Container Security**
   - Run as non-root user
   - Use minimal base images (Alpine)
   - Scan images for vulnerabilities

2. **Network Security**
   - Use internal networks for service communication
   - Implement proper authentication/authorization
   - Use TLS for external communications

3. **Data Security**
   - Encrypt sensitive data at rest
   - Use connection pooling with proper timeouts
   - Implement rate limiting

## Performance Optimization

1. **Go Service**
   - Use worker pools for concurrent processing
   - Implement circuit breakers for external APIs
   - Use connection pooling for database access

2. **Python Service**
   - Use async/await for I/O operations
   - Implement response caching where appropriate
   - Use database connection pooling

3. **Infrastructure**
   - Configure proper resource limits
   - Use horizontal pod autoscaling
   - Implement database indexing strategy

## Monitoring and Alerting

### Key Metrics to Monitor
- API response times and error rates
- Job queue length and processing times
- Database connection pool utilization
- External API call success rates
- Resource utilization (CPU, memory)

### Alerting Thresholds
- API error rate > 5%
- Job queue length > 1000
- Database connection pool > 80%
- Response time > 2 seconds
- Memory usage > 85%

This specification provides a comprehensive foundation for implementing the hybrid Go/Python microservices architecture while maintaining clear separation of concerns and optimal performance characteristics.