# Implementation Guide for Junior Engineer

## Quick Start Checklist

Before you begin, ensure you have:
- [ ] Docker 25.0+ and Docker Compose installed
- [ ] Go 1.22+ installed
- [ ] Python 3.13+ installed
- [ ] Git configured
- [ ] IDE/Editor with Go and Python support

## Day-by-Day Implementation Schedule

### Day 1: Project Foundation

#### Morning (4 hours): Project Structure Setup

**Step 1.1: Create Project Structure**
```bash
# Create main project directory
mkdir hybrid-microservices
cd hybrid-microservices

# Initialize git repository
git init
echo "# Hybrid Go/Python Microservices" > README.md
git add README.md
git commit -m "Initial commit"

# Create service directories
mkdir -p python-service/{app/{api,core,db,models,schemas,services},tests,alembic/versions}
mkdir -p go-service/{cmd/worker,internal/{config,handlers,services,workers},pkg/{database,redis,logger},tests}
mkdir -p docker-compose
mkdir -p config/{dev,prod}

# Create essential files
touch python-service/{requirements.txt,Dockerfile,.dockerignore}
touch go-service/{go.mod,go.sum,Dockerfile,.dockerignore}
touch docker-compose/{docker-compose.yml,docker-compose.prod.yml}
touch .env.example
```

**Step 1.2: Python Service Foundation**
```bash
cd python-service

# Create Python files
cat > requirements.txt << 'EOF'
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
EOF

# Create main application file
cat > app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

app = FastAPI(
    title="Python REST API",
    description="Hybrid microservices Python API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Python REST API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "python-api"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# Create configuration
cat > app/core/config.py << 'EOF'
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/appdb"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Go service
    go_service_url: str = "http://go-worker:8080"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
EOF
```

#### Afternoon (4 hours): Go Service Foundation

**Step 1.3: Go Service Foundation**
```bash
cd ../go-service

# Initialize Go module
go mod init github.com/company/go-worker

# Create main.go
cat > cmd/worker/main.go << 'EOF'
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/company/go-worker/internal/config"
    "github.com/company/go-worker/pkg/logger"
)

func main() {
    // Initialize configuration
    cfg := config.Load()
    
    // Initialize logger
    logger.Init(cfg.LogLevel)
    
    // Create Gin router
    router := gin.New()
    router.Use(gin.Logger())
    router.Use(gin.Recovery())
    
    // Health check endpoint
    router.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "status":  "healthy",
            "service": "go-worker",
        })
    })
    
    // Start server
    srv := &http.Server{
        Addr:    ":" + cfg.Port,
        Handler: router,
    }
    
    // Graceful shutdown
    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("Failed to start server: %v", err)
        }
    }()
    
    // Wait for interrupt signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    
    log.Println("Shutting down server...")
    
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatal("Server forced to shutdown:", err)
    }
    
    log.Println("Server exited")
}
EOF

# Create configuration
cat > internal/config/config.go << 'EOF'
package config

import (
    "os"
)

type Config struct {
    Port        string
    DatabaseURL string
    RedisURL    string
    LogLevel    string
}

func Load() *Config {
    return &Config{
        Port:        getEnv("PORT", "8080"),
        DatabaseURL: getEnv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/appdb"),
        RedisURL:    getEnv("REDIS_URL", "redis://localhost:6379/0"),
        LogLevel:    getEnv("LOG_LEVEL", "info"),
    }
}

func getEnv(key, defaultValue string) string {
    if value := os.Getenv(key); value != "" {
        return value
    }
    return defaultValue
}
EOF

# Add initial dependencies
go mod tidy
```

### Day 2: Docker and Infrastructure

#### Morning (4 hours): Docker Configuration

**Step 2.1: Create Dockerfiles**

**Python Dockerfile:**
```bash
cd ../python-service
cat > Dockerfile << 'EOF'
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
EOF

# Create .dockerignore
cat > .dockerignore << 'EOF'
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.pytest_cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
.venv
.env
EOF
```

**Go Dockerfile:**
```bash
cd ../go-service
cat > Dockerfile << 'EOF'
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
EOF

# Create .dockerignore
cat > .dockerignore << 'EOF'
*.exe
*.exe~
*.dll
*.so
*.dylib
.git/
.gitignore
README.md
.env
.env.local
.env.production
.vscode/
.idea/
*.tmp
*.log
EOF
```

#### Afternoon (4 hours): Docker Compose Setup

