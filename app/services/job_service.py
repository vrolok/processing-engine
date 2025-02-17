from datetime import datetime, timedelta, timezone
import asyncio
from typing import List, Optional
from fastapi import Depends
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import json
import logging

from app.core.config import settings
from app.models.job import JobCreate, JobUpdate, JobResponse, JobStatus
from app.db.repositories.jobs import JobRepository

logger = logging.getLogger(__name__)


class JobService:
    def __init__(
        self,
        job_repository: JobRepository = Depends(),
        task_client: Optional[tasks_v2.CloudTasksClient] = None,
    ):
        self.repository = job_repository
        self.task_client = task_client or tasks_v2.CloudTasksClient()
        self.parent = self.task_client.queue_path(
            settings.PROJECT_ID, settings.LOCATION, settings.QUEUE_NAME
        )

    async def create_job(self, job_create: JobCreate, user_id: str) -> JobResponse:
        """
        Create a new job and schedule it for processing.
        """
        # Create job in the database with timestamps using UTC with timezone awareness
        job = await self.repository.create(
            user_id=user_id,
            data=job_create.model_dump(),  # Using model_dump instead of dict() for pydantic v2
            status=JobStatus.QUEUED,
        )
        # Schedule processing task via Cloud Tasks
        await self._schedule_processing(str(job.id))
        # Using model_validate (pydantic v2) in place of from_orm
        return JobResponse.model_validate(job)

    async def get_job(self, job_id: str, user_id: str) -> Optional[JobResponse]:
        """
        Retrieve a specific job.
        """
        job = await self.repository.get(job_id, user_id)
        if job:
            return JobResponse.model_validate(job)
        return None

    async def list_jobs(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> List[JobResponse]:
        """
        List jobs with pagination and optional status filter.
        """
        jobs = await self.repository.list_by_user(
            user_id=user_id, status=status, skip=skip, limit=limit
        )
        return [JobResponse.model_validate(job) for job in jobs]

    async def update_job(
        self, job_id: str, job_update: JobUpdate, user_id: str
    ) -> Optional[JobResponse]:
        """
        Update a specific job.
        """
        update_data = job_update.model_dump(exclude_unset=True)
        # Note: The repository.update method in BaseRepository does not support user validation.
        # Ensure that the repository implementation enforces user ownership if required.
        job = await self.repository.update(job_id, update_data)
        if job and job.user_id == user_id:
            return JobResponse.model_validate(job)
        return None

    async def delete_job(self, job_id: str, user_id: str) -> bool:
        """
        Delete a specific job.
        """
        # User verification should be handled in the repository if necessary.
        return await self.repository.delete(job_id)

    async def process_job(self, job_id: str) -> JobResponse:
        """
        Process a job (called by Cloud Tasks).
        Implements idempotent processing to handle potential retries.
        """
        job = await self.repository.get_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            return JobResponse.model_validate(job)

        try:
            # Update status to processing
            job = await self.repository.update_status(
                job_id=job_id, status=JobStatus.PROCESSING
            )
            # Execute the actual job processing logic
            processing_result = await self._process_job_logic(job)
            # Update job with processing results
            job = await self.repository.update(
                job_id,
                {
                    "status": JobStatus.COMPLETED,
                    "result": processing_result,
                    "completed_at": datetime.now(timezone.utc),
                },
            )
        except Exception as e:
            # Update job status as failed if an exception occurs
            job = await self.repository.update(
                job_id,
                {
                    "status": JobStatus.FAILED,
                    "error": str(e),
                    "completed_at": datetime.now(timezone.utc),
                },
            )
            raise

        return JobResponse.model_validate(job)

    async def _process_job_logic(self, job) -> dict:
        """
        Implement actual job processing logic here.
        This is a placeholder for real processing code.
        """
        await asyncio.sleep(2)
        return {"processed": True, "timestamp": datetime.now(timezone.utc).isoformat()}

    async def _schedule_processing(self, job_id: str, delay_seconds: int = 0):
        """
        Schedule a job for processing using Cloud Tasks.
        """
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{settings.CLOUD_RUN_URL}/api/v1/jobs/{job_id}/process",
                "oidc_token": {
                    "service_account_email": settings.SERVICE_ACCOUNT_EMAIL,
                },
            }
        }

        if delay_seconds > 0:
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(datetime.now(timezone.utc) + timedelta(seconds=delay_seconds))
            task["schedule_time"] = timestamp

        try:
            response = self.task_client.create_task(
                request={"parent": self.parent, "task": task}
            )
            return response
        except Exception as e:
            logger.error(f"Failed to schedule task for job {job_id}: {str(e)}")
            raise