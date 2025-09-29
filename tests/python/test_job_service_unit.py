"""
Unit Tests for JobService

These tests focus on the JobService class functionality in isolation,
testing business logic without external dependencies.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import JobService
from app.models.user import User
from app.models.job import Job


class TestJobServiceCreation:
    """Test JobService job creation functionality"""

    @pytest.mark.asyncio
    async def test_create_external_data_job_success(self):
        """Test successful job creation with valid data"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        
        # Mock job creation
        mock_job = Job(id=123, user_id=1, job_type="external_data", status="queued")
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        # Create service
        service = JobService(mock_db)
        
        # Mock HTTP call to Go service
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Test job creation
            parameters = {
                "data_sources": ["https://api.example.com/data"],
                "filters": {"category": "test"}
            }
            
            job_id = await service.create_external_data_job(1, parameters)
        
        # Assertions
        assert job_id == 123
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_user_not_found(self):
        """Test job creation fails when user doesn't exist"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = None  # User not found
        mock_db.execute.return_value = mock_user_result
        
        service = JobService(mock_db)
        
        parameters = {"data_sources": ["https://api.example.com/data"]}
        
        with pytest.raises(ValueError, match="User 999 not found"):
            await service.create_external_data_job(999, parameters)

    @pytest.mark.asyncio
    async def test_create_job_go_service_failure(self):
        """Test job creation when Go service communication fails"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        
        # Mock job creation
        mock_job = Job(id=123, user_id=1, job_type="external_data", status="queued")
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        service = JobService(mock_db)
        
        # Mock HTTP call failure
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Connection failed")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            parameters = {"data_sources": ["https://api.example.com/data"]}
            
            # Should still return job_id even if Go service fails
            job_id = await service.create_external_data_job(1, parameters)
            
            assert job_id == 123
            # Job should be marked as failed
            mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_job_database_error(self):
        """Test job creation with database errors"""
        # Mock database session with commit failure
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        mock_db.add = MagicMock()
        mock_db.commit.side_effect = Exception("Database connection failed")
        
        service = JobService(mock_db)
        
        parameters = {"data_sources": ["https://api.example.com/data"]}
        
        with pytest.raises(Exception, match="Database connection failed"):
            await service.create_external_data_job(1, parameters)