**Step 2.2: Docker Compose Configuration**
```bash
cd ../docker-compose
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: hybrid_postgres
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - hybrid_network

  redis:
    image: redis:8.2-alpine
    container_name: hybrid_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    networks:
      - hybrid_network

  python-api:
    build:
      context: ../python-service
      target: development
    container_name: hybrid_python_api
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
      - ../python-service:/app
    networks:
      - hybrid_network
    restart: unless-stopped

  go-worker:
    build:
      context: ../go-service
      target: production
    container_name: hybrid_go_worker
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/appdb
      - REDIS_URL=redis://redis:6379/0
      - PORT=8080
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - hybrid_network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  hybrid_network:
    driver: bridge
EOF

# Create environment file
cd ..
cat > .env.example << 'EOF'
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/appdb

# Redis
REDIS_URL=redis://localhost:6379/0

# Python API
PYTHON_API_HOST=0.0.0.0
PYTHON_API_PORT=8000

# Go Worker
GO_WORKER_PORT=8080

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging
LOG_LEVEL=info
EOF
```

**Step 2.3: Test Initial Setup**
```bash
# Copy environment file
cp .env.example .env

# Start services
cd docker-compose
docker-compose up --build

# Test endpoints (in separate terminal)
curl http://localhost:8000/health  # Python API
curl http://localhost:8080/health  # Go Worker
```

### Day 3: Database Integration

#### Morning (4 hours): Database Models and Migrations

**Step 3.1: Python Database Setup**
```bash
cd ../python-service

# Create database models
cat > app/models/user.py << 'EOF'
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
EOF

cat > app/models/job.py << 'EOF'
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

Base = declarative_base()

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_type = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    parameters = Column(Text)  # JSON parameters
    result = Column(Text)  # JSON result
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="jobs")
EOF

# Update user model to include relationship
cat >> app/models/user.py << 'EOF'

from sqlalchemy.orm import relationship

# Add this to User class
User.jobs = relationship("Job", back_populates="user")
EOF

# Create database connection
cat > app/db/database.py << 'EOF'
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=True,
    future=True
)

# Create session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Dependency to get database session
async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
EOF

# Initialize Alembic
alembic init alembic

# Configure Alembic
cat > alembic.ini << 'EOF'
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql://postgres:postgres@localhost:5432/appdb

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
EOF

# Create first migration
alembic revision --autogenerate -m "Create users and jobs tables"
```

#### Afternoon (4 hours): Go Database Integration

**Step 3.2: Go Database Setup**
```bash
cd ../go-service

# Add database dependencies
go get github.com/jackc/pgx/v5
go get github.com/jackc/pgx/v5/pgxpool

# Create database package
cat > pkg/database/postgres.go << 'EOF'
package database

import (
    "context"
    "fmt"

    "github.com/jackc/pgx/v5/pgxpool"
)

type DB struct {
    Pool *pgxpool.Pool
}

func NewDB(databaseURL string) (*DB, error) {
    config, err := pgxpool.ParseConfig(databaseURL)
    if err != nil {
        return nil, fmt.Errorf("failed to parse database URL: %w", err)
    }

    pool, err := pgxpool.NewWithConfig(context.Background(), config)
    if err != nil {
        return nil, fmt.Errorf("failed to create connection pool: %w", err)
    }

    return &DB{Pool: pool}, nil
}

func (db *DB) Close() {
    db.Pool.Close()
}

func (db *DB) Ping(ctx context.Context) error {
    return db.Pool.Ping(ctx)
}
EOF

# Create models
cat > internal/models/job.go << 'EOF'
package models

import (
    "time"
)

type Job struct {
    ID           int       `json:"id"`
    UserID       int       `json:"user_id"`
    JobType      string    `json:"job_type"`
    Status       string    `json:"status"`
    Parameters   string    `json:"parameters"`
    Result       string    `json:"result"`
    ErrorMessage string    `json:"error_message"`
    CreatedAt    time.Time `json:"created_at"`
    UpdatedAt    time.Time `json:"updated_at"`
}

type JobStatus string

const (
    JobStatusPending    JobStatus = "pending"
    JobStatusProcessing JobStatus = "processing"
    JobStatusCompleted  JobStatus = "completed"
    JobStatusFailed     JobStatus = "failed"
)
EOF

# Update main.go to include database
cat > cmd/worker/main.go << 'EOF'
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/company/go-worker/internal/config"
    "github.com/company/go-worker/pkg/database"
    "github.com/company/go-worker/pkg/logger"
)

func main() {
    // Initialize configuration
    cfg := config.Load()
    
    // Initialize logger
    logger.Init(cfg.LogLevel)
    
    // Initialize database
    db, err := database.NewDB(cfg.DatabaseURL)
    if err != nil {
        log.Fatalf("Failed to connect to database: %v", err)
    }
    defer db.Close()
    
    // Test database connection
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    
    if err := db.Ping(ctx); err != nil {
        log.Fatalf("Failed to ping database: %v", err)
    }
    
    log.Println("Connected to database successfully")
    
    // Create Gin router
    router := gin.New()
    router.Use(gin.Logger())
    router.Use(gin.Recovery())
    
    // Health check endpoint
    router.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "status":   "healthy",
            "service":  "go-worker",
            "database": "connected",
        })
    })
    
    // Start server
    srv := &http.Server{
        Addr:    ":" + cfg.Port,
        Handler: router,
    }
    
    // Graceful shutdown
    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("Failed to start server: %v", err)
        }
    }()
    
    // Wait for interrupt signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    
    log.Println("Shutting down server...")
    
    ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatal("Server forced to shutdown:", err)
    }
    
    log.Println("Server exited")
}
EOF
```

