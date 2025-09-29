"""
End-to-End Complete Workflow Tests

These tests verify the entire system workflow from user registration
to job completion, ensuring all components work together correctly.
"""
import pytest
import asyncio
import json
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


class TestCompleteUserJourney:
    """Test complete user journey from registration to job completion"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_user_workflow(self, client: AsyncClient):
        """Test complete workflow: register → login → create job → check status → get results"""
        
        # Step 1: Register new user
        user_data = {
            "email": "journey@example.com",
            "username": "journeyuser",
            "password": "SecurePassword123!"
        }
        
        register_response = await client.post("/api/v1/users/", json=user_data)
        assert register_response.status_code == 201
        
        user = register_response.json()
        user_id = user["id"]
        assert user["email"] == user_data["email"]
        assert user["username"] == user_data["username"]
        
        # Step 2: Login to get token
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"]
        }
        
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        token_data = login_response.json()
        token = token_data["access_token"]
        assert token_data["token_type"] == "bearer"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Verify authentication works
        profile_response = await client.get("/api/v1/users/me", headers=headers)
        assert profile_response.status_code == 200
        
        profile = profile_response.json()
        assert profile["id"] == user_id
        assert profile["email"] == user_data["email"]
        
        # Step 4: Create external data job
        job_data = {
            "data_sources": [
                "https://jsonplaceholder.typicode.com/posts/1",
                "https://jsonplaceholder.typicode.com/users/1"
            ],
            "filters": {
                "category": "e2e_test",
                "priority": "high"
            }
        }
        
        # Mock Go service response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "accepted", "job_id": 1}
            mock_post.return_value = mock_response
            
            job_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        assert job_response.status_code == 202
        
        job_result = job_response.json()
        job_id = job_result["job_id"]
        assert job_result["status"] == "queued"
        assert isinstance(job_id, int)
        
        # Step 5: Check job status
        status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert status_response.status_code == 200
        
        job_status = status_response.json()
        assert job_status["id"] == job_id
        assert job_status["user_id"] == user_id
        assert job_status["job_type"] == "external_data"
        assert job_status["status"] in ["queued", "processing"]
        
        # Step 6: List user jobs
        jobs_response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        assert jobs_response.status_code == 200
        
        user_jobs = jobs_response.json()
        assert isinstance(user_jobs, list)
        assert len(user_jobs) >= 1
        
        # Find our job in the list
        our_job = next((job for job in user_jobs if job["id"] == job_id), None)
        assert our_job is not None
        assert our_job["job_type"] == "external_data"

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_job_lifecycle_with_cancellation(self, client: AsyncClient):
        """Test job lifecycle including cancellation"""
        
        # Register and login
        user_data = {
            "email": "cancel@example.com",
            "username": "canceluser",
            "password": "CancelPassword123!"
        }
        
        register_response = await client.post("/api/v1/users/", json=user_data)
        user_id = register_response.json()["id"]
        
        login_response = await client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create job
        job_data = {
            "data_sources": ["https://slow-api.example.com/data"],
            "filters": {"cancellation_test": True}
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            job_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        job_id = job_response.json()["job_id"]
        
        # Verify job is created
        status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["status"] in ["queued", "processing"]
        
        # Cancel the job
        cancel_response = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        assert cancel_response.status_code == 200
        
        cancel_result = cancel_response.json()
        assert cancel_result["status"] == "cancelled"
        assert cancel_result["job_id"] == job_id
        
        # Verify job is cancelled
        final_status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert final_status_response.status_code == 200
        assert final_status_response.json()["status"] == "cancelled"

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multiple_users_concurrent_operations(self, client: AsyncClient):
        """Test multiple users performing operations concurrently"""
        
        # Create multiple users concurrently
        user_tasks = []
        for i in range(5):
            user_data = {
                "email": f"multiuser{i}@example.com",
                "username": f"multiuser{i}",
                "password": f"Password{i}123!"
            }
            task = client.post("/api/v1/users/", json=user_data)
            user_tasks.append((task, user_data))
        
        # Wait for all users to be created
        users_info = []
        for task, user_data in user_tasks:
            response = await task
            assert response.status_code == 201
            user = response.json()
            users_info.append((user["id"], user_data))
        
        # Login all users concurrently
        login_tasks = []
        for user_id, user_data in users_info:
            login_data = {
                "username": user_data["username"],
                "password": user_data["password"]
            }
            task = client.post("/api/v1/auth/login", json=login_data)
            login_tasks.append((task, user_id))
        
        # Get all tokens
        user_tokens = []
        for task, user_id in login_tasks:
            response = await task
            assert response.status_code == 200
            token = response.json()["access_token"]
            user_tokens.append((user_id, token))
        
        # Each user creates multiple jobs concurrently
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            all_job_tasks = []
            for user_id, token in user_tokens:
                headers = {"Authorization": f"Bearer {token}"}
                
                # Each user creates 3 jobs
                for j in range(3):
                    job_data = {
                        "data_sources": [f"https://api{user_id}-{j}.example.com/data"],
                        "filters": {"user": user_id, "job": j}
                    }
                    
                    task = client.post(
                        f"/api/v1/users/{user_id}/external-data",
                        json=job_data,
                        headers=headers
                    )
                    all_job_tasks.append((task, user_id, j))
            
            # Wait for all jobs to be created
            job_results = []
            for task, user_id, job_index in all_job_tasks:
                response = await task
                assert response.status_code == 202
                job_results.append((response.json()["job_id"], user_id, job_index))
        
        # Verify each user can see their own jobs
        for user_id, token in user_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            
            jobs_response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
            assert jobs_response.status_code == 200
            
            user_jobs = jobs_response.json()
            user_job_count = len([job for job in user_jobs if job["user_id"] == user_id])
            assert user_job_count >= 3, f"User {user_id} should have at least 3 jobs"

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, client: AsyncClient):
        """Test system behavior and recovery from various error conditions"""
        
        # Create user and login
        user_data = {
            "email": "errortest@example.com",
            "username": "erroruser",
            "password": "ErrorPassword123!"
        }
        
        register_response = await client.post("/api/v1/users/", json=user_data)
        user_id = register_response.json()["id"]
        
        login_response = await client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Job creation with Go service error
        job_data = {
            "data_sources": ["https://api.example.com/data"],
            "filters": {"error_test": "go_service_error"}
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 500  # Go service error
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response
            
            job_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        # Should still create job even if Go service fails
        assert job_response.status_code == 202
        failed_job_id = job_response.json()["job_id"]
        
        # Test 2: Job creation with timeout
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            timeout_job_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        # Should handle timeout gracefully
        assert timeout_job_response.status_code == 202
        timeout_job_id = timeout_job_response.json()["job_id"]
        
        # Test 3: Verify system continues to work after errors
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            recovery_job_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        # Should work normally after errors
        assert recovery_job_response.status_code == 202
        recovery_job_id = recovery_job_response.json()["job_id"]
        
        # Verify all jobs are tracked
        jobs_response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        user_jobs = jobs_response.json()
        job_ids = [job["id"] for job in user_jobs]
        
        assert failed_job_id in job_ids
        assert timeout_job_id in job_ids
        assert recovery_job_id in job_ids

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_authentication_edge_cases_workflow(self, client: AsyncClient):
        """Test authentication edge cases in complete workflow"""
        
        # Create user
        user_data = {
            "email": "authtest@example.com",
            "username": "authuser",
            "password": "AuthPassword123!"
        }
        
        register_response = await client.post("/api/v1/users/", json=user_data)
        user_id = register_response.json()["id"]
        
        # Get valid token
        login_response = await client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        valid_token = login_response.json()["access_token"]
        valid_headers = {"Authorization": f"Bearer {valid_token}"}
        
        # Test 1: Use expired token (simulated)
        expired_headers = {"Authorization": "Bearer expired.token.here"}
        
        expired_response = await client.get(f"/api/v1/users/{user_id}", headers=expired_headers)
        assert expired_response.status_code == 401
        
        # Test 2: Use malformed token
        malformed_headers = {"Authorization": "Bearer malformed_token"}
        
        malformed_response = await client.get(f"/api/v1/users/{user_id}", headers=malformed_headers)
        assert malformed_response.status_code == 401
        
        # Test 3: No authorization header
        no_auth_response = await client.get(f"/api/v1/users/{user_id}")
        assert no_auth_response.status_code == 401
        
        # Test 4: Valid token should still work
        valid_response = await client.get(f"/api/v1/users/{user_id}", headers=valid_headers)
        assert valid_response.status_code == 200
        
        # Test 5: Try to access another user's data
        other_user_response = await client.get(f"/api/v1/users/{user_id + 1000}", headers=valid_headers)
        # Should either be not found or forbidden
        assert other_user_response.status_code in [404, 403]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_job_data_integrity_workflow(self, client: AsyncClient):
        """Test job data integrity throughout the complete workflow"""
        
        # Setup user and authentication
        user_data = {
            "email": "integrity@example.com",
            "username": "integrityuser",
            "password": "IntegrityPassword123!"
        }
        
        register_response = await client.post("/api/v1/users/", json=user_data)
        user_id = register_response.json()["id"]
        
        login_response = await client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create job with complex data
        complex_job_data = {
            "data_sources": [
                "https://api1.example.com/users",
                "https://api2.example.com/posts",
                "https://api3.example.com/comments"
            ],
            "filters": {
                "date_range": "2023-01-01 to 2023-12-31",
                "categories": ["tech", "science", "business"],
                "pagination": {
                    "page": 1,
                    "limit": 100,
                    "sort": "created_at",
                    "order": "desc"
                },
                "nested_filters": {
                    "user_preferences": {
                        "language": "en",
                        "timezone": "UTC",
                        "format": "json"
                    }
                },
                "boolean_flags": {
                    "include_metadata": True,
                    "exclude_deleted": True,
                    "compress_response": False
                }
            }
        }
        
        # Mock Go service to return specific data
        expected_result = {
            "api_results": [
                {
                    "source": "https://api1.example.com/users",
                    "data": {"users": [{"id": 1, "name": "John"}]},
                    "status": "success"
                },
                {
                    "source": "https://api2.example.com/posts",
                    "data": {"posts": [{"id": 1, "title": "Test Post"}]},
                    "status": "success"
                }
            ],
            "metadata": {
                "processed_at": "2023-01-01T00:00:00Z",
                "total_sources": 3,
                "successful_calls": 2
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            job_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=complex_job_data,
                headers=headers
            )
        
        job_id = job_response.json()["job_id"]
        
        # Simulate job completion by updating database directly
        # (In real scenario, Go service would do this)
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import select, update
        from app.models.job import Job
        
        engine = create_async_engine("postgresql+asyncpg://testuser:testpass@localhost:5433/testdb")
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Update job to completed with results
            await session.execute(
                update(Job)
                .where(Job.id == job_id)
                .values(
                    status="completed",
                    result=json.dumps(expected_result)
                )
            )
            await session.commit()
        
        await engine.dispose()
        
        # Verify job completion
        final_status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert final_status_response.status_code == 200
        
        final_job = final_status_response.json()
        assert final_job["status"] == "completed"
        assert final_job["result"] == expected_result
        
        # Test job results endpoint
        results_response = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        assert results_response.status_code == 200
        
        results_data = results_response.json()
        assert "results" in results_data
        assert "metadata" in results_data
        assert results_data["results"] == expected_result

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_high_load_complete_workflow(self, client: AsyncClient):
        """Test complete workflow under high load conditions"""
        
        # Create multiple users
        users = []
        for i in range(10):
            user_data = {
                "email": f"loadtest{i}@example.com",
                "username": f"loaduser{i}",
                "password": f"LoadPassword{i}123!"
            }
            
            register_response = await client.post("/api/v1/users/", json=user_data)
            assert register_response.status_code == 201
            
            login_response = await client.post("/api/v1/auth/login", json={
                "username": user_data["username"],
                "password": user_data["password"]
            })
            assert login_response.status_code == 200
            
            users.append({
                "id": register_response.json()["id"],
                "token": login_response.json()["access_token"]
            })
        
        # Each user creates multiple jobs concurrently
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            all_tasks = []
            for user in users:
                headers = {"Authorization": f"Bearer {user['token']}"}
                
                for j in range(5):  # 5 jobs per user = 50 total jobs
                    job_data = {
                        "data_sources": [f"https://api{user['id']}-{j}.example.com/data"],
                        "filters": {"load_test": True, "user": user["id"], "job": j}
                    }
                    
                    task = client.post(
                        f"/api/v1/users/{user['id']}/external-data",
                        json=job_data,
                        headers=headers
                    )
                    all_tasks.append(task)
            
            # Execute all job creations concurrently
            start_time = asyncio.get_event_loop().time()
            responses = await asyncio.gather(*all_tasks)
            end_time = asyncio.get_event_loop().time()
        
        # Verify all jobs were created successfully
        successful_jobs = sum(1 for r in responses if r.status_code == 202)
        total_time = end_time - start_time
        
        assert successful_jobs == 50, f"Only {successful_jobs}/50 jobs created successfully"
        assert total_time < 10.0, f"High load job creation took too long: {total_time:.2f}s"
        
        # Verify each user can still access their jobs
        for user in users:
            headers = {"Authorization": f"Bearer {user['token']}"}
            
            jobs_response = await client.get(f"/api/v1/users/{user['id']}/jobs", headers=headers)
            assert jobs_response.status_code == 200
            
            user_jobs = jobs_response.json()
            user_job_ids = [job["id"] for job in user_jobs if job["user_id"] == user["id"]]
            assert len(user_job_ids) >= 5, f"User {user['id']} missing jobs after high load"

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_data_consistency_across_operations(self, client: AsyncClient):
        """Test data consistency across multiple operations"""
        
        # Create user
        user_data = {
            "email": "consistency@example.com",
            "username": "consistencyuser",
            "password": "ConsistencyPassword123!"
        }
        
        register_response = await client.post("/api/v1/users/", json=user_data)
        user_id = register_response.json()["id"]
        
        login_response = await client.post("/api/v1/auth/login", json={
            "username": user_data["username"],
            "password": user_data["password"]
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple jobs with tracking data
        job_tracking = []
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            for i in range(10):
                job_data = {
                    "data_sources": [f"https://consistency-api{i}.example.com/data"],
                    "filters": {
                        "consistency_test": True,
                        "sequence_number": i,
                        "timestamp": f"2023-01-{i+1:02d}T00:00:00Z"
                    }
                }
                
                job_response = await client.post(
                    f"/api/v1/users/{user_id}/external-data",
                    json=job_data,
                    headers=headers
                )
                
                assert job_response.status_code == 202
                job_id = job_response.json()["job_id"]
                job_tracking.append({
                    "id": job_id,
                    "sequence": i,
                    "expected_data": job_data
                })
        
        # Verify data consistency across multiple status checks
        for _ in range(3):  # Check multiple times
            for job_info in job_tracking:
                status_response = await client.get(f"/api/v1/jobs/{job_info['id']}", headers=headers)
                assert status_response.status_code == 200
                
                job_status = status_response.json()
                assert job_status["id"] == job_info["id"]
                assert job_status["user_id"] == user_id
                assert job_status["job_type"] == "external_data"
                
                # Parameters should be preserved
                if job_status.get("parameters"):
                    # Would need to implement parameter retrieval in API
                    pass
            
            await asyncio.sleep(0.1)  # Small delay between checks
        
        # Verify job list consistency
        jobs_list_response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        assert jobs_list_response.status_code == 200
        
        all_jobs = jobs_list_response.json()
        tracked_job_ids = [job_info["id"] for job_info in job_tracking]
        
        for job_id in tracked_job_ids:
            assert any(job["id"] == job_id for job in all_jobs), f"Job {job_id} missing from job list"