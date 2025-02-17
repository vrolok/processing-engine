from typing import List
from pydantic import BaseModel, EmailStr, Field

from app.models.base import MongoModel

class User(MongoModel):
    """
    Internal user model for database operations.
    Represents the user document structure.
    """
    email: EmailStr
    name: str
    roles: List[str] = Field(default_factory=list)
    is_active: bool = True
    azure_id: str
    
    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "roles": ["user"],
                "azure_id": "azure123"
            }
        }

class UserResponse(BaseModel):
    """
    API response model for users.
    Controls what user data is exposed via the API.
    """
    id: str
    email: EmailStr
    name: str
    roles: List[str]
    
    class Config:
        orm_mode = True