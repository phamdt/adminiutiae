from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta
from typing import List

from app.db.database import get_db
from app.schemas.user import UserCreate, UserResponse, UserLogin, Token
from app.schemas.job import ExternalDataRequest, JobResponse, JobStatusResponse
from app.models.user import User
from app.services.auth import (
    get_password_hash, 
    authenticate_user, 
    create_access_token,
    get_user_by_username
)
from app.services.job_service import JobService
from app.api.dependencies import get_current_active_user
from app.core.config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter()

# User endpoints
@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user."""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    result = await db.execute(select(User).where(User.username == user.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    logger.info("User created", user_id=db_user.id, username=db_user.username)
    return db_user

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get user by ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.get("/users/", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """List users with pagination."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users

# Authentication endpoints
@router.post("/auth/login", response_model=Token)
async def login(user_login: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return access token."""
    user = await authenticate_user(db, user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    logger.info("User logged in", user_id=user.id, username=user.username)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user

# Job endpoints
@router.post("/users/{user_id}/external-data", status_code=status.HTTP_202_ACCEPTED)
async def create_external_data_job(
    user_id: int,
    request: ExternalDataRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create an external data fetching job."""
    # Verify user exists and matches current user (or admin check)
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create jobs for this user"
        )
    
    job_service = JobService(db)
    
    try:
        job_id = await job_service.create_external_data_job(
            user_id=user_id,
            parameters=request.dict()
        )
        
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "External data fetching job has been queued"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to create job", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )

@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get job status and results."""
    job_service = JobService(db)
    job = await job_service.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if user owns this job (or is admin)
    if job["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job"
        )
    
    return job

@router.get("/users/{user_id}/jobs", response_model=List[JobResponse])
async def get_user_jobs(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all jobs for a user."""
    # Check authorization
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view jobs for this user"
        )
    
    job_service = JobService(db)
    jobs = await job_service.get_user_jobs(user_id, skip, limit)
    return jobs

@router.post("/jobs/{job_id}/cancel", response_model=JobStatusResponse)
async def cancel_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a job."""
    job_service = JobService(db)
    
    try:
        success = await job_service.cancel_job(job_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job_id,
            "status": "cancelled",
            "message": "Job has been cancelled"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error("Failed to cancel job", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job"
        )

@router.get("/jobs/{job_id}/results")
async def get_job_results(
    job_id: int,
    format: str = "json",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed job results."""
    job_service = JobService(db)
    job = await job_service.get_job_status(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check authorization
    if job["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this job"
        )
    
    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed (status: {job['status']})"
        )
    
    if format == "json":
        return {
            "results": job["result"],
            "metadata": {
                "job_id": job_id,
                "completed_at": job["completed_at"],
                "job_type": job["job_type"]
            }
        }
    elif format == "csv":
        # For CSV format, you would implement CSV conversion here
        # This is a simplified version
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            content="CSV format not implemented yet",
            media_type="text/csv"
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")