# Comprehensive Testing Guide

## 🧪 Test Suite Overview

This project includes a comprehensive test suite designed to ensure reliability, performance, and maintainability of the hybrid Go/Python microservices architecture.

## 📊 Test Coverage

### Python Tests (145+ tests)
- **Authentication Tests** (32 tests): `tests/python/test_auth_api.py`
- **Job Management Tests** (45 tests): `tests/python/test_job_management.py`
- **Database Operations** (28 tests): `tests/python/test_database_operations.py`
- **Job Service Unit Tests** (25 tests): `tests/python/test_job_service_unit.py`
- **User API Tests** (15 tests): `tests/python/test_user_api.py`

### Go Tests (35+ tests)
- **External API Tests** (20 tests): `tests/go/external_api_test.go`
- **Job Handler Tests** (10 tests): `tests/go/job_handler_test.go`
- **Database Tests** (5 tests): `tests/go/database_test.go`

### Integration Tests (12 tests)
- **Service Integration** (12 tests): `tests/integration/test_service_integration.py`

### Performance Tests (15 tests)
- **Load Testing** (15 tests): `tests/performance/test_load_testing.py`

## 🎯 Test Categories

### 🟢 Unit Tests (Fast)
Test individual components in isolation with mocked dependencies.

```bash
# Python unit tests
pytest tests/python/test_job_service_unit.py -v

# Go unit tests  
cd go-service && go test ./tests/... -v
```

### 🟡 Integration Tests (Medium)
Test service-to-service communication with real dependencies.

```bash
# Integration tests
pytest tests/integration/ -v -m integration
```

### 🔴 Performance Tests (Slow)
Test system behavior under load and stress conditions.

```bash
# Performance tests
pytest tests/performance/ -v -m slow
```

## 🔧 Test Execution

### Quick Development Testing
```bash
# Fast feedback loop during development
pytest tests/python/test_auth_api.py::TestUserRegistration::test_create_user_success -v

# Run all unit tests (fast)
pytest -m unit -v
```

### Complete Test Suite
```bash
# Run all tests
./run_ci_tests.sh

# Or manually:
pytest tests/ -v --cov=app
cd go-service && go test -v ./...
```

### GitHub Actions Compatible
```bash
# Same commands as CI/CD pipeline
./run_ci_tests.sh

# Or step by step:
./validate_code.sh
pytest tests/python/ -v --cov=app --cov-report=xml
cd go-service && go test -v -race -coverprofile=coverage.out ./...
```

## 📋 Test Scenarios Covered

### Authentication & Security
- ✅ User registration with validation
- ✅ Password hashing and verification
- ✅ JWT token generation and validation
- ✅ Protected endpoint access
- ✅ Authorization checks
- ✅ SQL injection prevention
- ✅ Token tampering detection
- ✅ Brute force protection

### Job Management
- ✅ Job creation and validation
- ✅ Status tracking (queued → processing → completed)
- ✅ Error handling and failure scenarios
- ✅ Job cancellation
- ✅ Result retrieval and formatting
- ✅ User authorization for jobs
- ✅ Large payload handling
- ✅ Concurrent job processing

### Service Communication
- ✅ Python → Go HTTP communication
- ✅ Go service job processing
- ✅ Database consistency between services
- ✅ Error propagation
- ✅ Timeout handling
- ✅ Service recovery

### Database Operations
- ✅ Model validation and constraints
- ✅ Relationship integrity
- ✅ Transaction handling
- ✅ Query performance
- ✅ Connection pooling
- ✅ Concurrent operations

### External API Integration
- ✅ HTTP client functionality
- ✅ Concurrent API calls
- ✅ Retry logic and error handling
- ✅ Timeout management
- ✅ Response parsing and validation
- ✅ Rate limiting handling

### Performance & Scalability
- ✅ High concurrency handling
- ✅ Response time consistency
- ✅ Memory usage optimization
- ✅ Database connection pool efficiency
- ✅ Large payload processing
- ✅ Sustained load testing

## 🎭 Mock Strategy

### External Dependencies Mocked
- **External APIs**: Mocked with `httptest.NewServer` (Go) and `httpx` mocks (Python)
- **Go Service Communication**: Mocked HTTP client responses
- **Database**: Real database for integration tests, mocked for unit tests
- **Redis**: Real Redis for integration, mocked for unit tests

### Test Data Management
- **Database Isolation**: Each test runs in its own transaction
- **Cleanup**: Automatic rollback after each test
- **Fixtures**: Reusable test data via pytest fixtures
- **Factories**: Generate test data with realistic variations

## 🚀 Running Tests Locally

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock httpx psutil
go get github.com/stretchr/testify

# Start test infrastructure
docker run -d --name test-postgres \
  -e POSTGRES_DB=testdb -e POSTGRES_USER=testuser -e POSTGRES_PASSWORD=testpass \
  -p 5433:5432 postgres:16-alpine

docker run -d --name test-redis -p 6380:6379 redis:8.2-alpine
```

### Run Tests
```bash
# All tests
./run_ci_tests.sh

