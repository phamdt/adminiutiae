# End-to-End API Tests for TDD Implementation

## Overview
This test suite defines the expected behavior of the hybrid Go/Python microservices architecture. Use these tests to drive your implementation using the red-green-refactor TDD approach.

## Test Strategy

### Phase 1: Red Phase (Failing Tests)
1. Write tests first - they should fail
2. Run tests to confirm they fail for the right reasons
3. Don't implement any business logic yet

### Phase 2: Green Phase (Minimal Implementation)
1. Write minimal code to make tests pass
2. Focus on making tests green, not on perfect code
3. Avoid over-engineering

### Phase 3: Refactor Phase (Clean Code)
1. Improve code quality while keeping tests green
2. Extract functions, improve naming, optimize performance
3. Ensure tests still pass after each refactor

## Test Execution Order

1. **Unit Tests** - Test individual components
2. **Integration Tests** - Test service interactions
3. **End-to-End Tests** - Test complete user workflows
4. **Performance Tests** - Test under load

## Test Environment Setup

### Prerequisites
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx pytest-mock
go get github.com/stretchr/testify/assert
go get github.com/stretchr/testify/mock

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
```

### Test Configuration
```python
# tests/conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import get_db
from app.models.user import Base

TEST_DATABASE_URL = "postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```