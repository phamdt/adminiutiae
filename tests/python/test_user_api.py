"""
End-to-End Tests for User Management API

These tests define the expected behavior for user-related operations.
Run these tests first (they will fail), then implement the features to make them pass.
"""
import pytest
import json
from httpx import AsyncClient
from app.main import app


class TestUserRegistration:
    """Test user registration workflow"""

    @pytest.mark.asyncio
    async def test_create_user_success(self, client: AsyncClient):
        """Test successful user creation"""
        user_data = {
            "email": "john.doe@example.com",
            "username": "johndoe",
            "password": "securepassword123"
        }
        
        response = await client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "password" not in data  # Password should not be returned
        assert "id" in data
        assert data["is_active"] is True
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, client: AsyncClient):
        """Test user creation with duplicate email fails"""
        user_data = {
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "password123"
        }
        
        # Create first user
        response1 = await client.post("/api/v1/users/", json=user_data)
        assert response1.status_code == 201
        
        # Try to create second user with same email
        user_data["username"] = "user2"
        response2 = await client.post("/api/v1/users/", json=user_data)
        
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, client: AsyncClient):
        """Test user creation with duplicate username fails"""
        user_data1 = {
            "email": "user1@example.com",
            "username": "duplicateuser",
            "password": "password123"
        }
        user_data2 = {
            "email": "user2@example.com",
            "username": "duplicateuser",
            "password": "password123"
        }
        
        # Create first user
        response1 = await client.post("/api/v1/users/", json=user_data1)
        assert response1.status_code == 201
        
        # Try to create second user with same username
        response2 = await client.post("/api/v1/users/", json=user_data2)
        
        assert response2.status_code == 400
        assert "username" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_invalid_email(self, client: AsyncClient):
        """Test user creation with invalid email fails"""
        user_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("email" in error["loc"] for error in errors)

    @pytest.mark.asyncio
    async def test_create_user_weak_password(self, client: AsyncClient):
        """Test user creation with weak password fails"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "123"  # Too short
        }
        
        response = await client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 422
        assert "password" in response.json()["detail"][0]["loc"]


class TestUserRetrieval:
    """Test user retrieval operations"""

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, client: AsyncClient):
        """Test successful user retrieval by ID"""
        # Create a user first
        user_data = {
            "email": "getuser@example.com",
            "username": "getuser",
            "password": "password123"
        }
        create_response = await client.post("/api/v1/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Get the user
        response = await client.get(f"/api/v1/users/{user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, client: AsyncClient):
        """Test user retrieval with non-existent ID"""
        response = await client.get("/api/v1/users/99999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_user_by_id_invalid_id(self, client: AsyncClient):
        """Test user retrieval with invalid ID format"""
        response = await client.get("/api/v1/users/invalid")
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient):
        """Test listing users with pagination"""
        # Create multiple users
        users = []
        for i in range(5):
            user_data = {
                "email": f"user{i}@example.com",
                "username": f"user{i}",
                "password": "password123"
            }
            response = await client.post("/api/v1/users/", json=user_data)
            users.append(response.json())
        
        # Test default listing
        response = await client.get("/api/v1/users/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5
        assert all("password" not in user for user in data)

    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self, client: AsyncClient):
        """Test user listing with pagination parameters"""
        response = await client.get("/api/v1/users/?skip=0&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2


class TestUserAuthentication:
    """Test user authentication"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """Test successful user login"""
        # Create a user first
        user_data = {
            "email": "login@example.com",
            "username": "loginuser",
            "password": "password123"
        }
        await client.post("/api/v1/users/", json=user_data)
        
        # Login
        login_data = {
            "username": "loginuser",
            "password": "password123"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient):
        """Test login with wrong password"""
        # Create a user first
        user_data = {
            "email": "wrongpass@example.com",
            "username": "wrongpassuser",
            "password": "correctpassword"
        }
        await client.post("/api/v1/users/", json=user_data)
        
        # Try to login with wrong password
        login_data = {
            "username": "wrongpassuser",
            "password": "wrongpassword"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user"""
        login_data = {
            "username": "nonexistent",
            "password": "password123"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token"""
        response = await client.get("/api/v1/users/me")
        
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_valid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with valid token"""
        # Create and login user
        user_data = {
            "email": "protected@example.com",
            "username": "protecteduser",
            "password": "password123"
        }
        create_response = await client.post("/api/v1/users/", json=user_data)
        
        login_data = {
            "username": "protecteduser",
            "password": "password123"
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "protecteduser"
        assert data["email"] == "protected@example.com"

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() or "decode" in response.json()["detail"].lower()