# Python only
cd python-service
pytest tests/ -v

# Go only
cd go-service
go test ./tests/... -v

# Specific test
pytest tests/python/test_auth_api.py::TestUserRegistration -v
```

## 📈 Performance Benchmarks

### Expected Performance Metrics
- **User Creation**: >5 users/second
- **Job Creation**: >6 jobs/second  
- **Authentication**: >20 logins/second
- **Database Queries**: >30 operations/second
- **Status Checks**: >50 requests/second

### Memory Usage
- **Python Service**: <100MB increase under load
- **Go Service**: <50MB baseline
- **Database Connections**: Pool utilization <80%

### Response Times
- **Average Response**: <100ms
- **95th Percentile**: <200ms
- **Maximum Response**: <500ms
- **Database Queries**: <50ms

## 🐛 Debugging Test Failures

### Common Issues

**Database Connection Errors:**
```bash
# Check if test database is running
docker ps | grep test-postgres
psql "postgresql://testuser:testpass@localhost:5433/testdb" -c "SELECT 1;"
```

**Import Errors:**
```bash
# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/python-service"

# Verify imports
cd python-service && python -c "from app.main import app; print('OK')"
```

**Go Test Failures:**
```bash
# Run with verbose output
cd go-service && go test -v ./tests/...

# Check for race conditions
go test -race ./tests/...
```

### Debug Specific Tests
```bash
# Run single test with full output
pytest tests/python/test_auth_api.py::test_create_user_success -v -s --tb=long

# Drop into debugger on failure
pytest --pdb tests/python/test_auth_api.py::test_create_user_success

# Run with increased logging
pytest tests/ -v -s --log-cli-level=DEBUG
```

## 📊 Test Metrics

### Coverage Goals
- **Python Code Coverage**: >90%
- **Go Code Coverage**: >85%
- **API Endpoint Coverage**: 100%
- **Error Path Coverage**: >80%

### Test Execution Time
- **Unit Tests**: <30 seconds total
- **Integration Tests**: <2 minutes total
- **Performance Tests**: <5 minutes total
- **Full Test Suite**: <8 minutes total

## 🎨 Test Writing Guidelines

### Test Naming Convention
```python
# Good
def test_create_user_with_valid_data_returns_user_object():

# Bad  
def test_user_creation():
```

### Test Structure (AAA Pattern)
```python
async def test_example():
    # Arrange
    user_data = {"email": "test@example.com", ...}
    
    # Act
    response = await client.post("/api/v1/users/", json=user_data)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["email"] == user_data["email"]
```

### Mock Usage
```python
# Good - Mock external dependencies
with patch('httpx.AsyncClient.post') as mock_post:
    mock_post.return_value = mock_response
    result = await service.call_external_api()

# Bad - Mock internal logic
with patch('app.services.job_service.JobService.create_job'):
    # This tests the mock, not the code
```

## 🔄 Continuous Integration

### GitHub Actions Workflow
The `.github/workflows/ci.yml` file defines the complete CI/CD pipeline:

1. **Code Quality Checks**
   - Python syntax and linting
   - Go formatting and vetting
   - Security scanning

2. **Unit Testing**
   - Python unit tests with coverage
   - Go unit tests with race detection

3. **Integration Testing**
   - Service-to-service communication
   - Database operations
   - End-to-end workflows

4. **Docker Validation**
   - Image building
   - Container startup
   - Service health checks

### Pre-commit Hooks (Recommended)
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📚 Test Data & Fixtures

### Available Fixtures
- `client`: HTTP client with database override
- `authenticated_user`: User with valid JWT token
- `test_user`: Basic user in database
- `mock_processing_job`: Job in processing state
- `mock_completed_job`: Job with results
- `mock_failed_job`: Job with error message
- `db_session`: Database session with transaction rollback

### Test Data Patterns
```python
# User data variations
VALID_USERS = [
    {"email": "test@example.com", "username": "testuser", "password": "ValidPass123!"},
    {"email": "admin@example.com", "username": "admin", "password": "AdminPass456!"},
]

# Job data variations
VALID_JOBS = [
    {"data_sources": ["https://api.example.com/data"], "filters": {}},
    {"data_sources": ["https://api1.com", "https://api2.com"], "filters": {"type": "test"}},
]
```

## 🎯 Next Steps

### To Add More Tests
1. **Create test file** in appropriate directory
2. **Follow naming conventions** (`test_*.py` or `*_test.go`)
3. **Use existing fixtures** when possible
4. **Add appropriate markers** (`@pytest.mark.unit`, etc.)
5. **Update this documentation**

### To Run in CI/CD
1. **Ensure all tests pass locally** with `./run_ci_tests.sh`
2. **Check coverage reports** are acceptable
3. **Verify Docker builds** work correctly
4. **Commit and push** to trigger GitHub Actions

This comprehensive test suite ensures the hybrid Go/Python architecture is robust, performant, and maintainable.