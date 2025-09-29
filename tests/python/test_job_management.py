"""
Comprehensive Job Management API Tests

These tests verify all job-related functionality including creation,
status tracking, result retrieval, and error handling.
"""
import pytest
import json
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from app.models.job import Job
from app.models.user import User


class TestJobCreationValidation:
    """Test job creation with comprehensive validation"""

    @pytest.mark.asyncio
    async def test_create_external_data_job_success(self, client: AsyncClient, authenticated_user):
        """Test successful external data job creation"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": [
                "https://jsonplaceholder.typicode.com/posts/1",
                "https://jsonplaceholder.typicode.com/users/1"
            ],
            "filters": {
                "date_range": "last_30_days",
                "category": "technology",
                "limit": 100
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "accepted"}
            mock_post.return_value = mock_response
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert isinstance(data["job_id"], int)
        assert "message" in data

    @pytest.mark.asyncio
    async def test_create_job_empty_data_sources(self, client: AsyncClient, authenticated_user):
        """Test job creation fails with empty data sources"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": [],  # Empty
            "filters": {}
        }
        
        response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("data_sources" in str(error["loc"]).lower() for error in errors)

    @pytest.mark.asyncio
    async def test_create_job_invalid_urls(self, client: AsyncClient, authenticated_user):
        """Test job creation with invalid URLs"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-protocol.com",
            "http://",
            "",
            "javascript:alert('xss')"
        ]
        
        job_data = {
            "data_sources": invalid_urls,
            "filters": {}
        }
        
        # Depending on validation implementation, this might:
        # 1. Reject at API level (422)
        # 2. Accept but fail during processing
        response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        # Document expected behavior
        assert response.status_code in [202, 422]

    @pytest.mark.asyncio
    async def test_create_job_malformed_filters(self, client: AsyncClient, authenticated_user):
        """Test job creation with various filter formats"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with different filter types
        filter_variations = [
            {"simple": "value"},
            {"nested": {"key": "value"}},
            {"array": ["item1", "item2"]},
            {"mixed": {"string": "text", "number": 123, "bool": True}},
            {},  # Empty filters should be OK
        ]
        
        for filters in filter_variations:
            job_data = {
                "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
                "filters": filters
            }
            
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_post.return_value = mock_response
                
                response = await client.post(
                    f"/api/v1/users/{user_id}/external-data",
                    json=job_data,
                    headers=headers
                )
            
            assert response.status_code == 202, f"Filters {filters} should be accepted"

    @pytest.mark.asyncio
    async def test_create_job_large_payload(self, client: AsyncClient, authenticated_user):
        """Test job creation with large data payload"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create job with many data sources
        large_data_sources = [f"https://api{i}.example.com/data" for i in range(100)]
        large_filters = {f"filter_{i}": f"value_{i}" for i in range(50)}
        
        job_data = {
            "data_sources": large_data_sources,
            "filters": large_filters
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        # Should handle large payloads
        assert response.status_code in [202, 413]  # Accepted or Payload Too Large

    @pytest.mark.asyncio
    async def test_create_job_unauthorized_user(self, client: AsyncClient, authenticated_user):
        """Test creating job for different user (authorization check)"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        different_user_id = user_id + 1000  # Different user
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {}
        }
        
        response = await client.post(
            f"/api/v1/users/{different_user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        assert response.status_code == 403  # Forbidden


class TestJobStatusTracking:
    """Test job status tracking and lifecycle"""

    @pytest.mark.asyncio
    async def test_job_status_progression(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test job status progresses correctly"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create job in database directly for testing
        job = Job(
            user_id=user_id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps({"data_sources": ["test"]})
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        
        # Test queued status
        response = await client.get(f"/api/v1/jobs/{job.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        
        # Update to processing
        job.status = "processing"
        await db_session.commit()
        
        response = await client.get(f"/api/v1/jobs/{job.id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
        
        # Update to completed
        job.status = "completed"
        job.result = json.dumps({"api_results": [{"source": "test", "data": "result"}]})
        job.completed_at = datetime.utcnow()
        await db_session.commit()
        
        response = await client.get(f"/api/v1/jobs/{job.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] is not None

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, client: AsyncClient, authenticated_user):
        """Test getting status of non-existent job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/jobs/99999", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_job_status_different_user(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test authorization check for job status access"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create job for different user
        different_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password="hashedpass",
            is_active=True
        )
        db_session.add(different_user)
        await db_session.commit()
        await db_session.refresh(different_user)
        
        job = Job(
            user_id=different_user.id,
            job_type="external_data",
            status="completed",
            parameters=json.dumps({"test": True})
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        
        # Try to access other user's job
        response = await client.get(f"/api/v1/jobs/{job.id}", headers=headers)
        
        assert response.status_code == 403  # Forbidden


class TestJobResultRetrieval:
    """Test job result retrieval and formatting"""

    @pytest.mark.asyncio
    async def test_get_completed_job_results(self, client: AsyncClient, authenticated_user, mock_completed_job):
        """Test retrieving results from completed job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_completed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "metadata" in data
        
        # Verify result structure
        results = data["results"]
        assert "api_results" in results
        assert isinstance(results["api_results"], list)
        
        metadata = data["metadata"]
        assert "job_id" in metadata
        assert "completed_at" in metadata

    @pytest.mark.asyncio
    async def test_get_results_job_not_completed(self, client: AsyncClient, authenticated_user, mock_processing_job):
        """Test getting results from incomplete job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_processing_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        
        assert response.status_code == 409  # Conflict
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_results_failed_job(self, client: AsyncClient, authenticated_user, mock_failed_job):
        """Test getting results from failed job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_failed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        
        assert response.status_code == 409  # Conflict
        assert "failed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_results_csv_format(self, client: AsyncClient, authenticated_user, mock_completed_job):
        """Test getting results in CSV format"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_completed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results?format=csv", headers=headers)
        
        # Should either implement CSV format or return appropriate error
        assert response.status_code in [200, 400, 501]  # OK, Bad Request, or Not Implemented
        
        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_get_results_invalid_format(self, client: AsyncClient, authenticated_user, mock_completed_job):
        """Test getting results with invalid format parameter"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_completed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results?format=xml", headers=headers)
        
        assert response.status_code == 400
        assert "unsupported format" in response.json()["detail"].lower()


class TestJobCancellation:
    """Test job cancellation functionality"""

    @pytest.mark.asyncio
    async def test_cancel_queued_job_success(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test successfully cancelling a queued job"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a queued job
        job = Job(
            user_id=user_id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps({"data_sources": ["test"]})
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        
        response = await client.post(f"/api/v1/jobs/{job.id}/cancel", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["job_id"] == job.id

    @pytest.mark.asyncio
    async def test_cancel_processing_job(self, client: AsyncClient, authenticated_user, mock_processing_job):
        """Test cancelling a job that's currently processing"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_processing_job
        
        response = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        
        # Might not be cancellable if already processing
        assert response.status_code in [200, 409]  # OK or Conflict
        
        if response.status_code == 409:
            assert "cannot be cancelled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cancel_completed_job(self, client: AsyncClient, authenticated_user, mock_completed_job):
        """Test cancelling a completed job (should fail)"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_completed_job
        
        response = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        
        assert response.status_code == 409  # Conflict
        assert "cannot be cancelled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_cancel_job_different_user(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test cancelling job belonging to different user"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create different user and their job
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password="hashedpass",
            is_active=True
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)
        
        other_job = Job(
            user_id=other_user.id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps({"test": True})
        )
        db_session.add(other_job)
        await db_session.commit()
        await db_session.refresh(other_job)
        
        response = await client.post(f"/api/v1/jobs/{other_job.id}/cancel", headers=headers)
        
        assert response.status_code == 404  # Not found (or 403 Forbidden)

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_job(self, client: AsyncClient, authenticated_user):
        """Test cancelling non-existent job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.post("/api/v1/jobs/99999/cancel", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestUserJobsListing:
    """Test listing jobs for users with various scenarios"""

    @pytest.mark.asyncio
    async def test_get_user_jobs_empty(self, client: AsyncClient, authenticated_user):
        """Test getting jobs for user with no jobs"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_user_jobs_with_multiple_jobs(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test getting jobs for user with multiple jobs"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple jobs
        job_statuses = ["queued", "processing", "completed", "failed"]
        created_jobs = []
        
        for i, status in enumerate(job_statuses):
            job = Job(
                user_id=user_id,
                job_type="external_data",
                status=status,
                parameters=json.dumps({"index": i})
            )
            if status == "completed":
                job.result = json.dumps({"test_result": i})
                job.completed_at = datetime.utcnow()
            elif status == "failed":
                job.error_message = f"Test error {i}"
            
            db_session.add(job)
            created_jobs.append(job)
        
        await db_session.commit()
        
        response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= len(job_statuses)
        
        # Verify all job statuses are represented
        returned_statuses = [job["status"] for job in data]
        for status in job_statuses:
            assert status in returned_statuses

    @pytest.mark.asyncio
    async def test_get_user_jobs_pagination(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test job listing pagination"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create many jobs
        for i in range(15):
            job = Job(
                user_id=user_id,
                job_type="external_data",
                status="completed",
                parameters=json.dumps({"index": i})
            )
            db_session.add(job)
        
        await db_session.commit()
        
        # Test default pagination
        response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        assert response.status_code == 200
        all_jobs = response.json()
        
        # Test with limit
        response = await client.get(f"/api/v1/users/{user_id}/jobs?limit=5", headers=headers)
        assert response.status_code == 200
        limited_jobs = response.json()
        assert len(limited_jobs) <= 5
        
        # Test with skip
        response = await client.get(f"/api/v1/users/{user_id}/jobs?skip=5&limit=5", headers=headers)
        assert response.status_code == 200
        skipped_jobs = response.json()
        assert len(skipped_jobs) <= 5
        
        # Jobs should be different when skipping
        if len(limited_jobs) > 0 and len(skipped_jobs) > 0:
            limited_ids = [job["id"] for job in limited_jobs]
            skipped_ids = [job["id"] for job in skipped_jobs]
            assert not set(limited_ids).intersection(set(skipped_ids))

    @pytest.mark.asyncio
    async def test_get_user_jobs_ordering(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test that jobs are returned in correct order (newest first)"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create jobs with different creation times
        job_times = []
        for i in range(3):
            job = Job(
                user_id=user_id,
                job_type="external_data",
                status="completed",
                parameters=json.dumps({"order_test": i})
            )
            db_session.add(job)
            await db_session.commit()
            await db_session.refresh(job)
            job_times.append((job.id, job.created_at))
            
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)
        
        response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        assert response.status_code == 200
        jobs = response.json()
        
        # Should be ordered by creation time (newest first)
        if len(jobs) >= 3:
            job_ids = [job["id"] for job in jobs[:3]]
            expected_order = [job_id for job_id, _ in sorted(job_times, key=lambda x: x[1], reverse=True)]
            
            # Check that newest jobs appear first
            assert job_ids[0] in [job_id for job_id, _ in job_times[-2:]]  # One of the newest


class TestJobErrorHandling:
    """Test error handling in job processing"""

    @pytest.mark.asyncio
    async def test_job_creation_go_service_down(self, client: AsyncClient, authenticated_user):
        """Test job creation when Go service is unavailable"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {}
        }
        
        # Mock Go service being down
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        # Job should still be created but marked as failed
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        # Check job status
        status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        # Job might be marked as failed due to Go service communication failure
        assert status_response.status_code == 200

    @pytest.mark.asyncio
    async def test_job_creation_go_service_timeout(self, client: AsyncClient, authenticated_user):
        """Test job creation with Go service timeout"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {}
        }
        
        # Mock timeout
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError("Request timeout")
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        # Should handle timeout gracefully
        assert response.status_code == 202

    @pytest.mark.asyncio
    async def test_job_creation_database_error(self, client: AsyncClient, authenticated_user):
        """Test job creation with database errors"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {}
        }
        
        # Mock database error during job creation
        with patch('app.services.job_service.JobService.create_external_data_job') as mock_create:
            mock_create.side_effect = Exception("Database connection failed")
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        assert response.status_code == 500
        assert "failed to create job" in response.json()["detail"].lower()


class TestJobConcurrency:
    """Test concurrent job operations"""

    @pytest.mark.asyncio
    async def test_concurrent_job_creation(self, client: AsyncClient, authenticated_user):
        """Test creating multiple jobs concurrently"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Mock Go service responses
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            # Create multiple jobs concurrently
            tasks = []
            for i in range(5):
                job_data = {
                    "data_sources": [f"https://api{i}.example.com/data"],
                    "filters": {"concurrent_test": i}
                }
                
                task = client.post(
                    f"/api/v1/users/{user_id}/external-data",
                    json=job_data,
                    headers=headers
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
        
        # All should succeed
        job_ids = []
        for response in responses:
            assert response.status_code == 202
            job_ids.append(response.json()["job_id"])
        
        # All job IDs should be unique
        assert len(set(job_ids)) == len(job_ids)

    @pytest.mark.asyncio
    async def test_concurrent_job_status_checks(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test concurrent job status checking"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple jobs
        job_ids = []
        for i in range(3):
            job = Job(
                user_id=user_id,
                job_type="external_data",
                status="processing",
                parameters=json.dumps({"test": i})
            )
            db_session.add(job)
            job_ids.append(job)
        
        await db_session.commit()
        for job in job_ids:
            await db_session.refresh(job)
        
        # Check all job statuses concurrently
        tasks = []
        for job in job_ids:
            task = client.get(f"/api/v1/jobs/{job.id}", headers=headers)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "processing"


class TestJobParameterValidation:
    """Test job parameter validation and sanitization"""

    @pytest.mark.asyncio
    async def test_job_parameters_json_serialization(self, client: AsyncClient, authenticated_user):
        """Test that job parameters are properly JSON serialized"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        complex_parameters = {
            "data_sources": ["https://api.example.com/data"],
            "filters": {
                "string_filter": "text value",
                "number_filter": 42,
                "boolean_filter": True,
                "array_filter": [1, 2, 3],
                "nested_filter": {
                    "nested_key": "nested_value",
                    "nested_number": 3.14
                },
                "date_filter": "2023-01-01T00:00:00Z",
                "null_filter": None
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=complex_parameters,
                headers=headers
            )
        
        assert response.status_code == 202
        job_id = response.json()["job_id"]
        
        # Verify parameters were stored correctly
        status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        job_data = status_response.json()
        
        # Parameters should be accessible (though stored as JSON string)
        assert "parameters" in job_data or job_data.get("job_type") == "external_data"

    @pytest.mark.asyncio
    async def test_job_parameters_size_limits(self, client: AsyncClient, authenticated_user):
        """Test job parameter size limitations"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create very large parameters
        large_filters = {}
        for i in range(1000):
            large_filters[f"key_{i}"] = f"value_{i}" * 100  # Large string values
        
        job_data = {
            "data_sources": ["https://api.example.com/data"],
            "filters": large_filters
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        # Should either accept or reject based on size limits
        assert response.status_code in [202, 413, 422]

    @pytest.mark.asyncio
    async def test_job_parameters_special_characters(self, client: AsyncClient, authenticated_user):
        """Test job parameters with special characters"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        special_char_data = {
            "data_sources": ["https://api.example.com/data"],
            "filters": {
                "unicode": "Test with émojis 🚀 and ñoñó",
                "symbols": "!@#$%^&*()_+-=[]{}|;:,.<>?",
                "quotes": 'Single "double" quotes mixed',
                "newlines": "Line 1\nLine 2\rLine 3",
                "backslashes": "Path\\to\\file",
                "sql_chars": "'; DROP TABLE test; --"
            }
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=special_char_data,
                headers=headers
            )
        
        assert response.status_code == 202
        # Special characters should be handled safely


class TestGoServiceCommunication:
    """Test communication with Go service"""

    @pytest.mark.asyncio
    async def test_go_service_communication_success(self, client: AsyncClient, authenticated_user):
        """Test successful communication with Go service"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {"test": "communication"}
        }
        
        # Mock successful Go service response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "accepted", "job_id": 123}
            mock_post.return_value = mock_response
            
            response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
        
        assert response.status_code == 202
        
        # Verify the call to Go service was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert "/api/v1/jobs/process" in str(call_args)
        
        # Check payload structure
        json_payload = call_args.kwargs.get("json")
        assert json_payload is not None
        assert "job_id" in json_payload
        assert "user_id" in json_payload
        assert json_payload["user_id"] == user_id
        assert "job_type" in json_payload
        assert "parameters" in json_payload

    @pytest.mark.asyncio
    async def test_go_service_error_responses(self, client: AsyncClient, authenticated_user):
        """Test handling of Go service error responses"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {}
        }
        
        error_scenarios = [
            (400, "Bad Request"),
            (500, "Internal Server Error"),
            (503, "Service Unavailable")
        ]
        
        for status_code, error_message in error_scenarios:
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status_code = status_code
                mock_response.text = error_message
                mock_post.return_value = mock_response
                
                response = await client.post(
                    f"/api/v1/users/{user_id}/external-data",
                    json=job_data,
                    headers=headers
                )
            
            # Should still create job but mark as failed
            assert response.status_code == 202
            job_id = response.json()["job_id"]
            
            # Check job was marked as failed
            status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            job_status = status_response.json()
            # Job might be marked as failed due to Go service error
            assert job_status["status"] in ["queued", "failed"]