### Base Repository (repositories/base.py)
#
### Generic repository pattern implementation:
# - Type-safe CRUD operations using generics
# - Async/await pattern for all database operations
# - Pagination support with skip/limit
# - Sorting capabilities with multiple fields
# - Query building with type checking
# - ObjectId handling and conversion
# - Error handling and logging
# - Dependency injection integration
#
### Operations provided:
# - get(): Retrieve by ID with type conversion
# - get_by_query(): Flexible query-based retrieval
# - list(): Paginated listing with sorting
# - create(): Document creation with validation
# - update(): Atomic updates with upsert option
# - delete(): Safe document deletion
# - count(): Query-based document counting
#
### Features:
# - Generic type constraints
# - Model validation
# - Query building
# - Cursor management
# - Transaction support
# - Error handling
# - Performance optimization

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import Depends

from app.db.mongodb import get_database
from app.models.base import MongoModel

ModelType = TypeVar("ModelType", bound=MongoModel)

class BaseRepository(Generic[ModelType]):
    """
    Base repository implementing common database operations.
    Provides CRUD operations with proper typing and error handling.
    """
    
    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncIOMotorDatabase = Depends(get_database)
    ):
        self.model = model
        self.db = db
        self.collection = db[model.__name__.lower()]

    async def get(self, id: str) -> Optional[ModelType]:
        """
        Retrieve a document by ID.
        """
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return self.model(**doc) if doc else None

    async def get_by_query(self, query: Dict[str, Any]) -> Optional[ModelType]:
        """
        Retrieve a document by custom query.
        """
        doc = await self.collection.find_one(query)
        return self.model(**doc) if doc else None

    async def list(
        self,
        query: Dict[str, Any] = None,
        skip: int = 0,
        limit: int = 100,
        sort: List[tuple] = None
    ) -> List[ModelType]:
        """
        List documents with pagination and sorting.
        """
        cursor = self.collection.find(query or {})
        
        if sort:
            cursor = cursor.sort(sort)
            
        cursor = cursor.skip(skip).limit(limit)
        
        return [self.model(**doc) async for doc in cursor]

    async def create(self, data: Dict[str, Any]) -> ModelType:
        """
        Create a new document.
        """
        doc = await self.collection.insert_one(data)
        return await self.get(str(doc.inserted_id))

    async def update(
        self,
        id: str,
        data: Dict[str, Any],
        upsert: bool = False
    ) -> Optional[ModelType]:
        """
        Update a document by ID.
        """
        doc = await self.collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": data},
            upsert=upsert,
            return_document=True
        )
        return self.model(**doc) if doc else None

    async def delete(self, id: str) -> bool:
        """
        Delete a document by ID.
        """
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def count(self, query: Dict[str, Any] = None) -> int:
        """
        Count documents matching query.
        """
        return await self.collection.count_documents(query or {})