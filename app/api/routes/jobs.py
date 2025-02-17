from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.models.job import JobCreate, JobResponse, JobUpdate, JobList
from app.services.job_service import JobService

router = APIRouter()

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job: JobCreate,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends()
) -> JobResponse:
    """
    Create a new job.
    """
    try:
        return await job_service.create_job(job, current_user["id"])
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends()
) -> JobResponse:
    """
    Get a specific job by ID.
    """
    job = await job_service.get_job(job_id, current_user["id"])
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job

@router.get("/", response_model=JobList)
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends()
) -> JobList:
    """
    List jobs with pagination and an optional status filter.
    """
    jobs = await job_service.list_jobs(
        user_id=current_user["id"],
        skip=skip,
        limit=limit,
        status=status
    )
    return JobList(items=jobs, total=len(jobs), skip=skip, limit=limit)

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends()
) -> JobResponse:
    """
    Update a specific job.
    """
    job = await job_service.update_job(job_id, job_update, current_user["id"])
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    return job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    job_service: JobService = Depends()
) -> None:
    """
    Delete a specific job.
    """
    success = await job_service.delete_job(job_id, current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

@router.post("/{job_id}/process", response_model=JobResponse)
async def process_job(
    job_id: str,
    job_service: JobService = Depends()
) -> JobResponse:
    """
    Internal endpoint to process a job (called by Cloud Tasks).
    """
    try:
        return await job_service.process_job(job_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )