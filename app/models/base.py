### Data models and schemas:
### Database Models:
# - Base MongoDB models with timestamps
# - Proper type hints and validation
# - Schema versioning support
# - Serialization/deserialization logic

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class TimestampModel(BaseModel):
    """
    Base model with timestamp fields.
    Used as a base class for all models that need creation/update timestamps.
    """
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
        
class MongoModel(TimestampModel):
    """
    Base model for MongoDB documents.
    Includes common fields and configuration for MongoDB documents.
    """
    id: Optional[str] = Field(None, alias="_id")
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True