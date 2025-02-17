from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from app.models.base import MongoModel


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: int = Field(default=0, ge=0, le=100)
    payload: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload")
    def validate_payload(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if len(str(value)) > 1_000_000:  # 1MB limit
            raise ValueError("Payload too large")
        return value


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    priority: Optional[int] = Field(None, ge=0, le=100)
    payload: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"


class Job(MongoModel):
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
                        "description": "Process customer data batch",
                        "status": "completed",
                        "priority": 1,
                        "created_at": "2025-02-17T10:00:00Z",
                        "updated_at": "2025-02-17T10:00:00Z",
                        "started_at": None,
                        "completed_at": None,
                        "result": None,
                        "error": None
                    }
                ],
                "total": 1,
                "skip": 0,
                "limit": 10
            }
        }