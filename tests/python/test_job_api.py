"""
End-to-End Tests for Job Management API

These tests define the expected behavior for job-related operations.
The Python API should delegate complex jobs to the Go service.
"""
import pytest
import json
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


class TestJobCreation:
    """Test job creation and queuing"""

    @pytest.mark.asyncio
    async def test_create_external_data_job_success(self, client: AsyncClient, authenticated_user):
        """Test successful creation of external data job"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": ["api1", "api2", "api3"],
            "filters": {
                "date_range": "last_30_days",
                "category": "technology"
            }
        }
        
        response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        assert response.status_code == 202  # Accepted
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "queued"
        assert "message" in data
        assert isinstance(data["job_id"], int)

    @pytest.mark.asyncio
    async def test_create_external_data_job_unauthorized(self, client: AsyncClient):
        """Test job creation without authentication"""
        job_data = {
            "data_sources": ["api1"],
            "filters": {}
        }
        
        response = await client.post("/api/v1/users/1/external-data", json=job_data)
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_external_data_job_invalid_user(self, client: AsyncClient, authenticated_user):
        """Test job creation for non-existent user"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": ["api1"],
            "filters": {}
        }
        
        response = await client.post(
            "/api/v1/users/99999/external-data",
            json=job_data,
            headers=headers
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_external_data_job_invalid_data(self, client: AsyncClient, authenticated_user):
        """Test job creation with invalid data"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Missing required fields
        job_data = {
            "filters": {"category": "tech"}
            # Missing data_sources
        }
        
        response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any("data_sources" in error["loc"] for error in errors)

    @pytest.mark.asyncio
    async def test_create_external_data_job_empty_data_sources(self, client: AsyncClient, authenticated_user):
        """Test job creation with empty data sources"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        job_data = {
            "data_sources": [],  # Empty list
            "filters": {}
        }
        
        response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        assert response.status_code == 422
        assert "data_sources" in str(response.json()["detail"]).lower()