### Day 4: Message Queue Integration

#### Morning (4 hours): Redis and Job Queue Setup

**Step 4.1: Python Redis Job Queue Setup**
```bash
cd ../python-service

# Create Redis job queue service
cat > app/services/redis_queue.py << 'EOF'
import json
import redis.asyncio as redis
from typing import Dict, Any
from app.core.config import settings

class RedisJobQueue:
    def __init__(self):
        self.redis_client = None
    
    async def connect(self):
        """Initialize Redis connection"""
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def queue_job(self, job_type: str, job_data: Dict[str, Any]) -> str:
        """Queue a job to Redis stream"""
        stream_name = f"jobs:{job_type}"
        
        # Add job to Redis stream
        job_id = await self.redis_client.xadd(
            stream_name,
            job_data,
            maxlen=10000  # Keep last 10k jobs
        )
        
        return job_id
    
    async def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Get job status from Redis or database"""
        # For now, we'll get status from database
        # In production, you might cache status in Redis
        return {"status": "pending", "job_id": job_id}
    
    async def publish_job_update(self, job_id: int, status: str, result: Dict[str, Any] = None):
        """Publish job status update"""
        update_data = {
            "job_id": job_id,
            "status": status,
            "timestamp": str(int(time.time()))
        }
        
        if result:
            update_data["result"] = json.dumps(result)
            
        await self.redis_client.publish(f"job_updates:{job_id}", json.dumps(update_data))

# Global job queue instance
job_queue = RedisJobQueue()

async def get_job_queue() -> RedisJobQueue:
    """Dependency to get job queue instance"""
    if job_queue.redis_client is None:
        await job_queue.connect()
    return job_queue
EOF

# Create job service
cat > app/services/job_service.py << 'EOF'
import json
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job import Job
from app.services.redis_queue import RedisJobQueue

class JobService:
    def __init__(self, db: AsyncSession, job_queue: RedisJobQueue):
        self.db = db
        self.job_queue = job_queue
    
    async def create_external_data_job(self, user_id: int, parameters: Dict[str, Any]) -> int:
        """Create and queue an external data job"""
        # Create job record in database
        job = Job(
            user_id=user_id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps(parameters)
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        # Queue job to Redis
        job_data = {
            "job_id": str(job.id),
            "user_id": str(user_id),
            "job_type": "external_data",
            "parameters": json.dumps(parameters)
        }
        
        await self.job_queue.queue_job("external_data", job_data)
        
        return job.id
    
    async def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """Get job status from database"""
        from sqlalchemy import select
        
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return None
            
        return {
            "id": job.id,
            "status": job.status,
            "result": json.loads(job.result) if job.result else None,
            "error_message": job.error_message,
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
    
    async def update_job_status(self, job_id: int, status: str, result: Dict[str, Any] = None, error_message: str = None):
        """Update job status in database"""
        from sqlalchemy import select
        
        result_db = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result_db.scalar_one_or_none()
        
        if job:
            job.status = status
            if result:
                job.result = json.dumps(result)
            if error_message:
                job.error_message = error_message
                
            await self.db.commit()
            
            # Publish update to Redis
            await self.job_queue.publish_job_update(job_id, status, result)
EOF
```

#### Afternoon (4 hours): Go Redis Integration

