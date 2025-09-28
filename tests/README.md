# Test Suite for Hybrid Go/Python Microservices

## Overview

This test suite implements comprehensive end-to-end testing for the hybrid Go/Python microservices architecture using Test-Driven Development (TDD) principles.

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── python/                     # Python service tests
│   ├── test_user_api.py       # User management API tests
│   └── test_job_api.py        # Job management API tests
├── go/                        # Go service tests
│   └── job_processor_test.go  # Go job processor tests
├── integration/               # Integration tests
│   └── test_service_integration.py
└── README.md                  # This file
```

## Test Categories

### 🔴 Unit Tests (Fast)
- Test individual components in isolation
- Mock external dependencies
- Run in < 1 second per test
- **Markers**: `@pytest.mark.unit`

### 🟡 Integration Tests (Medium)
- Test service-to-service communication
- Use real database and Redis
- Run in < 10 seconds per test
- **Markers**: `@pytest.mark.integration`

### 🟢 End-to-End Tests (Slow)
- Test complete user workflows
- Use all real services
- Run in < 60 seconds per test
- **Markers**: `@pytest.mark.e2e`

## TDD Workflow

### Phase 1: Red 🔴
Write failing tests first:

```bash
# Run specific test to see it fail
pytest tests/python/test_user_api.py::TestUserRegistration::test_create_user_success -v

# Expected: FAILED (because implementation doesn't exist yet)
```

### Phase 2: Green 🟢
Write minimal code to make tests pass:

```bash
# Implement minimal user creation endpoint
# Run test again
pytest tests/python/test_user_api.py::TestUserRegistration::test_create_user_success -v

# Expected: PASSED
```

### Phase 3: Refactor ♻️
Improve code quality while keeping tests green:

```bash
# Refactor implementation
# Run all related tests
pytest tests/python/test_user_api.py::TestUserRegistration -v

# Expected: All PASSED
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Python dependencies
pip install pytest pytest-asyncio httpx pytest-mock sqlalchemy[asyncio] asyncpg redis

# Go dependencies
cd go-service
go get github.com/stretchr/testify/assert
go get github.com/stretchr/testify/mock
go get github.com/stretchr/testify/suite
```

### 2. Start Test Infrastructure

```bash
# Start test database
docker run -d --name test-postgres \
  -e POSTGRES_DB=testdb \
  -e POSTGRES_USER=testuser \
  -e POSTGRES_PASSWORD=testpass \
  -p 5433:5432 \
  postgres:16-alpine

# Start test Redis
docker run -d --name test-redis \
  -p 6380:6379 \
  redis:8.2-alpine

# Verify connections
psql "postgresql://testuser:testpass@localhost:5433/testdb" -c "SELECT 1;"
redis-cli -p 6380 ping
```

### 3. Set Environment Variables

```bash
export TEST_DATABASE_URL="postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"
export TEST_REDIS_URL="redis://localhost:6380/0"
export GO_SERVICE_URL="http://localhost:8080"
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# End-to-end tests only
pytest -m e2e
```

### Run Specific Test Files
```bash
# Python API tests
pytest tests/python/

# Go service tests
cd go-service && go test ./tests/...

# Integration tests
pytest tests/integration/
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run with Verbose Output
```bash
pytest -v -s
```

## Test Implementation Order

Follow this order for TDD implementation:

### Week 1: Core User Management
1. `test_create_user_success` ✅
2. `test_create_user_duplicate_email` ✅
3. `test_get_user_by_id_success` ✅
4. `test_login_success` ✅

### Week 2: Job Management
1. `test_create_external_data_job_success` ✅
2. `test_get_job_status_queued` ✅
3. `test_get_job_status_completed` ✅
4. `test_get_user_jobs_with_jobs` ✅

### Week 3: Go Service Integration
1. `TestProcessJobRequest` ✅
2. `TestExternalAPIProcessing` ✅
3. `TestConcurrentJobProcessing` ✅
4. `test_complete_job_workflow` ✅

### Week 4: Advanced Features
1. `test_job_failure_handling` ✅
2. `test_concurrent_job_processing` ✅
3. `test_cancel_queued_job` ✅
4. `test_get_job_results_completed` ✅

## Test Data Management

### Fixtures Available

- `client`: HTTP client with database override
- `authenticated_user`: User with valid JWT token
- `test_user`: Basic user in database
- `mock_processing_job`: Job in processing state
- `mock_completed_job`: Job with results
- `mock_failed_job`: Job with error message

### Database Cleanup

Tests automatically clean up using transactions:
- Each test runs in a transaction
- Transaction is rolled back after test
- No manual cleanup needed

## Debugging Tests

### View SQL Queries
```bash
# Enable SQL logging in conftest.py
engine = create_async_engine(TEST_DATABASE_URL, echo=True)
```

### Debug Failing Tests
```bash
# Run single test with full output
pytest tests/python/test_user_api.py::test_create_user_success -v -s --tb=long

# Drop into debugger on failure
pytest --pdb tests/python/test_user_api.py::test_create_user_success
```

### Check Database State
```bash
# Connect to test database
psql "postgresql://testuser:testpass@localhost:5433/testdb"

# List tables
\dt

# Check users table
SELECT * FROM users;

# Check jobs table
SELECT * FROM jobs;
```

## Mock External Services

For unit tests, external services are mocked:

```python
@pytest.fixture
def mock_external_api(monkeypatch):
    """Mock external API calls."""
    # httpx calls are automatically mocked
    # Returns predictable test data
```

For integration tests, use real external services or test doubles.

## Performance Guidelines

### Test Speed Targets
- Unit tests: < 1 second each
- Integration tests: < 10 seconds each
- E2E tests: < 60 seconds each

### Optimization Tips
```bash
# Run tests in parallel
pytest -n auto

# Skip slow tests during development
pytest -m "not integration and not e2e"

# Use test database with faster settings
# (configured in conftest.py)
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
          POSTGRES_USER: testuser
        ports:
          - 5433:5432
      redis:
        image: redis:8.2-alpine
        ports:
          - 6380:6379
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - uses: actions/setup-go@v4
        with:
          go-version: '1.22'
      - run: pip install -r requirements.txt
      - run: pytest tests/python/
      - run: cd go-service && go test ./tests/...
```

## Test Coverage Goals

- **Unit Tests**: 90%+ code coverage
- **Integration Tests**: 80%+ API endpoint coverage
- **E2E Tests**: 100% critical user journey coverage

## Common Issues & Solutions

### Database Connection Errors
```bash
# Check if test database is running
docker ps | grep test-postgres

# Reset test database
docker stop test-postgres && docker rm test-postgres
# Then restart with setup commands
```

### Redis Connection Errors
```bash
# Check Redis
docker ps | grep test-redis
redis-cli -p 6380 ping
```

### Go Service Not Available
```bash
# Start Go service for integration tests
cd go-service
go run cmd/worker/main.go
```

### Tests Taking Too Long
```bash
# Run only fast tests during development
pytest -m unit

# Use parallel execution
pytest -n auto
```

## Contributing

When adding new tests:

1. **Follow TDD**: Write test first (red), then implementation (green), then refactor
2. **Use Descriptive Names**: `test_create_user_with_duplicate_email_fails`
3. **Test One Thing**: Each test should verify one specific behavior
4. **Use Fixtures**: Reuse common setup with pytest fixtures
5. **Add Docstrings**: Explain what the test verifies
6. **Mock External Deps**: Use mocks for unit tests, real services for integration

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Go Testing with Testify](https://github.com/stretchr/testify)
- [TDD Best Practices](https://martinfowler.com/articles/practical-test-pyramid.html)