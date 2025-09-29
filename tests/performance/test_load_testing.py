"""
Performance and Load Tests

These tests verify the system can handle high load scenarios
and concurrent operations efficiently.
"""
import pytest
import asyncio
import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock


class TestAPIPerformance:
    """Test API endpoint performance under various loads"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_user_creation_performance(self, client: AsyncClient):
        """Test user creation performance under load"""
        start_time = time.time()
        
        # Create multiple users concurrently
        tasks = []
        for i in range(50):
            user_data = {
                "email": f"perftest{i}@example.com",
                "username": f"perfuser{i}",
                "password": "password123"
            }
            task = client.post("/api/v1/users/", json=user_data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Analyze results
        success_count = 0
        error_count = 0
        
        for response in responses:
            if isinstance(response, Exception):
                error_count += 1
            elif hasattr(response, 'status_code') and response.status_code == 201:
                success_count += 1
            else:
                error_count += 1
        
        total_time = end_time - start_time
        
        # Performance assertions
        assert success_count > 40, f"Only {success_count}/50 users created successfully"
        assert total_time < 10.0, f"User creation took too long: {total_time:.2f}s"
        assert error_count < 5, f"Too many errors: {error_count}/50"
        
        # Calculate throughput
        throughput = success_count / total_time
        assert throughput > 5, f"Throughput too low: {throughput:.2f} users/second"

    @pytest.mark.slow  
    @pytest.mark.asyncio
    async def test_job_creation_performance(self, client: AsyncClient, authenticated_user):
        """Test job creation performance under concurrent load"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock Go service to prevent actual external calls
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            start_time = time.time()
            
            # Create multiple jobs concurrently
            tasks = []
            for i in range(30):
                job_data = {
                    "data_sources": [f"https://api{i}.example.com/data"],
                    "filters": {"performance_test": i}
                }
                task = client.post(
                    f"/api/v1/users/{user_id}/external-data",
                    json=job_data,
                    headers=headers
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
        
        # Analyze results
        success_count = 0
        job_ids = []
        
        for response in responses:
            if hasattr(response, 'status_code') and response.status_code == 202:
                success_count += 1
                job_ids.append(response.json()["job_id"])
        
        total_time = end_time - start_time
        
        # Performance assertions
        assert success_count == 30, f"Only {success_count}/30 jobs created successfully"
        assert total_time < 5.0, f"Job creation took too long: {total_time:.2f}s"
        assert len(set(job_ids)) == len(job_ids), "Job IDs should be unique"
        
        # Calculate throughput
        throughput = success_count / total_time
        assert throughput > 6, f"Job creation throughput too low: {throughput:.2f} jobs/second"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_authentication_performance(self, client: AsyncClient, test_user):
        """Test authentication performance under load"""
        login_data = {
            "username": test_user["username"],
            "password": test_user["password"]
        }
        
        start_time = time.time()
        
        # Perform multiple concurrent logins
        tasks = []
        for _ in range(20):
            task = client.post("/api/v1/auth/login", json=login_data)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        total_time = end_time - start_time
        
        assert success_count == 20, f"Only {success_count}/20 logins succeeded"
        assert total_time < 3.0, f"Authentication took too long: {total_time:.2f}s"
        
        # Verify all tokens are valid
        tokens = [r.json()["access_token"] for r in responses if r.status_code == 200]
        assert len(tokens) == 20
        assert len(set(tokens)) == 20, "All tokens should be unique"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_job_status_checking_performance(self, client: AsyncClient, authenticated_user):
        """Test job status checking performance with many concurrent requests"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job first
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            job_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json={"data_sources": ["https://api.example.com/data"], "filters": {}},
                headers=headers
            )
        
        job_id = job_response.json()["job_id"]
        
        start_time = time.time()
        
        # Check job status many times concurrently
        tasks = []
        for _ in range(100):
            task = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        total_time = end_time - start_time
        
        assert success_count == 100, f"Only {success_count}/100 status checks succeeded"
        assert total_time < 2.0, f"Status checking took too long: {total_time:.2f}s"
        
        # Calculate throughput
        throughput = success_count / total_time
        assert throughput > 50, f"Status check throughput too low: {throughput:.2f} requests/second"


class TestDatabasePerformance:
    """Test database operation performance"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_bulk_user_creation_performance(self, db_session: AsyncSession):
        """Test bulk user creation performance"""
        from app.models.user import User
        from app.services.auth import get_password_hash
        
        start_time = time.time()
        
        # Create many users in bulk
        users = []
        for i in range(100):
            user = User(
                email=f"bulk{i}@example.com",
                username=f"bulkuser{i}",
                hashed_password=get_password_hash("password123"),
                is_active=True
            )
            users.append(user)
        
        db_session.add_all(users)
        await db_session.commit()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete quickly
        assert total_time < 5.0, f"Bulk user creation took too long: {total_time:.2f}s"
        
        # Calculate throughput
        throughput = 100 / total_time
        assert throughput > 20, f"Bulk creation throughput too low: {throughput:.2f} users/second"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_database_query_performance(self, db_session: AsyncSession, test_user):
        """Test database query performance with large datasets"""
        from app.models.job import Job
        from sqlalchemy import select
        import json
        
        # Create many jobs
        jobs = []
        for i in range(500):
            job = Job(
                user_id=test_user["id"],
                job_type="external_data",
                status="completed" if i % 2 == 0 else "failed",
                parameters=json.dumps({"performance_test": i}),
                result=json.dumps({"result": i}) if i % 2 == 0 else None
            )
            jobs.append(job)
        
        db_session.add_all(jobs)
        await db_session.commit()
        
        # Test query performance
        start_time = time.time()
        
        # Query jobs with various filters
        result = await db_session.execute(
            select(Job)
            .where(Job.user_id == test_user["id"])
            .where(Job.status == "completed")
            .order_by(Job.created_at.desc())
            .limit(50)
        )
        completed_jobs = result.scalars().all()
        
        end_time = time.time()
        query_time = end_time - start_time
        
        assert len(completed_jobs) == 50
        assert query_time < 0.5, f"Database query took too long: {query_time:.3f}s"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, db_session: AsyncSession):
        """Test concurrent database operations performance"""
        from app.models.user import User
        from app.services.auth import get_password_hash
        from sqlalchemy import select
        
        async def create_and_query_user(index):
            """Create a user and immediately query it"""
            # Note: This would normally require separate database sessions
            # for true concurrency testing
            user = User(
                email=f"concurrent{index}@example.com",
                username=f"concurrent{index}",
                hashed_password=get_password_hash("password123")
            )
            db_session.add(user)
            await db_session.commit()
            await db_session.refresh(user)
            
            # Query the user back
            result = await db_session.execute(
                select(User).where(User.id == user.id)
            )
            queried_user = result.scalar_one()
            return queried_user.id
        
        start_time = time.time()
        
        # Run concurrent operations
        tasks = [create_and_query_user(i) for i in range(10)]
        user_ids = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        assert len(user_ids) == 10
        assert len(set(user_ids)) == 10, "All user IDs should be unique"
        assert total_time < 3.0, f"Concurrent operations took too long: {total_time:.2f}s"


