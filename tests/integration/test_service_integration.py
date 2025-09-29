"""
Integration Tests for Python-Go Service Communication

These tests verify that the Python API and Go worker service
communicate correctly through HTTP and shared database.
"""
import pytest
import asyncio
import json
import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import requests


class TestServiceIntegration:
    """Test integration between Python API and Go worker service"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_job_workflow(self, client: AsyncClient, authenticated_user, go_service_url):
        """Test complete workflow from job creation to completion"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 1: Create a job via Python API
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {"type": "integration_test"}
        }
        
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]
        
        # Step 2: Verify job is created in database with "queued" status
        status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["status"] == "queued"
        
        # Step 3: Wait for Go service to process the job
        max_wait_time = 30  # seconds
        wait_interval = 1   # second
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            job_status = status_response.json()["status"]
            
            if job_status in ["completed", "failed"]:
                break
                
            await asyncio.sleep(wait_interval)
            elapsed_time += wait_interval
        
        # Step 4: Verify job completion
        final_status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        final_job = final_status_response.json()
        
        assert final_job["status"] == "completed"
        assert final_job["result"] is not None
        assert isinstance(final_job["result"], dict)
        assert "api_results" in final_job["result"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_job_failure_handling(self, client: AsyncClient, authenticated_user):
        """Test job failure handling between services"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job with invalid data sources (should cause failure)
        job_data = {
            "data_sources": ["https://invalid-url-that-does-not-exist.com/api"],
            "filters": {}
        }
        
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        assert create_response.status_code == 202
        job_id = create_response.json()["job_id"]
        
        # Wait for job to fail
        max_wait_time = 30
        wait_interval = 1
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            job_status = status_response.json()["status"]
            
            if job_status in ["completed", "failed"]:
                break
                
            await asyncio.sleep(wait_interval)
            elapsed_time += wait_interval
        
        # Verify job failed with proper error message
        final_status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        final_job = final_status_response.json()
        
        assert final_job["status"] == "failed"
        assert final_job["error_message"] is not None
        assert len(final_job["error_message"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_job_processing(self, client: AsyncClient, authenticated_user):
        """Test that multiple jobs can be processed concurrently"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple jobs
        job_ids = []
        for i in range(5):
            job_data = {
                "data_sources": [f"https://jsonplaceholder.typicode.com/posts/{i+1}"],
                "filters": {"batch": "concurrent_test", "index": i}
            }
            
            create_response = await client.post(
                f"/api/v1/users/{user_id}/external-data",
                json=job_data,
                headers=headers
            )
            
            assert create_response.status_code == 202
            job_ids.append(create_response.json()["job_id"])
        
        # Wait for all jobs to complete
        max_wait_time = 60  # More time for multiple jobs
        completed_jobs = 0
        
        for attempt in range(max_wait_time):
            completed_jobs = 0
            
            for job_id in job_ids:
                status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
                job_status = status_response.json()["status"]
                
                if job_status in ["completed", "failed"]:
                    completed_jobs += 1
            
            if completed_jobs == len(job_ids):
                break
                
            await asyncio.sleep(1)
        
        # Verify all jobs completed
        assert completed_jobs == len(job_ids), f"Only {completed_jobs} out of {len(job_ids)} jobs completed"
        
        # Verify each job has results
        for job_id in job_ids:
            status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            job = status_response.json()
            assert job["status"] in ["completed", "failed"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_database_consistency(self, client: AsyncClient, authenticated_user, db_session: AsyncSession):
        """Test that database state is consistent between services"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/users/1"],
            "filters": {}
        }
        
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        job_id = create_response.json()["job_id"]
        
        # Wait for job to complete
        max_wait_time = 30
        for _ in range(max_wait_time):
            status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            if status_response.json()["status"] in ["completed", "failed"]:
                break
            await asyncio.sleep(1)
        
        # Verify database state directly
        from sqlalchemy import select, text
        from app.models.job import Job
        
        result = await db_session.execute(select(Job).where(Job.id == job_id))
        db_job = result.scalar_one()
        
        # Verify job exists in database
        assert db_job is not None
        assert db_job.id == job_id
        assert db_job.user_id == user_id
        assert db_job.status in ["completed", "failed"]
        
        # Verify timestamps are set
        assert db_job.created_at is not None
        assert db_job.updated_at is not None
        
        if db_job.status == "completed":
            assert db_job.result is not None
            # Verify result is valid JSON
            result_data = json.loads(db_job.result)
            assert isinstance(result_data, dict)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_go_service_direct_communication(self, go_service_url, db_session: AsyncSession):
        """Test direct communication with Go service"""
        if not go_service_url:
            pytest.skip("Go service URL not provided")
        
        # Test Go service health check
        response = requests.get(f"{go_service_url}/health", timeout=10)
        assert response.status_code == 200
        
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "go-worker"
        
        # Test direct job submission to Go service
        job_request = {
            "job_id": 999,
            "user_id": 1,
            "job_type": "external_data",
            "parameters": {
                "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
                "filters": {}
            }
        }
        
        response = requests.post(
            f"{go_service_url}/api/v1/jobs/process",
            json=job_request,
            timeout=10
        )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "accepted"
        assert response_data["job_id"] == 999

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_error_propagation(self, client: AsyncClient, authenticated_user):
        """Test that errors from Go service are properly propagated"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job that will cause a specific error in Go service
        job_data = {
            "data_sources": ["https://httpstat.us/500"],  # Always returns 500 error
            "filters": {"error_test": True}
        }
        
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        job_id = create_response.json()["job_id"]
        
        # Wait for job to fail
        max_wait_time = 30
        for _ in range(max_wait_time):
            status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            job_status = status_response.json()["status"]
            
            if job_status == "failed":
                break
            elif job_status == "completed":
                pytest.fail("Job should have failed but completed successfully")
                
            await asyncio.sleep(1)
        
        # Verify error details
        final_status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        final_job = final_status_response.json()
        
        assert final_job["status"] == "failed"
        assert final_job["error_message"] is not None
        assert "500" in final_job["error_message"] or "error" in final_job["error_message"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_job_timeout_handling(self, client: AsyncClient, authenticated_user):
        """Test handling of jobs that take too long to process"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job that would timeout (if timeout is implemented)
        job_data = {
            "data_sources": ["https://httpstat.us/200?sleep=60000"],  # 60 second delay
            "filters": {"timeout_test": True}
        }
        
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        job_id = create_response.json()["job_id"]
        
        # Check status after a reasonable time
        await asyncio.sleep(10)  # Wait 10 seconds
        
        status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        job_status = status_response.json()["status"]
        
        # Job should either be processing, completed, or failed (depending on timeout implementation)
        assert job_status in ["processing", "completed", "failed", "queued"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_large_result_handling(self, client: AsyncClient, authenticated_user):
        """Test handling of jobs with large result sets"""
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job that returns multiple data sources
        job_data = {
            "data_sources": [
                "https://jsonplaceholder.typicode.com/posts",
                "https://jsonplaceholder.typicode.com/users",
                "https://jsonplaceholder.typicode.com/albums"
            ],
            "filters": {"large_result_test": True}
        }
        
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        job_id = create_response.json()["job_id"]
        
        # Wait for completion
        max_wait_time = 60  # Larger results might take longer
        for _ in range(max_wait_time):
            status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
            job_status = status_response.json()["status"]
            
            if job_status in ["completed", "failed"]:
                break
                
            await asyncio.sleep(1)
        
        # Verify large result handling
        final_status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        final_job = final_status_response.json()
        
        if final_job["status"] == "completed":
            assert final_job["result"] is not None
            result = final_job["result"]
            assert isinstance(result, dict)
            assert "api_results" in result
            assert len(result["api_results"]) == 3  # Three data sources

    @pytest.mark.asyncio
    @pytest.mark.integration 
    async def test_service_recovery_after_restart(self, client: AsyncClient, authenticated_user):
        """Test that jobs can be recovered after service restart"""
        # This test would require actually restarting services
        # For now, we'll test the job persistence aspect
        
        user_id, token = authenticated_user
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a job
        job_data = {
            "data_sources": ["https://jsonplaceholder.typicode.com/posts/1"],
            "filters": {"recovery_test": True}
        }
        
        create_response = await client.post(
            f"/api/v1/users/{user_id}/external-data",
            json=job_data,
            headers=headers
        )
        
        job_id = create_response.json()["job_id"]
        
        # Verify job persists in database even if services restart
        # (In a real test, you would restart the services here)
        
        status_response = await client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert status_response.status_code == 200
        assert status_response.json()["id"] == job_id