**Step 4.2: Go Redis and Job Processing**
```bash
cd ../go-service

# Add Redis dependencies (latest version)
go get github.com/redis/go-redis/v9@v9.7.0

# Create Redis client
cat > pkg/redis/client.go << 'EOF'
package redis

import (
    "context"
    "fmt"
    "time"

    "github.com/redis/go-redis/v9"
)

type Client struct {
    rdb *redis.Client
}

func NewClient(redisURL string) (*Client, error) {
    opt, err := redis.ParseURL(redisURL)
    if err != nil {
        return nil, fmt.Errorf("failed to parse Redis URL: %w", err)
    }

    rdb := redis.NewClient(opt)

    // Test connection
    ctx := context.Background()
    if err := rdb.Ping(ctx).Err(); err != nil {
        return nil, fmt.Errorf("failed to connect to Redis: %w", err)
    }

    return &Client{rdb: rdb}, nil
}

func (c *Client) Close() error {
    return c.rdb.Close()
}

func (c *Client) Ping(ctx context.Context) error {
    return c.rdb.Ping(ctx).Err()
}

// Job queue methods
func (c *Client) ReadStream(ctx context.Context, stream string, consumer string, group string) ([]redis.XStream, error) {
    return c.rdb.XReadGroup(ctx, &redis.XReadGroupArgs{
        Group:    group,
        Consumer: consumer,
        Streams:  []string{stream, ">"},
        Count:    10,
        Block:    time.Second,
    }).Result()
}

func (c *Client) AckMessage(ctx context.Context, stream string, group string, messageID string) error {
    return c.rdb.XAck(ctx, stream, group, messageID).Err()
}

func (c *Client) CreateConsumerGroup(ctx context.Context, stream string, group string) error {
    return c.rdb.XGroupCreate(ctx, stream, group, "$").Err()
}

func (c *Client) PublishUpdate(ctx context.Context, channel string, message string) error {
    return c.rdb.Publish(ctx, channel, message).Err()
}
EOF

# Create external API service
cat > internal/services/external_api.go << 'EOF'
package services

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "sync"
    "time"
)

type ExternalAPIService struct {
    client *http.Client
}

type APIResult struct {
    Source string      `json:"source"`
    Data   interface{} `json:"data"`
    Error  string      `json:"error,omitempty"`
}

func NewExternalAPIService() *ExternalAPIService {
    return &ExternalAPIService{
        client: &http.Client{
            Timeout: 30 * time.Second,
        },
    }
}

func (s *ExternalAPIService) FetchExternalData(ctx context.Context, parameters map[string]interface{}) ([]APIResult, error) {
    // Simulate multiple external API calls
    apis := []string{
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://jsonplaceholder.typicode.com/users/1",
        "https://jsonplaceholder.typicode.com/albums/1",
    }

    var wg sync.WaitGroup
    results := make(chan APIResult, len(apis))

    // Make concurrent API calls
    for _, apiURL := range apis {
        wg.Add(1)
        go func(url string) {
            defer wg.Done()
            
            req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
            if err != nil {
                results <- APIResult{
                    Source: url,
                    Error:  err.Error(),
                }
                return
            }

            resp, err := s.client.Do(req)
            if err != nil {
                results <- APIResult{
                    Source: url,
                    Error:  err.Error(),
                }
                return
            }
            defer resp.Body.Close()

            var data interface{}
            if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
                results <- APIResult{
                    Source: url,
                    Error:  err.Error(),
                }
                return
            }

            results <- APIResult{
                Source: url,
                Data:   data,
            }
        }(apiURL)
    }

    // Wait for all goroutines to complete
    go func() {
        wg.Wait()
        close(results)
    }()

    // Collect results
    var apiResults []APIResult
    for result := range results {
        apiResults = append(apiResults, result)
    }

    if len(apiResults) == 0 {
        return nil, fmt.Errorf("no results from external APIs")
    }

    return apiResults, nil
}
EOF

# Create job processor
cat > internal/workers/job_processor.go << 'EOF'
package workers

import (
    "context"
    "encoding/json"
    "fmt"
    "log"

    "github.com/company/go-worker/internal/models"
    "github.com/company/go-worker/internal/services"
    "github.com/company/go-worker/pkg/database"
)

type JobProcessor struct {
    db         *database.DB
    apiService *services.ExternalAPIService
}

func NewJobProcessor(db *database.DB) *JobProcessor {
    return &JobProcessor{
        db:         db,
        apiService: services.NewExternalAPIService(),
    }
}

func (jp *JobProcessor) ProcessExternalDataJob(ctx context.Context, jobID int, userID int, parameters map[string]interface{}) error {
    // Update job status to processing
    if err := jp.updateJobStatus(ctx, jobID, models.JobStatusProcessing, ""); err != nil {
        return fmt.Errorf("failed to update job status: %w", err)
    }

    // Fetch external data
    results, err := jp.apiService.FetchExternalData(ctx, parameters)
    if err != nil {
        // Update job with error
        if updateErr := jp.updateJobStatus(ctx, jobID, models.JobStatusFailed, err.Error()); updateErr != nil {
            log.Printf("Failed to update job error status: %v", updateErr)
        }
        return fmt.Errorf("failed to fetch external data: %w", err)
    }

    // Store results
    resultJSON, err := json.Marshal(results)
    if err != nil {
        return fmt.Errorf("failed to marshal results: %w", err)
    }

    // Update job with results
    if err := jp.updateJobResult(ctx, jobID, string(resultJSON)); err != nil {
        return fmt.Errorf("failed to update job result: %w", err)
    }

    return nil
}

func (jp *JobProcessor) updateJobStatus(ctx context.Context, jobID int, status models.JobStatus, errorMessage string) error {
    query := `
        UPDATE jobs 
        SET status = $1, error_message = $2, updated_at = NOW()
        WHERE id = $3
    `
    _, err := jp.db.Pool.Exec(ctx, query, status, errorMessage, jobID)
    return err
}

func (jp *JobProcessor) updateJobResult(ctx context.Context, jobID int, result string) error {
    query := `
        UPDATE jobs 
        SET status = $1, result = $2, updated_at = NOW()
        WHERE id = $3
    `
    _, err := jp.db.Pool.Exec(ctx, query, models.JobStatusCompleted, result, jobID)
    return err
}
EOF
```