class TestJobStatusRetrieval:
    """Test job status and result retrieval"""

    @pytest.mark.asyncio
    async def test_get_job_status_queued(self, client: AsyncClient, authenticated_user):
        """Test getting status of a queued job"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job first
        job_data = {
            "data_sources": ["api1"],
            "filters": {}
        }
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        job_id = create_response.json()["job_id"]
        
        # Get job status
        response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["status"] in ["queued", "processing"]
        assert data["job_type"] == "external_data"
        assert "created_at" in data
        assert data["user_id"] == user_id

    @pytest.mark.asyncio
    async def test_get_job_status_processing(self, client: AsyncClient, authenticated_user, mock_processing_job):
        """Test getting status of a processing job"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_processing_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["result"] is None
        assert data["error_message"] is None

    @pytest.mark.asyncio
    async def test_get_job_status_completed(self, client: AsyncClient, authenticated_user, mock_completed_job):
        """Test getting status of a completed job"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_completed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert isinstance(data["result"], dict)
        assert "completed_at" in data

    @pytest.mark.asyncio
    async def test_get_job_status_failed(self, client: AsyncClient, authenticated_user, mock_failed_job):
        """Test getting status of a failed job"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_failed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] is not None
        assert len(data["error_message"]) > 0

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self, client: AsyncClient, authenticated_user):
        """Test getting status of non-existent job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/jobs/99999", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_job_status_unauthorized(self, client: AsyncClient, mock_completed_job):
        """Test getting job status without authentication"""
        response = await client.get(f"/api/v1/jobs/{mock_completed_job}")
        
        assert response.status_code == 401


class TestUserJobsRetrieval:
    """Test retrieving all jobs for a user"""

    @pytest.mark.asyncio
    async def test_get_user_jobs_empty(self, client: AsyncClient, authenticated_user):
        """Test getting jobs for user with no jobs"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # May be empty or contain jobs from other tests

    @pytest.mark.asyncio
    async def test_get_user_jobs_with_jobs(self, client: AsyncClient, authenticated_user):
        """Test getting jobs for user with multiple jobs"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple jobs
        job_ids = []
        for i in range(3):
            job_data = {
                "data_sources": [f"api{i}"],
                "filters": {"index": i}
            }
            create_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
            job_ids.append(create_response.json()["job_id"])
        
        # Get all jobs
        response = await client.get(f"/api/v1/users/{user_id}/jobs", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3
        
        # Check that all our jobs are in the response
        response_job_ids = [job["id"] for job in data]
        for job_id in job_ids:
            assert job_id in response_job_ids

    @pytest.mark.asyncio
    async def test_get_user_jobs_with_pagination(self, client: AsyncClient, authenticated_user):
        """Test getting user jobs with pagination"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test pagination parameters
        response = await client.get(
            f"/api/v1/users/{user_id}/jobs?skip=0&limit=2",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 2

    @pytest.mark.asyncio
    async def test_get_user_jobs_unauthorized(self, client: AsyncClient):
        """Test getting user jobs without authentication"""
        response = await client.get("/api/v1/users/1/jobs")
        
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_user_jobs_different_user(self, client: AsyncClient, authenticated_user):
        """Test getting jobs for a different user (should be forbidden)"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to get jobs for a different user
        different_user_id = user_id + 1000  # Assume this is a different user
        response = await client.get(f"/api/v1/users/{different_user_id}/jobs", headers=headers)
        
        # Should either be 403 (forbidden) or 404 (not found)
        assert response.status_code in [403, 404]


class TestJobCancellation:
    """Test job cancellation functionality"""

    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, client: AsyncClient, authenticated_user):
        """Test cancelling a queued job"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job
        job_data = {
            "data_sources": ["api1"],
            "filters": {}
        }
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        job_id = create_response.json()["job_id"]
        
        # Cancel the job
        response = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_cancel_processing_job(self, client: AsyncClient, authenticated_user, mock_processing_job):
        """Test cancelling a processing job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_processing_job
        
        response = await client.post(f"/api/v1/jobs/{job_id}/cancel", headers=headers)
        
        # Processing jobs might not be cancellable
        assert response.status_code in [200, 409]  # OK or Conflict

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
    async def test_cancel_job_not_found(self, client: AsyncClient, authenticated_user):
        """Test cancelling non-existent job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.post("/api/v1/jobs/99999/cancel", headers=headers)
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_job_unauthorized(self, client: AsyncClient, mock_processing_job):
        """Test cancelling job without authentication"""
        response = await client.post(f"/api/v1/jobs/{mock_processing_job}/cancel")
        
        assert response.status_code == 401


class TestJobResultsRetrieval:
    """Test retrieving detailed job results"""

    @pytest.mark.asyncio
    async def test_get_job_results_completed(self, client: AsyncClient, authenticated_user, mock_completed_job):
        """Test getting results from completed job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_completed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "metadata" in data
        assert isinstance(data["results"], list)
        assert len(data["results"]) > 0

    @pytest.mark.asyncio
    async def test_get_job_results_not_completed(self, client: AsyncClient, authenticated_user, mock_processing_job):
        """Test getting results from job that's not completed"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_processing_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        
        assert response.status_code == 409  # Conflict
        assert "not completed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_job_results_failed(self, client: AsyncClient, authenticated_user, mock_failed_job):
        """Test getting results from failed job"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_failed_job
        
        response = await client.get(f"/api/v1/jobs/{job_id}/results", headers=headers)
        
        assert response.status_code == 409  # Conflict
        assert "failed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_job_results_with_format(self, client: AsyncClient, authenticated_user, mock_completed_job):
        """Test getting job results in different formats"""
        _, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        job_id = mock_completed_job
        
        # Test JSON format (default)
        response = await client.get(f"/api/v1/jobs/{job_id}/results?format=json", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/json")
        
        # Test CSV format
        response = await client.get(f"/api/v1/jobs/{job_id}/results?format=csv", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")

    @pytest.mark.asyncio
    async def test_get_job_results_unauthorized(self, client: AsyncClient, mock_completed_job):
        """Test getting job results without authentication"""
        response = await client.get(f"/api/v1/jobs/{mock_completed_job}/results")
        
        assert response.status_code == 401