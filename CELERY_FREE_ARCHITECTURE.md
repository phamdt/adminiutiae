# Celery-Free Go/Python Architecture

## The Problem with Celery
- **Complex Setup**: Requires separate broker, workers, and monitoring
- **Python-Centric**: Doesn't play well with Go services
- **Resource Heavy**: Additional processes and memory overhead
- **Integration Complexity**: Hard to share job state between Go and Python

## Solution: Direct HTTP + Redis Architecture

### Core Principle
**Python handles HTTP APIs → Go handles everything else**

## Architecture Overview

```
┌─────────────────┐    HTTP POST     ┌─────────────────┐
│   Python API    │ ──────────────► │   Go Worker     │
│   (FastAPI)     │                 │   (Gin + Jobs)  │
└─────────────────┘                 └─────────────────┘
         │                                   │
         │                                   │
         ▼                                   ▼
┌─────────────────┐    Redis Pub/Sub  ┌─────────────────┐
│   PostgreSQL    │ ◄─────────────── │     Redis       │
│   (Job Status)  │                  │  (Notifications)│
└─────────────────┘                  └─────────────────┘
```

## How It Works

### 1. Job Initiation (Python → Go)
```python
# Python API receives request
@app.post("/users/{user_id}/external-data")
async def start_external_data_job(user_id: int, params: dict):
    # 1. Create job record in database
    job = create_job_record(user_id, "external_data", params)
    
    # 2. Send HTTP request to Go service
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GO_SERVICE_URL}/jobs/process",
            json={
                "job_id": job.id,
                "job_type": "external_data",
                "user_id": user_id,
                "parameters": params
            },
            timeout=5.0  # Quick timeout - fire and forget
        )
    
    # 3. Return immediately
    return {"job_id": job.id, "status": "processing"}
```

### 2. Job Processing (Go)
```go
// Go service receives job
func (h *JobHandler) ProcessJob(c *gin.Context) {
    var req JobRequest
    c.ShouldBindJSON(&req)
    
    // Process asynchronously
    go h.processJobAsync(req)
    
    // Return immediately
    c.JSON(200, gin.H{"status": "accepted"})
}

func (h *JobHandler) processJobAsync(req JobRequest) {
    // 1. Update job status to processing
    h.updateJobStatus(req.JobID, "processing")
    
    // 2. Do actual work (external APIs, etc.)
    result, err := h.doExternalAPIWork(req.Parameters)
    
    // 3. Update job with results
    if err != nil {
        h.updateJobStatus(req.JobID, "failed", err.Error())
    } else {
        h.updateJobWithResult(req.JobID, "completed", result)
    }
    
    // 4. Notify via Redis pub/sub
    h.notifyJobComplete(req.JobID)
}
```

### 3. Status Checking (Python)
```python
# Python provides status endpoint
@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: int):
    job = await get_job_from_db(job_id)
    return {
        "job_id": job.id,
        "status": job.status,
        "result": job.result,
        "created_at": job.created_at,
        "completed_at": job.completed_at
    }
```

## Benefits of This Approach

### ✅ Maximum Go/Python Interoperability
- **Simple HTTP**: Both languages handle HTTP naturally
- **Shared Database**: Single source of truth for job state
- **No Message Brokers**: No complex serialization/deserialization
- **Easy Testing**: Can test services independently

### ✅ Simplified Dependencies
**Python:**
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
httpx==0.25.2
redis==5.0.1  # Only for pub/sub notifications
```

**Go:**
```go
github.com/gin-gonic/gin v1.9.1
github.com/jackc/pgx/v5 v5.5.0
github.com/redis/go-redis/v9 v9.3.0  // Only for pub/sub
```

### ✅ Operational Simplicity
- **2 Services Only**: Python API + Go Worker
- **No Queue Management**: No dead letter queues, retries, etc.
- **Standard Monitoring**: HTTP metrics, database queries
- **Easy Scaling**: Scale services independently

## Implementation Details

### Database Schema
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    parameters JSONB,
    result JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
```

