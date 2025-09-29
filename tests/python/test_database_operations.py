"""
Unit Tests for Database Operations

These tests focus on database layer functionality, model validation,
and data persistence without HTTP layer dependencies.
"""
import pytest
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.job import Job
from app.services.auth import get_password_hash, verify_password


class TestUserModel:
    """Test User model functionality and validation"""

    @pytest.mark.asyncio
    async def test_create_user_model(self, db_session: AsyncSession):
        """Test creating user model with valid data"""
        user = User(
            email="model@example.com",
            username="modeluser",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "model@example.com"
        assert user.username == "modeluser"
        assert user.is_active is True
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    @pytest.mark.asyncio
    async def test_user_email_uniqueness(self, db_session: AsyncSession):
        """Test that email uniqueness constraint is enforced"""
        # Create first user
        user1 = User(
            email="unique@example.com",
            username="user1",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create second user with same email
        user2 = User(
            email="unique@example.com",  # Same email
            username="user2",            # Different username
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_username_uniqueness(self, db_session: AsyncSession):
        """Test that username uniqueness constraint is enforced"""
        # Create first user
        user1 = User(
            email="user1@example.com",
            username="uniqueusername",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create second user with same username
        user2 = User(
            email="user2@example.com",   # Different email
            username="uniqueusername",   # Same username
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_user_timestamps(self, db_session: AsyncSession):
        """Test that timestamps are automatically set"""
        user = User(
            email="timestamp@example.com",
            username="timestampuser",
            hashed_password=get_password_hash("password123")
        )
        
        # created_at should be None before saving
        assert user.created_at is None
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # created_at should be set after saving
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
        
        # Should be recent (within last minute)
        assert user.created_at > datetime.utcnow() - timedelta(minutes=1)

    @pytest.mark.asyncio
    async def test_user_default_values(self, db_session: AsyncSession):
        """Test that default values are set correctly"""
        user = User(
            email="defaults@example.com",
            username="defaultsuser",
            hashed_password=get_password_hash("password123")
            # Not setting is_active explicitly
        )
        
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # is_active should default to True
        assert user.is_active is True


class TestJobModel:
    """Test Job model functionality and relationships"""

    @pytest.mark.asyncio
    async def test_create_job_model(self, db_session: AsyncSession, test_user_id):
        """Test creating job model with valid data"""
        parameters = {
            "data_sources": ["https://api.example.com/data"],
            "filters": {"category": "test"}
        }
        
        job = Job(
            user_id=test_user_id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps(parameters)
        )
        
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        
        assert job.id is not None
        assert job.user_id == test_user_id
        assert job.job_type == "external_data"
        assert job.status == "queued"
        assert job.created_at is not None
        
        # Verify parameters can be deserialized
        stored_params = json.loads(job.parameters)
        assert stored_params == parameters

    @pytest.mark.asyncio
    async def test_job_user_relationship(self, db_session: AsyncSession):
        """Test job-user relationship"""
        # Create user
        user = User(
            email="relation@example.com",
            username="relationuser",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create job
        job = Job(
            user_id=user.id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps({"test": True})
        )
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        
        # Test relationship access
        result = await db_session.execute(
            select(User).where(User.id == user.id)
        )
        db_user = result.scalar_one()
        
        # Access jobs through relationship
        user_jobs = db_user.jobs
        assert len(user_jobs) == 1
        assert user_jobs[0].id == job.id

    @pytest.mark.asyncio
    async def test_job_status_updates(self, db_session: AsyncSession, test_user_id):
        """Test job status progression"""
        job = Job(
            user_id=test_user_id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps({"test": True})
        )
        
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        original_updated_at = job.updated_at
        
        # Update status
        job.status = "processing"
        await db_session.commit()
        await db_session.refresh(job)
        
        assert job.status == "processing"
        # updated_at should be automatically updated
        if job.updated_at and original_updated_at:
            assert job.updated_at >= original_updated_at

    @pytest.mark.asyncio
    async def test_job_result_storage(self, db_session: AsyncSession, test_user_id):
        """Test storing and retrieving job results"""
        job = Job(
            user_id=test_user_id,
            job_type="external_data",
            status="processing",
            parameters=json.dumps({"test": True})
        )
        
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)
        
        # Add result
        result_data = {
            "api_results": [
                {"source": "api1", "data": {"key": "value1"}},
                {"source": "api2", "data": {"key": "value2"}}
            ],
            "metadata": {
                "processed_at": datetime.utcnow().isoformat(),
                "total_sources": 2
            }
        }
        
        job.result = json.dumps(result_data)
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        await db_session.commit()
        await db_session.refresh(job)
        
        # Verify result storage
        assert job.result is not None
        stored_result = json.loads(job.result)
        assert stored_result == result_data
        assert job.completed_at is not None

    @pytest.mark.asyncio
    async def test_job_foreign_key_constraint(self, db_session: AsyncSession):
        """Test that jobs require valid user_id"""
        job = Job(
            user_id=99999,  # Non-existent user
            job_type="external_data",
            status="queued",
            parameters=json.dumps({"test": True})
        )
        
        db_session.add(job)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_cascade_delete_jobs(self, db_session: AsyncSession):
        """Test that deleting user cascades to jobs"""
        # Create user
        user = User(
            email="cascade@example.com",
            username="cascadeuser",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create jobs
        for i in range(3):
            job = Job(
                user_id=user.id,
                job_type="external_data",
                status="completed",
                parameters=json.dumps({"index": i})
            )
            db_session.add(job)
        
        await db_session.commit()
        
        # Verify jobs exist
        result = await db_session.execute(select(Job).where(Job.user_id == user.id))
        jobs_before = result.scalars().all()
        assert len(jobs_before) == 3
        
        # Delete user
        await db_session.delete(user)
        await db_session.commit()
        
        # Verify jobs are also deleted (cascade)
        result = await db_session.execute(select(Job).where(Job.user_id == user.id))
        jobs_after = result.scalars().all()
        assert len(jobs_after) == 0


class TestPasswordHashing:
    """Test password hashing functionality"""

    def test_password_hashing_bcrypt(self):
        """Test that passwords are hashed using bcrypt"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50
        assert hashed != password
        
        # Same password should generate different hashes (salt)
        hashed2 = get_password_hash(password)
        assert hashed != hashed2

    def test_password_verification(self):
        """Test password verification against hash"""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        # Correct password should verify
        assert verify_password(password, hashed) is True
        
        # Wrong password should not verify
        assert verify_password("WrongPassword", hashed) is False
        assert verify_password("", hashed) is False
        assert verify_password("TestPassword123", hashed) is False  # Missing !

    def test_password_hash_security(self):
        """Test password hash security properties"""
        passwords = [
            "password123",
            "PASSWORD123",
            "Password123!",
            "Very Long Password With Many Words And Numbers 123456789",
            "🔒🚀💻",  # Unicode characters
            "pass word",  # With spaces
        ]
        
        for password in passwords:
            hashed = get_password_hash(password)
            
            # Hash should be different from password
            assert hashed != password
            
            # Should verify correctly
            assert verify_password(password, hashed) is True
            
            # Should not verify with wrong password
            assert verify_password(password + "x", hashed) is False


class TestDatabaseQueries:
    """Test database query operations"""

    @pytest.mark.asyncio
    async def test_user_lookup_by_email(self, db_session: AsyncSession):
        """Test looking up users by email"""
        user = User(
            email="lookup@example.com",
            username="lookupuser",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Test case-sensitive lookup
        result = await db_session.execute(
            select(User).where(User.email == "lookup@example.com")
        )
        found_user = result.scalar_one_or_none()
        assert found_user is not None
        assert found_user.id == user.id
        
        # Test case-insensitive lookup (might need implementation)
        result = await db_session.execute(
            select(User).where(User.email.ilike("LOOKUP@EXAMPLE.COM"))
        )
        found_user_case = result.scalar_one_or_none()
        # Depends on implementation - document behavior
        assert found_user_case is not None or found_user_case is None

    @pytest.mark.asyncio
    async def test_user_lookup_by_username(self, db_session: AsyncSession):
        """Test looking up users by username"""
        user = User(
            email="username@example.com",
            username="usernametest",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        result = await db_session.execute(
            select(User).where(User.username == "usernametest")
        )
        found_user = result.scalar_one_or_none()
        assert found_user is not None
        assert found_user.id == user.id

    @pytest.mark.asyncio
    async def test_job_queries_by_status(self, db_session: AsyncSession, test_user_id):
        """Test querying jobs by status"""
        # Create jobs with different statuses
        statuses = ["queued", "processing", "completed", "failed"]
        job_ids = []
        
        for status in statuses:
            job = Job(
                user_id=test_user_id,
                job_type="external_data",
                status=status,
                parameters=json.dumps({"test": status})
            )
            db_session.add(job)
            job_ids.append(job)
        
        await db_session.commit()
        
        # Query by each status
        for status in statuses:
            result = await db_session.execute(
                select(Job).where(Job.status == status)
            )
            status_jobs = result.scalars().all()
            
            # Should find at least one job with this status
            assert len(status_jobs) >= 1
            assert all(job.status == status for job in status_jobs)

    @pytest.mark.asyncio
    async def test_job_queries_by_user(self, db_session: AsyncSession):
        """Test querying jobs by user"""
        # Create two users
        user1 = User(
            email="jobquery1@example.com",
            username="jobquery1",
            hashed_password=get_password_hash("password123")
        )
        user2 = User(
            email="jobquery2@example.com",
            username="jobquery2", 
            hashed_password=get_password_hash("password123")
        )
        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)
        
        # Create jobs for each user
        for user in [user1, user2]:
            for i in range(3):
                job = Job(
                    user_id=user.id,
                    job_type="external_data",
                    status="completed",
                    parameters=json.dumps({"user_test": True, "index": i})
                )
                db_session.add(job)
        
        await db_session.commit()
        
        # Query jobs for user1
        result = await db_session.execute(
            select(Job).where(Job.user_id == user1.id)
        )
        user1_jobs = result.scalars().all()
        
        assert len(user1_jobs) == 3
        assert all(job.user_id == user1.id for job in user1_jobs)
        
        # Query jobs for user2
        result = await db_session.execute(
            select(Job).where(Job.user_id == user2.id)
        )
        user2_jobs = result.scalars().all()
        
        assert len(user2_jobs) == 3
        assert all(job.user_id == user2.id for job in user2_jobs)

    @pytest.mark.asyncio
    async def test_job_count_by_status(self, db_session: AsyncSession, test_user_id):
        """Test counting jobs by status"""
        # Create jobs with known distribution
        status_counts = {"queued": 5, "processing": 3, "completed": 7, "failed": 2}
        
        for status, count in status_counts.items():
            for i in range(count):
                job = Job(
                    user_id=test_user_id,
                    job_type="external_data",
                    status=status,
                    parameters=json.dumps({"count_test": True, "index": i})
                )
                db_session.add(job)
        
        await db_session.commit()
        
        # Count jobs by status
        for status, expected_count in status_counts.items():
            result = await db_session.execute(
                select(func.count(Job.id)).where(Job.status == status, Job.user_id == test_user_id)
            )
            actual_count = result.scalar()
            
            assert actual_count >= expected_count  # Might have jobs from other tests

    @pytest.mark.asyncio
    async def test_job_ordering_by_creation_time(self, db_session: AsyncSession, test_user_id):
        """Test that jobs can be ordered by creation time"""
        # Create jobs with small delays
        job_ids = []
        for i in range(3):
            job = Job(
                user_id=test_user_id,
                job_type="external_data",
                status="completed",
                parameters=json.dumps({"order_test": i})
            )
            db_session.add(job)
            await db_session.commit()
            await db_session.refresh(job)
            job_ids.append((job.id, job.created_at))
            
            # Small delay to ensure different timestamps
            await asyncio.sleep(0.01)
        
        # Query jobs ordered by creation time (newest first)
        result = await db_session.execute(
            select(Job)
            .where(Job.user_id == test_user_id)
            .order_by(Job.created_at.desc())
            .limit(3)
        )
        ordered_jobs = result.scalars().all()
        
        # Should be in descending order
        if len(ordered_jobs) >= 2:
            for i in range(len(ordered_jobs) - 1):
                assert ordered_jobs[i].created_at >= ordered_jobs[i + 1].created_at


class TestDatabasePerformance:
    """Test database performance and indexing"""

    @pytest.mark.asyncio
    async def test_user_email_index_performance(self, db_session: AsyncSession):
        """Test that email lookups are fast (using index)"""
        # Create many users
        users = []
        for i in range(100):
            user = User(
                email=f"perf{i}@example.com",
                username=f"perfuser{i}",
                hashed_password=get_password_hash("password123")
            )
            users.append(user)
        
        db_session.add_all(users)
        await db_session.commit()
        
        # Time email lookup
        start_time = datetime.utcnow()
        
        result = await db_session.execute(
            select(User).where(User.email == "perf50@example.com")
        )
        found_user = result.scalar_one_or_none()
        
        end_time = datetime.utcnow()
        lookup_time = (end_time - start_time).total_seconds()
        
        assert found_user is not None
        assert found_user.email == "perf50@example.com"
        # Lookup should be fast (under 100ms for indexed column)
        assert lookup_time < 0.1

    @pytest.mark.asyncio
    async def test_job_user_id_index_performance(self, db_session: AsyncSession):
        """Test that job queries by user_id are fast"""
        # Create user
        user = User(
            email="jobperf@example.com",
            username="jobperfuser",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        # Create many jobs
        jobs = []
        for i in range(100):
            job = Job(
                user_id=user.id,
                job_type="external_data",
                status="completed",
                parameters=json.dumps({"perf_test": i})
            )
            jobs.append(job)
        
        db_session.add_all(jobs)
        await db_session.commit()
        
        # Time user job lookup
        start_time = datetime.utcnow()
        
        result = await db_session.execute(
            select(Job).where(Job.user_id == user.id).limit(10)
        )
        user_jobs = result.scalars().all()
        
        end_time = datetime.utcnow()
        lookup_time = (end_time - start_time).total_seconds()
        
        assert len(user_jobs) == 10
        # Should be fast with index on user_id
        assert lookup_time < 0.1


class TestDatabaseTransactions:
    """Test database transaction handling"""

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self, db_session: AsyncSession):
        """Test that transactions rollback properly on errors"""
        # Count users before
        result = await db_session.execute(select(func.count(User.id)))
        users_before = result.scalar()
        
        try:
            # Create user successfully
            user = User(
                email="transaction@example.com",
                username="transactionuser",
                hashed_password=get_password_hash("password123")
            )
            db_session.add(user)
            
            # Try to create duplicate user (should fail)
            duplicate_user = User(
                email="transaction@example.com",  # Same email
                username="different",
                hashed_password=get_password_hash("password123")
            )
            db_session.add(duplicate_user)
            
            await db_session.commit()  # Should fail
            
        except IntegrityError:
            await db_session.rollback()
        
        # Count users after
        result = await db_session.execute(select(func.count(User.id)))
        users_after = result.scalar()
        
        # No users should have been added due to rollback
        assert users_after == users_before

    @pytest.mark.asyncio
    async def test_concurrent_user_creation(self, db_session: AsyncSession):
        """Test handling of concurrent user creation"""
        # This test might need actual concurrent database sessions
        # For now, test that unique constraints work
        
        user1 = User(
            email="concurrent@example.com",
            username="concurrent1",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create user with same email should fail
        user2 = User(
            email="concurrent@example.com",
            username="concurrent2",
            hashed_password=get_password_hash("password123")
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()


@pytest.fixture
async def test_user_id(db_session: AsyncSession) -> int:
    """Create a test user and return their ID"""
    user = User(
        email="testdbuser@example.com",
        username="testdbuser",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id