class TestMemoryUsage:
    """Test memory usage under load"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_memory_usage_during_load(self, client: AsyncClient, authenticated_user):
        """Test that memory usage remains reasonable under load"""
        import psutil
        import os
        
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock Go service
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Create many jobs to test memory usage
            for batch in range(10):  # 10 batches of 20 jobs each
                tasks = []
                for i in range(20):
                    job_data = {
                        "data_sources": [f"https://api{batch*20+i}.example.com/data"],
                        "filters": {"batch": batch, "index": i}
                    }
                    task = client.post(
                        f"/api/v1/users/{user_id}/external-data",
                        json=job_data,
                        headers=headers
                    )
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks)
                
                # Verify all succeeded
                success_count = sum(1 for r in responses if r.status_code == 202)
                assert success_count == 20, f"Batch {batch}: only {success_count}/20 succeeded"
                
                # Small delay between batches
                await asyncio.sleep(0.1)
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should not increase excessively
        assert memory_increase < 100, f"Memory increased too much: {memory_increase:.1f}MB"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_response_time_consistency(self, client: AsyncClient, authenticated_user):
        """Test that response times remain consistent under load"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response_times = []
        
        # Mock Go service
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Make sequential requests to measure response time consistency
            for i in range(50):
                start = time.time()
                
                job_data = {
                    "data_sources": [f"https://api{i}.example.com/data"],
                    "filters": {"response_time_test": i}
                }
                
                response = await client.post(
                    f"/api/v1/users/{user_id}/external-data",
                    json=job_data,
                    headers=headers
                )
                
                end = time.time()
                response_time = end - start
                response_times.append(response_time)
                
                assert response.status_code == 202
        
        # Analyze response times
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        # Response time assertions
        assert avg_response_time < 0.1, f"Average response time too high: {avg_response_time:.3f}s"
        assert max_response_time < 0.5, f"Maximum response time too high: {max_response_time:.3f}s"
        assert max_response_time / min_response_time < 10, "Response times too inconsistent"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, client: AsyncClient, authenticated_user):
        """Test database connection pool performance under load"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        start_time = time.time()
        
        # Make many concurrent requests that hit the database
        tasks = []
        for i in range(100):
            task = client.get(f"/api/v1/users/{user_id}", headers=headers)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        # All should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        total_time = end_time - start_time
        
        assert success_count == 100, f"Only {success_count}/100 database requests succeeded"
        assert total_time < 3.0, f"Database operations took too long: {total_time:.2f}s"
        
        # Calculate database throughput
        db_throughput = success_count / total_time
        assert db_throughput > 30, f"Database throughput too low: {db_throughput:.1f} ops/second"


class TestScalabilityLimits:
    """Test system behavior at scalability limits"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_maximum_concurrent_connections(self, client: AsyncClient):
        """Test maximum number of concurrent connections"""
        # Test health endpoint with many concurrent connections
        start_time = time.time()
        
        tasks = []
        for _ in range(200):  # High number of concurrent requests
            task = client.get("/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        success_count = 0
        connection_errors = 0
        
        for response in responses:
            if isinstance(response, Exception):
                connection_errors += 1
            elif hasattr(response, 'status_code') and response.status_code == 200:
                success_count += 1
        
        total_time = end_time - start_time
        
        # Should handle high concurrency
        assert success_count > 180, f"Only {success_count}/200 connections succeeded"
        assert connection_errors < 20, f"Too many connection errors: {connection_errors}"
        assert total_time < 5.0, f"High concurrency test took too long: {total_time:.2f}s"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, client: AsyncClient, authenticated_user):
        """Test handling of large request payloads"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create large payload
        large_data_sources = [f"https://api{i}.example.com/data/{j}" 
                             for i in range(10) for j in range(10)]  # 100 URLs
        
        large_filters = {}
        for i in range(100):
            large_filters[f"filter_{i}"] = f"value_{i}" * 100  # Large string values
        
        large_job_data = {
            "data_sources": large_data_sources,
            "filters": large_filters
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            start_time = time.time()
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=large_job_data,
                headers=headers
            )
            
            end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should handle large payloads
        assert response.status_code in [202, 413], "Large payload should be accepted or rejected cleanly"
        assert processing_time < 1.0, f"Large payload processing took too long: {processing_time:.3f}s"

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load_over_time(self, client: AsyncClient, authenticated_user):
        """Test system behavior under sustained load over time"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock Go service
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            total_requests = 0
            total_errors = 0
            start_time = time.time()
            
            # Run sustained load for 30 seconds
            while time.time() - start_time < 30:
                batch_start = time.time()
                
                # Send batch of requests
                tasks = []
                batch_size = 10
                for i in range(batch_size):
                    job_data = {
                        "data_sources": [f"https://api{total_requests + i}.example.com/data"],
                        "filters": {"sustained_test": total_requests + i}
                    }
                    task = client.post(
                        f"/api/v1/users/{user_id}/external-data",
                        json=job_data,
                        headers=headers
                    )
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successes and errors
                for response in responses:
                    total_requests += 1
                    if isinstance(response, Exception) or \
                       (hasattr(response, 'status_code') and response.status_code != 202):
                        total_errors += 1
                
                batch_time = time.time() - batch_start
                
                # Maintain reasonable request rate
                if batch_time < 0.5:  # If batch was too fast, slow down
                    await asyncio.sleep(0.5 - batch_time)
        
        total_time = time.time() - start_time
        error_rate = total_errors / total_requests if total_requests > 0 else 1
        average_throughput = total_requests / total_time
        
        # Performance assertions
        assert total_requests > 100, f"Not enough requests processed: {total_requests}"
        assert error_rate < 0.05, f"Error rate too high: {error_rate:.1%}"
        assert average_throughput > 5, f"Average throughput too low: {average_throughput:.1f} req/s"