### Error Handling & Retries
```go
// Go service handles retries internally
func (h *JobHandler) processJobWithRetry(req JobRequest) {
    maxRetries := 3
    
    for attempt := 1; attempt <= maxRetries; attempt++ {
        err := h.processJob(req)
        if err == nil {
            return // Success
        }
        
        // Log error and wait before retry
        log.Printf("Job %d failed attempt %d: %v", req.JobID, attempt, err)
        
        if attempt < maxRetries {
            time.Sleep(time.Duration(attempt) * time.Second)
        }
    }
    
    // All retries failed
    h.updateJobStatus(req.JobID, "failed", "Max retries exceeded")
}
```

### Real-time Notifications (Optional)
```python
# Python can subscribe to Redis for real-time updates
async def subscribe_to_job_updates():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("job_updates")
    
    async for message in pubsub.listen():
        job_data = json.loads(message['data'])
        # Send WebSocket update to frontend
        await websocket_manager.broadcast(job_data)
```

## Alternative: Pure HTTP Polling

For even simpler architecture, skip Redis entirely:

### Frontend Polling
```javascript
// Frontend polls for job status
async function pollJobStatus(jobId) {
    const response = await fetch(`/api/jobs/${jobId}/status`);
    const job = await response.json();
    
    if (job.status === 'processing') {
        setTimeout(() => pollJobStatus(jobId), 2000); // Poll every 2 seconds
    }
    
    return job;
}
```

### Server-Sent Events
```python
# Python API provides SSE for job updates
@app.get("/jobs/{job_id}/events")
async def job_events(job_id: int):
    async def event_generator():
        while True:
            job = await get_job_from_db(job_id)
            yield f"data: {json.dumps(job.dict())}\n\n"
            
            if job.status in ['completed', 'failed']:
                break
                
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/plain")
```

## Production Considerations

### Health Checks
```go
// Go service health check includes job queue health
func (h *HealthHandler) Check(c *gin.Context) {
    // Check database connection
    if err := h.db.Ping(context.Background()); err != nil {
        c.JSON(503, gin.H{"status": "unhealthy", "database": "down"})
        return
    }
    
    // Check pending jobs count
    pendingJobs := h.getPendingJobsCount()
    
    c.JSON(200, gin.H{
        "status": "healthy",
        "database": "up",
        "pending_jobs": pendingJobs,
    })
}
```

### Monitoring
```go
// Prometheus metrics
var (
    jobsProcessed = prometheus.NewCounterVec(
        prometheus.CounterOpts{Name: "jobs_processed_total"},
        []string{"status"},
    )
    
    jobDuration = prometheus.NewHistogramVec(
        prometheus.HistogramOpts{Name: "job_duration_seconds"},
        []string{"job_type"},
    )
)
```

### Graceful Shutdown
```go
// Go service graceful shutdown
func (s *Server) Shutdown(ctx context.Context) error {
    // Stop accepting new jobs
    s.jobHandler.StopAcceptingJobs()
    
    // Wait for current jobs to complete (with timeout)
    done := make(chan bool, 1)
    go func() {
        s.jobHandler.WaitForJobsToComplete()
        done <- true
    }()
    
    select {
    case <-done:
        return nil
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

## Docker Configuration

### Python Service (Minimal)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Go Service (Minimal)
```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.* ./
RUN go mod download
COPY . .
RUN go build -o worker ./cmd/worker

FROM alpine:3.18
COPY --from=builder /app/worker .
CMD ["./worker"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    
  redis:
    image: redis:7-alpine
    # Optional: only needed for pub/sub notifications
    
  python-api:
    build: ./python-service
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/appdb
      - GO_SERVICE_URL=http://go-worker:8080
    depends_on:
      - postgres
      
  go-worker:
    build: ./go-service
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/appdb
    depends_on:
      - postgres
```

## Summary

This architecture eliminates Celery completely while maximizing Go/Python interoperability:

1. **Python**: Handles HTTP APIs, simple database operations
2. **Go**: Handles all external APIs, concurrency, heavy processing
3. **Communication**: Simple HTTP requests (fire-and-forget)
4. **State**: Shared PostgreSQL database
5. **Notifications**: Optional Redis pub/sub or HTTP polling

**Result**: Simple, scalable, maintainable architecture with excellent Go/Python integration.