### Day 5: API Endpoints and Integration

#### Morning (4 hours): Python API Endpoints

**Step 5.1: Create API Endpoints**
```bash
cd ../python-service

# Create schemas
cat > app/schemas/user.py << 'EOF'
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str
EOF

cat > app/schemas/job.py << 'EOF'
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class JobBase(BaseModel):
    job_type: str
    parameters: Dict[str, Any]

class JobCreate(JobBase):
    user_id: int

class JobResponse(JobBase):
    id: int
    user_id: int
    status: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ExternalDataRequest(BaseModel):
    data_sources: list[str]
    filters: Optional[Dict[str, Any]] = None
EOF

# Create API endpoints
cat > app/api/endpoints.py << 'EOF'
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.schemas.job import JobCreate, JobResponse, ExternalDataRequest
from app.services.job_service import JobService
from app.models.user import User
from app.models.job import Job

router = APIRouter()

@router.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user"""
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create new user
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hash_password(user.password)  # Implement password hashing
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user by ID"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.post("/users/{user_id}/external-data")
async def create_external_data_job(
    user_id: int,
    request: ExternalDataRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create external data fetching job"""
    # Use JobService for job creation and Go service communication
    job_service = JobService(db)
    
    try:
        job_id = await job_service.create_external_data_job(
            user_id=user_id,
            parameters=request.dict()
        )
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "External data fetching job has been queued"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to create job"
        )

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    """Get job status and results"""
    result = await db.execute(
        select(Job).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.get("/users/{user_id}/jobs", response_model=List[JobResponse])
async def get_user_jobs(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all jobs for a user"""
    result = await db.execute(
        select(Job).where(Job.user_id == user_id).offset(skip).limit(limit)
    )
    jobs = result.scalars().all()
    
    return jobs

def hash_password(password: str) -> str:
    """Hash password - implement proper password hashing"""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)
EOF

# Update main.py to include routes
cat >> app/main.py << 'EOF'

from app.api.endpoints import router as api_router

app.include_router(api_router, prefix="/api/v1")
EOF
```

#### Afternoon (4 hours): Go HTTP Handlers

