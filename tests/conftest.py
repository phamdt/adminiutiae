"""
Pytest configuration and shared fixtures for all tests.
This file contains test setup, database fixtures, and authentication helpers.
"""
import pytest
import asyncio
import os
from typing import Tuple, AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis

# Import your app components
from app.main import app
from app.db.database import get_db
from app.models.user import Base as UserBase
from app.models.job import Base as JobBase


# Test configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://testuser:testpass@localhost:5433/testdb"
)
TEST_REDIS_URL = os.getenv(
    "TEST_REDIS_URL", 
    "redis://localhost:6380/0"
)
GO_SERVICE_URL = os.getenv(
    "GO_SERVICE_URL",
    "http://localhost:8080"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine and setup tables."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,  # Set to True for SQL debugging
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(JobBase.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(UserBase.metadata.drop_all)
        await conn.run_sync(JobBase.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for each test."""
    async_session = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        # Start a transaction
        await session.begin()
        
        try:
            yield session
        finally:
            # Rollback the transaction to clean up
            await session.rollback()


@pytest.fixture
async def redis_client():
    """Create Redis client for tests."""
    client = redis.from_url(TEST_REDIS_URL, decode_responses=True)
    yield client
    await client.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create HTTP client with database dependency override."""
    
    # Override the database dependency
    app.dependency_overrides[get_db] = lambda: db_session
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> dict:
    """Create a test user in the database."""
    from app.models.user import User
    from app.services.auth import get_password_hash
    
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": get_password_hash("testpassword123"),
        "is_active": True
    }
    
    user = User(**user_data)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "password": "testpassword123"  # Plain password for login tests
    }


@pytest.fixture
async def authenticated_user(client: AsyncClient, test_user: dict) -> Tuple[int, str]:
    """Create an authenticated user and return user_id and token."""
    
    # Login to get token
    login_data = {
        "username": test_user["username"],
        "password": test_user["password"]
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    user_id = test_user["id"]
    
    return user_id, token


@pytest.fixture
async def multiple_users(db_session: AsyncSession) -> list:
    """Create multiple test users."""
    from app.models.user import User
    from app.services.auth import get_password_hash
    
    users = []
    for i in range(5):
        user_data = {
            "email": f"user{i}@example.com",
            "username": f"user{i}",
            "hashed_password": get_password_hash(f"password{i}"),
            "is_active": True
        }
        
        user = User(**user_data)
        db_session.add(user)
        users.append(user_data)
    
    await db_session.commit()
    return users


@pytest.fixture
async def mock_processing_job(db_session: AsyncSession, test_user: dict) -> int:
    """Create a mock job in processing status."""
    from app.models.job import Job
    import json
    
    job_data = {
        "user_id": test_user["id"],
        "job_type": "external_data",
        "status": "processing",
        "parameters": json.dumps({
            "data_sources": ["api1", "api2"],
            "filters": {"test": True}
        })
    }
    
    job = Job(**job_data)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    return job.id


@pytest.fixture
async def mock_completed_job(db_session: AsyncSession, test_user: dict) -> int:
    """Create a mock job in completed status with results."""
    from app.models.job import Job
    import json
    from datetime import datetime
    
    job_data = {
        "user_id": test_user["id"],
        "job_type": "external_data",
        "status": "completed",
        "parameters": json.dumps({
            "data_sources": ["api1", "api2"],
            "filters": {"test": True}
        }),
        "result": json.dumps({
            "api_results": [
                {"source": "api1", "data": {"title": "Test 1"}, "status": "success"},
                {"source": "api2", "data": {"title": "Test 2"}, "status": "success"}
            ],
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "total_items": 2
            }
        })
    }
    
    job = Job(**job_data)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    return job.id


@pytest.fixture
async def mock_failed_job(db_session: AsyncSession, test_user: dict) -> int:
    """Create a mock job in failed status with error message."""
    from app.models.job import Job
    import json
    
    job_data = {
        "user_id": test_user["id"],
        "job_type": "external_data",
        "status": "failed",
        "parameters": json.dumps({
            "data_sources": ["invalid_api"],
            "filters": {}
        }),
        "error_message": "Failed to connect to external API: Connection timeout"
    }
    
    job = Job(**job_data)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    
    return job.id


@pytest.fixture
def go_service_url() -> str:
    """Return Go service URL for integration tests."""
    return GO_SERVICE_URL


# Pytest markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast)"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (slow)"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests (slowest)"
    )


# Pytest collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ["integration", "e2e"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Custom assertions for API testing
class APIAssertions:
    """Custom assertions for API testing."""
    
    @staticmethod
    def assert_job_response_structure(response_data: dict):
        """Assert that job response has correct structure."""
        required_fields = ["id", "status", "job_type", "user_id", "created_at"]
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
        
        assert response_data["status"] in ["queued", "processing", "completed", "failed", "cancelled"]
        assert isinstance(response_data["id"], int)
        assert isinstance(response_data["user_id"], int)
    
    @staticmethod
    def assert_user_response_structure(response_data: dict):
        """Assert that user response has correct structure."""
        required_fields = ["id", "email", "username", "is_active", "created_at"]
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
        
        # Ensure password is not included
        assert "password" not in response_data
        assert "hashed_password" not in response_data
        
        assert isinstance(response_data["id"], int)
        assert isinstance(response_data["is_active"], bool)


@pytest.fixture
def api_assertions():
    """Provide API assertions helper."""
    return APIAssertions()


# Database cleanup utilities
@pytest.fixture
async def clean_database(db_session: AsyncSession):
    """Clean database after test."""
    yield
    
    # Clean up all tables
    from app.models.job import Job
    from app.models.user import User
    
    await db_session.execute("DELETE FROM jobs")
    await db_session.execute("DELETE FROM users")
    await db_session.commit()


# Mock external services
@pytest.fixture
def mock_external_api(monkeypatch):
    """Mock external API calls for testing."""
    import httpx
    from unittest.mock import AsyncMock
    
    async def mock_get(*args, **kwargs):
        """Mock httpx.get calls."""
        response = AsyncMock()
        response.status_code = 200
        response.json.return_value = {"mocked": True, "data": "test"}
        return response
    
    async def mock_post(*args, **kwargs):
        """Mock httpx.post calls."""
        response = AsyncMock()
        response.status_code = 200
        response.json.return_value = {"status": "accepted", "job_id": 1}
        return response
    
    # Patch httpx methods
    monkeypatch.setattr("httpx.get", mock_get)
    monkeypatch.setattr("httpx.post", mock_post)
    
    # For AsyncClient context manager
    class MockAsyncClient:
        async def __aenter__(self):
            return self
        
        async def __aexit__(self, *args):
            pass
        
        async def get(self, *args, **kwargs):
            return await mock_get(*args, **kwargs)
        
        async def post(self, *args, **kwargs):
            return await mock_post(*args, **kwargs)
    
    monkeypatch.setattr("httpx.AsyncClient", MockAsyncClient)


# Environment setup
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up test environment variables."""
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["REDIS_URL"] = TEST_REDIS_URL
    
    yield
    
    # Cleanup
    if "TESTING" in os.environ:
        del os.environ["TESTING"]