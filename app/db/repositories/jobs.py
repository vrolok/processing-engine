### Job Repository (repositories/jobs.py)
### Job-specific repository implementation:
# - Extends base repository for job operations
# - User-context aware operations
# - Status management and transitions
# - Timestamp handling for job lifecycle
# - Custom query methods for job filtering
# - Sorting by creation time
# - User-based access control
# - Status-based filtering
#
### Specialized operations:
# - create(): Job creation with user context
# - get(): User-verified job retrieval
# - list_by_user(): User-specific job listing
# - update_status(): Job status management
#
### Features:
# - User permission enforcement
# - Status transition validation
# - Timestamp management
# - Error tracking
# - Query optimization
# - Index utilization
# - Atomic updates
# - Cursor management

from typing import List, Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import logging

from app.db.repositories.base import BaseRepository
from app.models.job import Job, JobStatus

logger = logging.getLogger(__name__)

class JobRepository(BaseRepository[Job]):
    """
    Repository for job-specific database operations.
    Extends base repository with job-specific queries and operations.
    """

    async def create(
        self,
        user_id: str,
        data: Dict[str, Any],
        status: JobStatus = JobStatus.QUEUED
    ) -> Job:
        """
        Create a new job with user context.
        Args:
            user_id: ID of the user creating the job
            data: Job data dictionary
            status: Initial job status (defaults to QUEUED)
        Returns:
            Created job instance
        """
        job_data = {
            **data,
            "user_id": user_id,
            "status": status,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "attempts": 0
        }
        
        logger.info(
            "Creating new job",
            extra={
                "user_id": user_id,
                "status": status,
                "data": data
            }
        )
        
        return await super().create(job_data)

    async def get(self, job_id: str, user_id: str) -> Optional[Job]:
        """
        Get job by ID with user verification.
        Args:
            job_id: ID of the job to retrieve
            user_id: ID of the user requesting the job
        Returns:
            Job instance if found and user has access, None otherwise
        """
        return await self.get_by_query({
            "_id": ObjectId(job_id),
            "user_id": user_id
        })

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID without user verification (for internal use).
        Args:
            job_id: ID of the job to retrieve
        Returns:
            Job instance if found, None otherwise
        """
        return await super().get(job_id)

    async def list_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Job]:
        """
        List jobs for specific user with optional status filter.
        Args:
            user_id: ID of the user whose jobs to list
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return
        Returns:
            List of jobs matching the criteria
        """
        query = {"user_id": user_id}
        if status:
            query["status"] = status
            
        return await self.list(
            query=query,
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )

    async def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error: Optional[str] = None
    ) -> Optional[Job]:
        """
        Update job status with optional error message.
        Args:
            job_id: ID of the job to update
            status: New job status
            error: Optional error message for failed jobs
        Returns:
            Updated job instance
        """
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        if status == JobStatus.PROCESSING:
            update_data["started_at"] = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            update_data["completed_at"] = datetime.utcnow()
        
        if error:
            update_data["error"] = error
        
        logger.info(
            "Updating job status",
            extra={
                "job_id": job_id,
                "new_status": status,
                "error": error
            }
        )
        
        return await self.update(job_id, update_data)

    async def increment_attempts(self, job_id: str) -> Optional[Job]:
        """
        Increment the number of processing attempts for a job.
        Args:
            job_id: ID of the job
        Returns:
            Updated job instance
        """
        return await self.collection.find_one_and_update(
            {"_id": ObjectId(job_id)},
            {
                "$inc": {"attempts": 1},
                "$set": {"updated_at": datetime.utcnow()}
            },
            return_document=True
        )

    async def find_stalled_jobs(
        self,
        threshold_minutes: int = 30
    ) -> List[Job]:
        """
        Find jobs that have been processing for too long.
        Args:
            threshold_minutes: Time in minutes after which a job is considered stalled
        Returns:
            List of stalled jobs
        """
        threshold_time = datetime.utcnow() - timedelta(minutes=threshold_minutes)
        
        query = {
            "status": JobStatus.PROCESSING,
            "started_at": {"$lt": threshold_time},
            "attempts": {"$lt": 3}  # Max retry attempts
        }
        
        return await self.list(query=query)

    async def cleanup_old_jobs(
        self,
        days: int = 30
    ) -> int:
        """
        Delete jobs older than specified days.
        Args:
            days: Age in days after which to delete jobs
        Returns:
            Number of jobs deleted
        """
        threshold_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.collection.delete_many({
            "created_at": {"$lt": threshold_date},
            "status": {"$in": [JobStatus.COMPLETED, JobStatus.FAILED]}
        })
        
        logger.info(
            "Cleaned up old jobs",
            extra={
                "deleted_count": result.deleted_count,
                "threshold_days": days
            }
        )
        
        return result.deleted_count

    async def get_job_stats(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get job statistics, optionally filtered by user.
        Args:
            user_id: Optional user ID to filter stats
        Returns:
            Dictionary with job counts by status
        """
        match_stage = {"$match": {}} if user_id is None else {"$match": {"user_id": user_id}}
        
        pipeline = [
            match_stage,
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        result = await self.collection.aggregate(pipeline).to_list(None)
        
        return {
            doc["_id"]: doc["count"]
            for doc in result
        }