class TestResourceUtilization:
    """Test resource utilization patterns"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_cpu_usage_under_load(self, client: AsyncClient, authenticated_user):
        """Test CPU usage during high load operations"""
        import psutil
        
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Monitor CPU usage
        cpu_usage_samples = []
        
        async def monitor_cpu():
            for _ in range(10):  # Sample for 10 seconds
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_usage_samples.append(cpu_percent)
        
        async def generate_load():
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                # Generate continuous load
                for i in range(50):
                    job_data = {
                        "data_sources": [f"https://api{i}.example.com/data"],
                        "filters": {"cpu_test": i}
                    }
                    
                    await client.post(
                        f"/api/v1/users/{user_id}/external-data",
                        json=job_data,
                        headers=headers
                    )
                    
                    await asyncio.sleep(0.1)  # Small delay
        
        # Run monitoring and load generation concurrently
        await asyncio.gather(monitor_cpu(), generate_load())
        
        # Analyze CPU usage
        avg_cpu = sum(cpu_usage_samples) / len(cpu_usage_samples) if cpu_usage_samples else 0
        max_cpu = max(cpu_usage_samples) if cpu_usage_samples else 0
        
        # CPU usage should be reasonable
        assert avg_cpu < 80, f"Average CPU usage too high: {avg_cpu:.1f}%"
        assert max_cpu < 95, f"Peak CPU usage too high: {max_cpu:.1f}%"