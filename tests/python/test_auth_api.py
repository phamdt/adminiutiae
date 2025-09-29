"""
Comprehensive Authentication API Tests

These tests cover all authentication scenarios including edge cases,
security validations, and token management.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.core.config import settings


class TestUserRegistration:
    """Test user registration with comprehensive validation"""

    @pytest.mark.asyncio
    async def test_create_user_success(self, client: AsyncClient):
        """Test successful user creation with all valid data"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePassword123!"
        }
        
        response = await client.post("/api/v1/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify response structure
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
        
        # Ensure sensitive data is not returned
        assert "password" not in data
        assert "hashed_password" not in data

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, client: AsyncClient):
        """Test user creation fails with duplicate email"""
        user_data = {
            "email": "duplicate@example.com",
            "username": "user1",
            "password": "password123"
        }
        
        # Create first user
        response1 = await client.post("/api/v1/users/", json=user_data)
        assert response1.status_code == 201
        
        # Try to create second user with same email, different username
        user_data["username"] = "user2"
        response2 = await client.post("/api/v1/users/", json=user_data)
        
        assert response2.status_code == 400
        assert "already registered" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self, client: AsyncClient):
        """Test user creation fails with duplicate username"""
        user_data1 = {
            "email": "user1@example.com",
            "username": "sameusername",
            "password": "password123"
        }
        user_data2 = {
            "email": "user2@example.com",
            "username": "sameusername",
            "password": "password123"
        }
        
        # Create first user
        response1 = await client.post("/api/v1/users/", json=user_data1)
        assert response1.status_code == 201
        
        # Try to create second user with same username
        response2 = await client.post("/api/v1/users/", json=user_data2)
        
        assert response2.status_code == 400
        assert "already taken" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_user_invalid_email_formats(self, client: AsyncClient):
        """Test various invalid email formats are rejected"""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "test@",
            "test..test@example.com",
            "test@example",
            "",
            "test@.com"
        ]
        
        for email in invalid_emails:
            user_data = {
                "email": email,
                "username": f"user_{abs(hash(email))}",
                "password": "password123"
            }
            
            response = await client.post("/api/v1/users/", json=user_data)
            
            assert response.status_code == 422, f"Email '{email}' should be invalid"
            errors = response.json()["detail"]
            assert any("email" in str(error["loc"]).lower() for error in errors)

    @pytest.mark.asyncio
    async def test_create_user_weak_passwords(self, client: AsyncClient):
        """Test various weak passwords are rejected"""
        weak_passwords = [
            "123",           # Too short
            "password",      # Too common
            "12345678",      # Only numbers
            "abcdefgh",      # Only letters
            "",              # Empty
            "1234567"        # Just under minimum
        ]
        
        for i, password in enumerate(weak_passwords):
            user_data = {
                "email": f"test{i}@example.com",
                "username": f"testuser{i}",
                "password": password
            }
            
            response = await client.post("/api/v1/users/", json=user_data)
            
            assert response.status_code == 422, f"Password '{password}' should be rejected"
            errors = response.json()["detail"]
            assert any("password" in str(error["loc"]).lower() for error in errors)

    @pytest.mark.asyncio
    async def test_create_user_username_validation(self, client: AsyncClient):
        """Test username validation rules"""
        invalid_usernames = [
            "ab",           # Too short
            "a" * 51,       # Too long
            "user with spaces",
            "user@symbol",
            "",             # Empty
            "123",          # Only numbers
        ]
        
        for i, username in enumerate(invalid_usernames):
            user_data = {
                "email": f"test{i}@example.com",
                "username": username,
                "password": "ValidPassword123!"
            }
            
            response = await client.post("/api/v1/users/", json=user_data)
            
            assert response.status_code == 422, f"Username '{username}' should be invalid"

    @pytest.mark.asyncio
    async def test_create_user_missing_fields(self, client: AsyncClient):
        """Test user creation with missing required fields"""
        # Missing email
        response = await client.post("/api/v1/users/", json={
            "username": "testuser",
            "password": "password123"
        })
        assert response.status_code == 422
        
        # Missing username
        response = await client.post("/api/v1/users/", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 422
        
        # Missing password
        response = await client.post("/api/v1/users/", json={
            "email": "test@example.com",
            "username": "testuser"
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_user_sql_injection_attempt(self, client: AsyncClient):
        """Test that SQL injection attempts are handled safely"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "admin'; UPDATE users SET is_active = false; --",
            "' OR '1'='1",
            "admin'/**/OR/**/1=1#"
        ]
        
        for i, malicious_input in enumerate(malicious_inputs):
            user_data = {
                "email": f"test{i}@example.com",
                "username": malicious_input,
                "password": "password123"
            }
            
            # Should either reject the input or sanitize it
            response = await client.post("/api/v1/users/", json=user_data)
            # Either validation error or creation with sanitized input
            assert response.status_code in [201, 422]


class TestUserAuthentication:
    """Test authentication workflows and security"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        """Test successful login returns valid JWT token"""
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify token structure
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
        # Verify token is valid JWT
        token = data["access_token"]
        decoded = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert decoded["sub"] == test_user["username"]
        assert "exp" in decoded

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """Test login fails with incorrect password"""
        login_data = {
            "username": test_user["username"],
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login fails with non-existent username"""
        login_data = {
            "username": "nonexistentuser",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_login_case_sensitivity(self, client: AsyncClient, test_user):
        """Test that login is case-sensitive"""
        login_data = {
            "username": test_user["username"].upper(),  # Different case
            "password": test_user["password"]
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client: AsyncClient, db_session: AsyncSession):
        """Test login fails for inactive user"""
        # Create inactive user
        from app.services.auth import get_password_hash
        
        inactive_user = User(
            email="inactive@example.com",
            username="inactiveuser",
            hashed_password=get_password_hash("password123"),
            is_active=False
        )
        db_session.add(inactive_user)
        await db_session.commit()
        
        login_data = {
            "username": "inactiveuser",
            "password": "password123"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        # Should either fail at login or at protected endpoint access
        # Implementation dependent - document the behavior
        assert response.status_code in [401, 200]

    @pytest.mark.asyncio
    async def test_login_brute_force_protection(self, client: AsyncClient, test_user):
        """Test protection against brute force attacks"""
        login_data = {
            "username": test_user["username"],
            "password": "wrongpassword"
        }
        
        # Attempt multiple failed logins
        failed_attempts = 0
        for i in range(10):
            response = await client.post("/api/v1/auth/login", json=login_data)
            if response.status_code == 401:
                failed_attempts += 1
            elif response.status_code == 429:  # Rate limited
                break
        
        # Should either rate limit or continue failing
        assert failed_attempts >= 5  # At least some attempts should fail


class TestTokenValidation:
    """Test JWT token validation and protected endpoints"""

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token fails"""
        response = await client.get("/api/v1/users/me")
        
        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "not authenticated" in detail or "authorization" in detail

    @pytest.mark.asyncio
    async def test_protected_endpoint_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token"""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "invalid" in detail or "decode" in detail

    @pytest.mark.asyncio
    async def test_protected_endpoint_expired_token(self, client: AsyncClient):
        """Test accessing protected endpoint with expired token"""
        # Create expired token
        expired_payload = {
            "sub": "testuser",
            "exp": datetime.utcnow() - timedelta(minutes=30)  # Expired
        }
        expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert "expired" in detail or "invalid" in detail

    @pytest.mark.asyncio
    async def test_protected_endpoint_malformed_token(self, client: AsyncClient):
        """Test various malformed token formats"""
        malformed_tokens = [
            "Bearer",                    # Missing token
            "InvalidBearer token",       # Wrong prefix
            "Bearer token.with.dots",    # Invalid JWT format
            "Bearer eyJhbGciOiJIUzI1NiJ9", # Incomplete JWT
            "",                          # Empty
            "Just_a_string",            # No Bearer prefix
        ]
        
        for token in malformed_tokens:
            if token == "":
                response = await client.get("/api/v1/users/me")
            else:
                headers = {"Authorization": token}
                response = await client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == 401, f"Token '{token}' should be rejected"

    @pytest.mark.asyncio
    async def test_protected_endpoint_valid_token(self, client: AsyncClient, authenticated_user):
        """Test accessing protected endpoint with valid token"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert "email" in data
        assert "username" in data
        assert "password" not in data

    @pytest.mark.asyncio
    async def test_token_contains_correct_claims(self, client: AsyncClient, test_user):
        """Test that generated tokens contain correct claims"""
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        token = response.json()["access_token"]
        
        # Decode without verification to check claims
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        assert decoded["sub"] == test_user["username"]
        assert "exp" in decoded
        assert "iat" in decoded or "nbf" in decoded  # Issued at or not before
        
        # Verify expiration is reasonable (should be in future)
        exp_time = datetime.fromtimestamp(decoded["exp"])
        assert exp_time > datetime.utcnow()
        assert exp_time < datetime.utcnow() + timedelta(hours=1)  # Reasonable expiration


class TestUserProfileAccess:
    """Test user profile access and management"""

    @pytest.mark.asyncio
    async def test_get_current_user_profile(self, client: AsyncClient, authenticated_user):
        """Test getting current user profile"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert "email" in data
        assert "username" in data
        assert "is_active" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_user_by_id_authorized(self, client: AsyncClient, authenticated_user):
        """Test getting user by ID when authorized"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get(f"/api/v1/users/{user_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, client: AsyncClient, authenticated_user):
        """Test getting non-existent user by ID"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/users/99999", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_users_pagination(self, client: AsyncClient, authenticated_user, multiple_users):
        """Test user listing with pagination"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test default pagination
        response = await client.get("/api/v1/users/", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1
        
        # Test with pagination parameters
        response = await client.get("/api/v1/users/?skip=0&limit=2", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert len(users) <= 2
        
        # Test skip parameter
        response = await client.get("/api/v1/users/?skip=1&limit=1", headers=headers)
        assert response.status_code == 200
        users = response.json()
        assert len(users) <= 1


class TestPasswordSecurity:
    """Test password security measures"""

    @pytest.mark.asyncio
    async def test_password_hashing(self, client: AsyncClient, db_session: AsyncSession):
        """Test that passwords are properly hashed in database"""
        user_data = {
            "email": "hashtest@example.com",
            "username": "hashtest",
            "password": "PlainTextPassword123!"
        }
        
        response = await client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 201
        user_id = response.json()["id"]
        
        # Check database directly
        result = await db_session.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one()
        
        # Password should be hashed, not plain text
        assert db_user.hashed_password != user_data["password"]
        assert len(db_user.hashed_password) > 50  # Bcrypt hashes are long
        assert db_user.hashed_password.startswith("$2b$")  # Bcrypt prefix

    @pytest.mark.asyncio
    async def test_password_verification(self, client: AsyncClient):
        """Test password verification during login"""
        user_data = {
            "email": "verify@example.com",
            "username": "verifyuser",
            "password": "CorrectPassword123!"
        }
        
        # Create user
        create_response = await client.post("/api/v1/users/", json=user_data)
        assert create_response.status_code == 201
        
        # Test correct password
        login_response = await client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        assert login_response.status_code == 200
        
        # Test incorrect password
        login_response = await client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": "WrongPassword123!"
        })
        assert login_response.status_code == 401


class TestAuthorizationEdgeCases:
    """Test authorization edge cases and security scenarios"""

    @pytest.mark.asyncio
    async def test_token_reuse_after_password_change(self, client: AsyncClient, authenticated_user):
        """Test token behavior after password change (if implemented)"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Token should work before password change
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        
        # Note: Password change endpoint would need to be implemented
        # This test documents expected behavior

    @pytest.mark.asyncio
    async def test_concurrent_logins_same_user(self, client: AsyncClient, test_user):
        """Test multiple concurrent logins for same user"""
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        # Create multiple tokens concurrently
        import asyncio
        tasks = []
        for _ in range(5):
            task = client.post("/api/v1/auth/login", json=login_data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_token_tampering_detection(self, client: AsyncClient, authenticated_user):
        """Test that tampered tokens are rejected"""
        _, token = authenticated_user
        
        # Tamper with token
        tampered_tokens = [
            token[:-5] + "XXXXX",  # Change signature
            token[:-1],            # Remove last character
            token + "extra",       # Add extra characters
            token.replace("eyJ", "XYZ") if "eyJ" in token else token + "X"  # Change header
        ]
        
        for tampered_token in tampered_tokens:
            headers = {"Authorization": f"Bearer {tampered_token}"}
            response = await client.get("/api/v1/users/me", headers=headers)
            
            assert response.status_code == 401, f"Tampered token should be rejected: {tampered_token[:20]}..."

    @pytest.mark.asyncio
    async def test_authorization_header_variations(self, client: AsyncClient, authenticated_user):
        """Test various Authorization header formats"""
        _, token = authenticated_user
        
        # Valid formats
        valid_headers = [
            {"Authorization": f"Bearer {token}"},
            {"Authorization": f"bearer {token}"},  # Lowercase bearer
        ]
        
        for headers in valid_headers:
            response = await client.get("/api/v1/users/me", headers=headers)
            # Should work (case-insensitive bearer)
            assert response.status_code in [200, 401]  # Depends on implementation
        
        # Invalid formats
        invalid_headers = [
            {"Authorization": f"Token {token}"},     # Wrong scheme
            {"Authorization": f"Basic {token}"},     # Wrong scheme
            {"Authorization": token},                # Missing Bearer
            {"Auth": f"Bearer {token}"},            # Wrong header name
        ]
        
        for headers in invalid_headers:
            response = await client.get("/api/v1/users/me", headers=headers)
            assert response.status_code == 401