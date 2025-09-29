import json
import httpx
import structlog
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.job import Job
from app.models.user import User
from app.core.config import settings

logger = structlog.get_logger()

class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_external_data_job(self, user_id: int, parameters: Dict[str, Any]) -> int:
        """Create and queue an external data job."""
        logger.info("Creating external data job", user_id=user_id, parameters=parameters)
        
        # Verify user exists
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Create job record in database
        job = Job(
            user_id=user_id,
            job_type="external_data",
            status="queued",
            parameters=json.dumps(parameters)
        )
        
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        
        # Send job to Go service via HTTP (fire-and-forget)
        try:
            await self._send_job_to_go_service(job.id, user_id, parameters)
            logger.info("Job sent to Go service", job_id=job.id)
        except Exception as e:
            logger.error("Failed to send job to Go service", job_id=job.id, error=str(e))
            # Update job status to failed
            job.status = "failed"
            job.error_message = f"Failed to send to Go service: {str(e)}"
            await self.db.commit()
        
        return job.id

    async def _send_job_to_go_service(self, job_id: int, user_id: int, parameters: Dict[str, Any]):
        """Send job request to Go service."""
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "job_type": "external_data",
            "parameters": parameters
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.go_service_url}/api/v1/jobs/process",
                json=job_data,
                timeout=5.0  # Quick timeout - fire and forget
            )
            
            if response.status_code != 200:
                raise Exception(f"Go service returned status {response.status_code}: {response.text}")

    async def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get job status from database."""
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            return None
            
        job_data = {
            "id": job.id,
            "user_id": job.user_id,
            "job_type": job.job_type,
            "status": job.status,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message
        }
        
        # Parse result if available
        if job.result:
            try:
                job_data["result"] = json.loads(job.result)
            except json.JSONDecodeError:
                job_data["result"] = job.result
        else:
            job_data["result"] = None
            
        return job_data

    async def get_user_jobs(self, user_id: int, skip: int = 0, limit: int = 100) -> list:
        """Get all jobs for a user with pagination."""
        result = await self.db.execute(
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = result.scalars().all()
        
        job_list = []
        for job in jobs:
            job_data = {
                "id": job.id,
                "user_id": job.user_id,
                "job_type": job.job_type,
                "status": job.status,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message
            }
            
            # Parse result if available
            if job.result:
                try:
                    job_data["result"] = json.loads(job.result)
                except json.JSONDecodeError:
                    job_data["result"] = job.result
            else:
                job_data["result"] = None
                
            job_list.append(job_data)
        
        return job_list

    async def cancel_job(self, job_id: int, user_id: int) -> bool:
        """Cancel a job if it's still queued or processing."""
        result = await self.db.execute(
            select(Job).where(Job.id == job_id, Job.user_id == user_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            return False
            
        if job.status in ["completed", "failed", "cancelled"]:
            raise ValueError(f"Job {job_id} cannot be cancelled (status: {job.status})")
        
        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        await self.db.commit()
        
        logger.info("Job cancelled", job_id=job_id, user_id=user_id)
        return True