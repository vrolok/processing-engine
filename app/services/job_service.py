from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import Depends
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import json

from app.core.config import settings
from app.models.job import JobCreate, JobUpdate, JobResponse, JobStatus
from app.db.repositories.jobs import JobRepository

class JobService:
    def __init__(
        self,
        job_repository: JobRepository = Depends(),
        task_client: Optional[tasks_v2.CloudTasksClient] = None
    ):
        self.repository = job_repository
        self.task_client = task_client or tasks_v2.CloudTasksClient()
        self.parent = self.task_client.queue_path(
            settings.PROJECT_ID,
            settings.LOCATION,
            settings.QUEUE_NAME
        )

    async def create_job(self, job_create: JobCreate, user_id: str) -> JobResponse:
        """
        Create a new job and schedule it for processing.
        """
        # Create job in database
        job = await self.repository.create(
            user_id=user_id,
            data=job_create.dict(),
            status=JobStatus.QUEUED
        )

        # Schedule processing task
        await self._schedule_processing(str(job.id))

        return JobResponse.from_orm(job)

    async def get_job(self, job_id: str, user_id: str) -> Optional[JobResponse]:
        """
        Retrieve a specific job.
        """
        job = await self.repository.get(job_id, user_id)
        return JobResponse.from_orm(job) if job else None

    async def list_jobs(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[JobResponse]:
        """
        List jobs with pagination and optional status filter.
        """
        jobs = await self.repository.list(
            user_id=user_id,
            skip=skip,
            limit=limit,
            status=status
        )
        return [JobResponse.from_orm(job) for job in jobs]

    async def update_job(
        self,
        job_id: str,
        job_update: JobUpdate,
        user_id: str
    ) -> Optional[JobResponse]:
        """
        Update a specific job.
        """
        job = await self.repository.update(
            job_id=job_id,
            user_id=user_id,
            data=job_update.dict(exclude_unset=True)
        )
        return JobResponse.from_orm(job) if job else None

    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """
        Delete a specific job.
        """
        return await self.repository.delete(job_id, user_id)

    async def process_job(self, job_id: str) -> JobResponse:
        """
        Process a job (called by Cloud Tasks).
        Implements idempotent processing to handle potential retries.
        """
        # Get job
        job = await self.repository.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Check if job is already processed
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return JobResponse.from_orm(job)

        try:
            # Update status to processing
            job = await self.repository.update_status(
                job_id=job_id,
                status=JobStatus.PROCESSING
            )

            # Perform job processing logic here
            # This is where you'd implement the actual job processing
            # For example, calling external services, processing data, etc.
            processing_result = await self._process_job_logic(job)

            # Update job with results
            job = await self.repository.update(
                job_id=job_id,
                user_id=job.user_id,
                data={
                    "status": JobStatus.COMPLETED,
                    "result": processing_result,
                    "completed_at": datetime.utcnow()
                }
            )

        except Exception as e:
            # Update job as failed
            job = await self.repository.update(
                job_id=job_id,
                user_id=job.user_id,
                data={
                    "status": JobStatus.FAILED,
                    "error": str(e),
                    "completed_at": datetime.utcnow()
                }
            )
            raise

        return JobResponse.from_orm(job)

    async def _process_job_logic(self, job) -> dict:
        """
        Implement actual job processing logic here.
        This is a placeholder for the actual implementation.
        """
        # Simulate processing time
        await asyncio.sleep(2)
        return {"processed": True, "timestamp": datetime.utcnow().isoformat()}

    async def _schedule_processing(self, job_id: str, delay_seconds: int = 0):
        """
        Schedule a job for processing using Cloud Tasks.
        """
        # Create task
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{settings.CLOUD_RUN_URL}/api/v1/jobs/{job_id}/process",
                "oidc_token": {
                    "service_account_email": settings.SERVICE_ACCOUNT_EMAIL,
                }
            }
        }

        if delay_seconds > 0:
            # Add scheduling time if delay is specified
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(
                datetime.utcnow() + timedelta(seconds=delay_seconds)
            )
            task["schedule_time"] = timestamp

        try:
            # Create the task
            response = self.task_client.create_task(
                request={
                    "parent": self.parent,
                    "task": task
                }
            )
            return response
        except Exception as e:
            # Log error and re-raise
            logger.error(f"Failed to schedule task for job {job_id}: {str(e)}")
            raise