**Step 5.2: Go HTTP Endpoints**
```bash
cd ../go-service

# Create HTTP handlers
cat > internal/handlers/jobs.go << 'EOF'
package handlers

import (
    "context"
    "encoding/json"
    "net/http"
    "strconv"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/company/go-worker/internal/workers"
    "github.com/company/go-worker/pkg/database"
)

type JobHandler struct {
    processor *workers.JobProcessor
}

type ExternalDataJobRequest struct {
    JobID      int                    `json:"job_id"`
    UserID     int                    `json:"user_id"`
    Parameters map[string]interface{} `json:"parameters"`
}

func NewJobHandler(db *database.DB) *JobHandler {
    return &JobHandler{
        processor: workers.NewJobProcessor(db),
    }
}

func (h *JobHandler) ProcessExternalDataJob(c *gin.Context) {
    var req ExternalDataJobRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    // Process job in background
    go func() {
        ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
        defer cancel()

        if err := h.processor.ProcessExternalDataJob(ctx, req.JobID, req.UserID, req.Parameters); err != nil {
            // Log error - in production, you might want to use a proper logging system
            println("Failed to process external data job:", err.Error())
        }
    }()

    c.JSON(http.StatusOK, gin.H{
        "message": "Job processing started",
        "job_id":  req.JobID,
    })
}

func (h *JobHandler) GetJobStatus(c *gin.Context) {
    jobIDStr := c.Param("id")
    jobID, err := strconv.Atoi(jobIDStr)
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid job ID"})
        return
    }

    // Get job status from database
    ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
    defer cancel()

    var job struct {
        ID           int    `json:"id"`
        Status       string `json:"status"`
        Result       string `json:"result"`
        ErrorMessage string `json:"error_message"`
    }

    query := `
        SELECT id, status, COALESCE(result, '') as result, COALESCE(error_message, '') as error_message
        FROM jobs WHERE id = $1
    `
    
    err = h.processor.db.Pool.QueryRow(ctx, query, jobID).Scan(
        &job.ID, &job.Status, &job.Result, &job.ErrorMessage,
    )
    
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job not found"})
        return
    }

    // Parse result JSON if available
    var result interface{}
    if job.Result != "" {
        json.Unmarshal([]byte(job.Result), &result)
    }

    response := gin.H{
        "id":     job.ID,
        "status": job.Status,
    }
    
    if result != nil {
        response["result"] = result
    }
    
    if job.ErrorMessage != "" {
        response["error"] = job.ErrorMessage
    }

    c.JSON(http.StatusOK, response)
}
EOF

# Update main.go to include job handlers
cat > cmd/worker/main.go << 'EOF'
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/company/go-worker/internal/config"
    "github.com/company/go-worker/internal/handlers"
    "github.com/company/go-worker/pkg/database"
    "github.com/company/go-worker/pkg/logger"
    "github.com/company/go-worker/pkg/redis"
)

func main() {
    // Initialize configuration
    cfg := config.Load()
    
    // Initialize logger
    logger.Init(cfg.LogLevel)
    
    // Initialize database
    db, err := database.NewDB(cfg.DatabaseURL)
    if err != nil {
        log.Fatalf("Failed to connect to database: %v", err)
    }
    defer db.Close()
    
    // Initialize Redis
    redisClient, err := redis.NewClient(cfg.RedisURL)
    if err != nil {
        log.Fatalf("Failed to connect to Redis: %v", err)
    }
    defer redisClient.Close()
    
    // Test connections
    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()
    
    if err := db.Ping(ctx); err != nil {
        log.Fatalf("Failed to ping database: %v", err)
    }
    
    if err := redisClient.Ping(ctx); err != nil {
        log.Fatalf("Failed to ping Redis: %v", err)
    }
    
    log.Println("Connected to database and Redis successfully")
    
    // Initialize handlers
    jobHandler := handlers.NewJobHandler(db)
    
    // Create Gin router
    router := gin.New()
    router.Use(gin.Logger())
    router.Use(gin.Recovery())
    
    // Health check endpoint
    router.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "status":   "healthy",
            "service":  "go-worker",
            "database": "connected",
            "redis":    "connected",
        })
    })
    
    // Job endpoints
    v1 := router.Group("/api/v1")
    {
        v1.POST("/jobs/external-data", jobHandler.ProcessExternalDataJob)
        v1.GET("/jobs/:id/status", jobHandler.GetJobStatus)
    }
    
    // Start server
    srv := &http.Server{
        Addr:    ":" + cfg.Port,
        Handler: router,
    }
    
    // Graceful shutdown
    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("Failed to start server: %v", err)
        }
    }()
    
    log.Printf("Server started on port %s", cfg.Port)
    
    // Wait for interrupt signal
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit
    
    log.Println("Shutting down server...")
    
    ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := srv.Shutdown(ctx); err != nil {
        log.Fatal("Server forced to shutdown:", err)
    }
    
    log.Println("Server exited")
}
EOF
```

### Day 6: Testing and Validation