class TestJobServiceStatusRetrieval:
    """Test JobService status retrieval functionality"""

    @pytest.mark.asyncio
    async def test_get_job_status_success(self):
        """Test successful job status retrieval"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job = Job(
            id=123,
            user_id=1,
            job_type="external_data",
            status="completed",
            result='{"api_results": [{"source": "test", "data": "result"}]}',
            error_message=None
        )
        mock_job_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_job_result
        
        service = JobService(mock_db)
        
        job_data = await service.get_job_status(123)
        
        assert job_data is not None
        assert job_data["id"] == 123
        assert job_data["status"] == "completed"
        assert job_data["result"] is not None
        assert isinstance(job_data["result"], dict)

    @pytest.mark.asyncio
    async def test_get_job_status_not_found(self):
        """Test job status retrieval for non-existent job"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_job_result
        
        service = JobService(mock_db)
        
        job_data = await service.get_job_status(999)
        
        assert job_data is None

    @pytest.mark.asyncio
    async def test_get_job_status_invalid_json_result(self):
        """Test job status retrieval with invalid JSON result"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job = Job(
            id=123,
            user_id=1,
            job_type="external_data",
            status="completed",
            result='invalid json {',  # Invalid JSON
            error_message=None
        )
        mock_job_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_job_result
        
        service = JobService(mock_db)
        
        job_data = await service.get_job_status(123)
        
        assert job_data is not None
        assert job_data["result"] == 'invalid json {'  # Should return as string


class TestJobServiceUserJobs:
    """Test JobService user jobs listing functionality"""

    @pytest.mark.asyncio
    async def test_get_user_jobs_success(self):
        """Test successful user jobs retrieval"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_jobs_result = AsyncMock()
        
        mock_jobs = [
            Job(id=1, user_id=1, job_type="external_data", status="completed"),
            Job(id=2, user_id=1, job_type="external_data", status="processing"),
            Job(id=3, user_id=1, job_type="external_data", status="queued"),
        ]
        mock_jobs_result.scalars.return_value.all.return_value = mock_jobs
        mock_db.execute.return_value = mock_jobs_result
        
        service = JobService(mock_db)
        
        jobs = await service.get_user_jobs(1, skip=0, limit=10)
        
        assert len(jobs) == 3
        assert all(job["user_id"] == 1 for job in jobs)
        assert jobs[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_get_user_jobs_empty(self):
        """Test user jobs retrieval with no jobs"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_jobs_result = AsyncMock()
        mock_jobs_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_jobs_result
        
        service = JobService(mock_db)
        
        jobs = await service.get_user_jobs(1, skip=0, limit=10)
        
        assert len(jobs) == 0
        assert isinstance(jobs, list)

    @pytest.mark.asyncio
    async def test_get_user_jobs_pagination(self):
        """Test user jobs retrieval with pagination"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_jobs_result = AsyncMock()
        
        # Return different jobs based on pagination
        mock_jobs = [
            Job(id=i, user_id=1, job_type="external_data", status="completed")
            for i in range(5, 10)  # Jobs 5-9 (simulating skip=5, limit=5)
        ]
        mock_jobs_result.scalars.return_value.all.return_value = mock_jobs
        mock_db.execute.return_value = mock_jobs_result
        
        service = JobService(mock_db)
        
        jobs = await service.get_user_jobs(1, skip=5, limit=5)
        
        assert len(jobs) == 5
        # Should verify that the query was called with correct skip/limit
        # This would require more sophisticated mocking of SQLAlchemy


class TestJobServiceCancellation:
    """Test JobService job cancellation functionality"""

    @pytest.mark.asyncio
    async def test_cancel_job_success(self):
        """Test successful job cancellation"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job = Job(
            id=123,
            user_id=1,
            job_type="external_data",
            status="queued"  # Cancellable status
        )
        mock_job_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_job_result
        mock_db.commit = AsyncMock()
        
        service = JobService(mock_db)
        
        result = await service.cancel_job(123, 1)
        
        assert result is True
        assert mock_job.status == "cancelled"
        assert mock_job.completed_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_job_not_found(self):
        """Test cancelling non-existent job"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_job_result
        
        service = JobService(mock_db)
        
        result = await service.cancel_job(999, 1)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_job_not_cancellable(self):
        """Test cancelling job in non-cancellable state"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job = Job(
            id=123,
            user_id=1,
            job_type="external_data",
            status="completed"  # Not cancellable
        )
        mock_job_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_job_result
        
        service = JobService(mock_db)
        
        with pytest.raises(ValueError, match="cannot be cancelled"):
            await service.cancel_job(123, 1)

    @pytest.mark.asyncio
    async def test_cancel_job_wrong_user(self):
        """Test cancelling job with wrong user ID"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job_result.scalar_one_or_none.return_value = None  # No job for this user
        mock_db.execute.return_value = mock_job_result
        
        service = JobService(mock_db)
        
        result = await service.cancel_job(123, 999)  # Wrong user ID
        
        assert result is False


class TestJobServiceHTTPCommunication:
    """Test JobService HTTP communication with Go service"""

    @pytest.mark.asyncio
    async def test_send_job_to_go_service_success(self):
        """Test successful HTTP communication with Go service"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        service = JobService(mock_db)
        
        # Mock successful HTTP response
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "accepted"}
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            parameters = {
                "data_sources": ["https://api.example.com/data"],
                "filters": {"test": True}
            }
            
            job_id = await service.create_external_data_job(1, parameters)
            
            # Verify HTTP call was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            
            # Check URL
            assert "/api/v1/jobs/process" in call_args[1]["json"]["job_id"] is not None
            
            # Check payload
            json_payload = call_args[1]["json"]
            assert json_payload["user_id"] == 1
            assert json_payload["job_type"] == "external_data"
            assert json_payload["parameters"] == parameters

    @pytest.mark.asyncio
    async def test_send_job_to_go_service_http_error(self):
        """Test HTTP communication failure handling"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        
        # Mock job that will be created and then updated to failed
        mock_job = MagicMock()
        mock_job.id = 123
        mock_job.status = "queued"
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        service = JobService(mock_db)
        
        # Mock HTTP error
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            parameters = {"data_sources": ["https://api.example.com/data"]}
            
            job_id = await service.create_external_data_job(1, parameters)
            
            # Should still return job ID
            assert job_id == 123
            
            # Should have attempted to update job status to failed
            # (This depends on implementation details)

    @pytest.mark.asyncio
    async def test_send_job_to_go_service_timeout(self):
        """Test HTTP timeout handling"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        service = JobService(mock_db)
        
        # Mock timeout
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = asyncio.TimeoutError("Request timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            parameters = {"data_sources": ["https://api.example.com/data"]}
            
            job_id = await service.create_external_data_job(1, parameters)
            
            # Should handle timeout gracefully
            assert job_id == 123


class TestJobServiceDataHandling:
    """Test JobService data handling and serialization"""

    @pytest.mark.asyncio
    async def test_job_parameters_serialization(self):
        """Test job parameter JSON serialization"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        
        # Capture the job that gets added
        added_job = None
        def capture_job(job):
            nonlocal added_job
            added_job = job
            
        mock_db.add = capture_job
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        service = JobService(mock_db)
        
        # Mock HTTP call
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Complex parameters
            complex_parameters = {
                "data_sources": ["https://api.example.com/data"],
                "filters": {
                    "string": "test",
                    "number": 42,
                    "boolean": True,
                    "array": [1, 2, 3],
                    "nested": {"key": "value"}
                }
            }
            
            await service.create_external_data_job(1, complex_parameters)
            
            # Verify parameters were properly serialized
            assert added_job is not None
            stored_params = json.loads(added_job.parameters)
            assert stored_params == complex_parameters

    @pytest.mark.asyncio
    async def test_job_result_deserialization(self):
        """Test job result JSON deserialization"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        
        complex_result = {
            "api_results": [
                {"source": "api1", "data": {"items": [1, 2, 3]}},
                {"source": "api2", "data": {"total": 100}}
            ],
            "metadata": {
                "processed_at": "2023-01-01T00:00:00Z",
                "total_sources": 2
            }
        }
        
        mock_job = Job(
            id=123,
            user_id=1,
            job_type="external_data",
            status="completed",
            result=json.dumps(complex_result)
        )
        mock_job_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_job_result
        
        service = JobService(mock_db)
        
        job_data = await service.get_job_status(123)
        
        assert job_data["result"] == complex_result
        assert isinstance(job_data["result"]["api_results"], list)
        assert len(job_data["result"]["api_results"]) == 2


class TestJobServiceEdgeCases:
    """Test JobService edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_create_job_with_none_parameters(self):
        """Test job creation with None parameters"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        service = JobService(mock_db)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Should handle None parameters gracefully
            job_id = await service.create_external_data_job(1, None)
            
            assert job_id == 123

    @pytest.mark.asyncio
    async def test_create_job_with_empty_parameters(self):
        """Test job creation with empty parameters"""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = User(
            id=1, email="test@example.com", username="testuser"
        )
        mock_db.execute.return_value = mock_user_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda job: setattr(job, 'id', 123)

        service = JobService(mock_db)
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            # Empty parameters should be handled
            job_id = await service.create_external_data_job(1, {})
            
            assert job_id == 123

    @pytest.mark.asyncio
    async def test_get_job_status_with_database_error(self):
        """Test job status retrieval with database errors"""
        # Mock database session with error
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.execute.side_effect = Exception("Database connection lost")
        
        service = JobService(mock_db)
        
        with pytest.raises(Exception, match="Database connection lost"):
            await service.get_job_status(123)

    @pytest.mark.asyncio
    async def test_cancel_job_with_database_error(self):
        """Test job cancellation with database errors"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        mock_job_result = AsyncMock()
        mock_job = Job(
            id=123,
            user_id=1,
            job_type="external_data",
            status="queued"
        )
        mock_job_result.scalar_one_or_none.return_value = mock_job
        mock_db.execute.return_value = mock_job_result
        mock_db.commit.side_effect = Exception("Database error")
        
        service = JobService(mock_db)
        
        with pytest.raises(Exception, match="Database error"):
            await service.cancel_job(123, 1)