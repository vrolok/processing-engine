### Data models and schemas:
### Job Models:
# - JobCreate: Input validation for job creation
# - JobUpdate: Partial update schema
# - JobResponse: API response format
# - JobStatus: Enumeration of possible job states
# - JobList: Paginated job list response

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime

from app.models.base import MongoModel

class JobStatus(str, Enum):
    """
    Enumeration of possible job states.
    Provides type-safe status values and transitions.
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JobCreate(BaseModel):
    """
    Schema for job creation requests.
    Validates input data for new jobs.
    """
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: int = Field(default=0, ge=0, le=100)
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("payload")
    def validate_payload(cls, v):
        """Ensure payload is serializable and not too large"""
        if len(str(v)) > 1_000_000:  # 1MB limit
            raise ValueError("Payload too large")
        return v

class JobUpdate(BaseModel):
    """
    Schema for job update requests.
    Allows partial updates of job fields.
    """
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[int] = Field(None, ge=0, le=100)
    payload: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "forbid"

class Job(MongoModel):
    """
    Internal job model for database operations.
    Represents the complete job document structure.
    """
    title: str
    description: Optional[str] = None
    status: JobStatus = Field(default=JobStatus.QUEUED)
    priority: int = 0
    payload: Dict[str, Any] = Field(default_factory=dict)
    user_id: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = Field(default=0, ge=0)
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Data Processing Job",
                "description": "Process customer data batch",
                "status": "queued",
                "priority": 1,
                "payload": {"batch_id": "123", "customer_count": 1000},
                "user_id": "user123"
            }
        }

class JobResponse(BaseModel):
    """
    API response model for jobs.
    Controls what job data is exposed via the API.
    """
    id: str
    title: str
    description: Optional[str]
    status: JobStatus
    priority: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    
    class Config:
        orm_mode = True

class JobList(BaseModel):
    """
    Paginated list of jobs response.
    Includes metadata for pagination.
    """
    items: List[JobResponse]
    total: int
    skip: int
    limit: int
    
    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "job123",
                        "title": "Data Processing Job",
                        "status": "completed",
                        "priority": 1,
                        "created_at": "2025-02-17T10:00:00Z"
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 10
            }
        }