#### Morning (4 hours): Testing Setup

**Step 6.1: Create Test Files**
```bash
cd ../python-service

# Create test configuration
cat > pytest.ini << 'EOF'
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
asyncio_mode = auto
EOF

# Create test files
mkdir -p tests
cat > tests/test_api.py << 'EOF'
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_create_user():
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword"
    }
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/users/", json=user_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert "id" in data
EOF

cd ../go-service

# Create Go tests
cat > internal/handlers/jobs_test.go << 'EOF'
package handlers

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/gin-gonic/gin"
    "github.com/stretchr/testify/assert"
)

func TestHealthCheck(t *testing.T) {
    gin.SetMode(gin.TestMode)
    router := gin.New()
    
    router.GET("/health", func(c *gin.Context) {
        c.JSON(http.StatusOK, gin.H{
            "status":  "healthy",
            "service": "go-worker",
        })
    })

    req, _ := http.NewRequest("GET", "/health", nil)
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)

    assert.Equal(t, http.StatusOK, w.Code)
    
    var response map[string]string
    err := json.Unmarshal(w.Body.Bytes(), &response)
    assert.NoError(t, err)
    assert.Equal(t, "healthy", response["status"])
}
EOF
```

#### Afternoon (4 hours): Integration Testing

**Step 6.2: End-to-End Testing**
```bash
# Create integration test script
cd ../
cat > test_integration.sh << 'EOF'
#!/bin/bash

echo "Starting integration tests..."

# Start services
docker-compose -f docker-compose/docker-compose.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 30

# Test Python API health
echo "Testing Python API health..."
curl -f http://localhost:8000/health || exit 1

# Test Go Worker health
echo "Testing Go Worker health..."
curl -f http://localhost:8080/health || exit 1

# Test user creation
echo "Testing user creation..."
curl -X POST http://localhost:8000/api/v1/users/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"testpass"}' \
  || exit 1

# Test external data job
echo "Testing external data job..."
JOB_RESPONSE=$(curl -X POST http://localhost:8000/api/v1/users/1/external-data \
  -H "Content-Type: application/json" \
  -d '{"data_sources":["api1","api2"],"filters":{"type":"test"}}')

echo "Job response: $JOB_RESPONSE"

# Extract job ID and check status
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Checking job status for job ID: $JOB_ID"

sleep 10

curl -f http://localhost:8000/api/v1/jobs/$JOB_ID || exit 1

echo "Integration tests completed successfully!"

# Cleanup
docker-compose -f docker-compose/docker-compose.yml down
EOF

chmod +x test_integration.sh
```

### Day 7: Monitoring and Logging

#### Morning (4 hours): Add Monitoring

**Step 7.1: Prometheus Metrics**
```bash
cd python-service

# Add Prometheus metrics to Python
cat > app/core/metrics.py << 'EOF'
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
from functools import wraps

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_JOBS = Gauge('active_jobs_total', 'Number of active jobs', ['status'])

def track_requests(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(method='POST', endpoint='/api/v1/jobs', status='success').inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/api/v1/jobs', status='error').inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    return wrapper
EOF

cd ../go-service

# Add Prometheus metrics to Go
go get github.com/prometheus/client_golang/prometheus
go get github.com/prometheus/client_golang/prometheus/promhttp

cat > pkg/metrics/metrics.go << 'EOF'
package metrics

import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    JobsProcessed = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "jobs_processed_total",
            Help: "Total number of processed jobs",
        },
        []string{"status"},
    )

    JobDuration = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name: "job_duration_seconds",
            Help: "Duration of job processing",
        },
        []string{"job_type"},
    )

    ExternalAPICalls = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "external_api_calls_total",
            Help: "Total external API calls",
        },
        []string{"api", "status"},
    )
)
EOF
```

#### Afternoon (4 hours): Logging and Error Handling

**Step 7.2: Structured Logging**
```bash
# Add structured logging to Go
go get github.com/rs/zerolog

cat > pkg/logger/logger.go << 'EOF'
package logger

import (
    "os"
    "strings"

    "github.com/rs/zerolog"
    "github.com/rs/zerolog/log"
)

func Init(level string) {
    // Configure zerolog
    zerolog.TimeFieldFormat = zerolog.TimeFormatUnix

    // Set log level
    switch strings.ToLower(level) {
    case "debug":
        zerolog.SetGlobalLevel(zerolog.DebugLevel)
    case "info":
        zerolog.SetGlobalLevel(zerolog.InfoLevel)
    case "warn":
        zerolog.SetGlobalLevel(zerolog.WarnLevel)
    case "error":
        zerolog.SetGlobalLevel(zerolog.ErrorLevel)
    default:
        zerolog.SetGlobalLevel(zerolog.InfoLevel)
    }

    // Pretty print in development
    if os.Getenv("GO_ENV") == "development" {
        log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
    }
}

func Info() *zerolog.Event {
    return log.Info()
}

func Error() *zerolog.Event {
    return log.Error()
}

func Debug() *zerolog.Event {
    return log.Debug()
}

func Warn() *zerolog.Event {
    return log.Warn()
}
EOF
```

### Day 8: Production Optimization

#### Morning (4 hours): Performance Optimization

**Step 8.1: Connection Pooling and Caching**
```bash
cd ../python-service

# Optimize database connections
cat > app/db/database.py << 'EOF'
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create async engine with optimized settings
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,  # Disable in production
    future=True,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create session factory
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Dependency to get database session
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
EOF

cd ../go-service

# Optimize Go database connections
cat > pkg/database/postgres.go << 'EOF'
package database

import (
    "context"
    "fmt"
    "time"

    "github.com/jackc/pgx/v5/pgxpool"
)

type DB struct {
    Pool *pgxpool.Pool
}

func NewDB(databaseURL string) (*DB, error) {
    config, err := pgxpool.ParseConfig(databaseURL)
    if err != nil {
        return nil, fmt.Errorf("failed to parse database URL: %w", err)
    }

    // Optimize connection pool settings
    config.MaxConns = 30
    config.MinConns = 5
    config.MaxConnLifetime = time.Hour
    config.MaxConnIdleTime = time.Minute * 30
    config.HealthCheckPeriod = time.Minute

    pool, err := pgxpool.NewWithConfig(context.Background(), config)
    if err != nil {
        return nil, fmt.Errorf("failed to create connection pool: %w", err)
    }

    return &DB{Pool: pool}, nil
}

func (db *DB) Close() {
    db.Pool.Close()
}

func (db *DB) Ping(ctx context.Context) error {
    return db.Pool.Ping(ctx)
}

func (db *DB) Stats() *pgxpool.Stat {
    return db.Pool.Stat()
}
EOF
```

#### Afternoon (4 hours): Security and Deployment

**Step 8.2: Security Hardening**
```bash
# Create production Docker Compose
cd ../docker-compose
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - hybrid_network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M

  redis:
    image: redis:8.2-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - hybrid_network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  python-api:
    build:
      context: ../python-service
      target: production
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - redis
    networks:
      - hybrid_network
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  go-worker:
    build:
      context: ../go-service
      target: production
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - PORT=8080
    depends_on:
      - postgres
      - redis
    networks:
      - hybrid_network
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - python-api
    networks:
      - hybrid_network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  hybrid_network:
    driver: bridge
EOF

# Create nginx configuration
cat > nginx.conf << 'EOF'
events {
    worker_connections 1024;
}

http {
    upstream python_api {
        server python-api:8000;
    }

    upstream go_worker {
        server go-worker:8080;
    }

    server {
        listen 80;
        server_name localhost;

        location /api/ {
            proxy_pass http://python_api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /worker/ {
            proxy_pass http://go_worker/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF
```

## Final Deployment Checklist

### Pre-deployment
- [ ] All tests passing
- [ ] Security review completed
- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Database migrations applied
- [ ] Monitoring configured

### Deployment Steps
1. Build and push Docker images
2. Update environment variables
3. Deploy database migrations
4. Deploy services with rolling update
5. Verify health checks
6. Configure monitoring alerts
7. Update DNS records

### Post-deployment
- [ ] Monitor application metrics
- [ ] Check error logs
- [ ] Verify all endpoints working
- [ ] Test job processing
- [ ] Confirm external API connectivity

## Troubleshooting Guide

### Common Issues
1. **Database Connection Errors**
   - Check connection string format
   - Verify network connectivity
   - Check database credentials

2. **Redis Connection Issues**
   - Verify Redis is running
   - Check Redis password
   - Confirm network access

3. **Job Processing Failures**
   - Check external API connectivity
   - Verify job queue is running
   - Review error logs

4. **Performance Issues**
   - Monitor connection pool usage
   - Check resource utilization
   - Review slow query logs

This implementation guide provides a complete roadmap for building the hybrid Go/Python microservices architecture with proper separation of concerns, optimized Docker configurations, and production-ready deployment strategies.