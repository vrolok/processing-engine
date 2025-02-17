from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

class TimestampModel(BaseModel):
    """Base model with timestamp fields."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

class MongoModel(TimestampModel):
    """Base model for MongoDB documents."""
    id: Optional[str] = Field(None, alias="_id")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True