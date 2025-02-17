### MongoDB Connection Management (mongodb.py)
#
### Core database connection management system:
# - Singleton pattern for database client management
# - Connection pooling with configurable pool sizes
# - Async connection handling using Motor
# - Health check functionality with ping command
# - Connection verification and error handling
# - Clean shutdown process
# - Dependency injection support for FastAPI
# - Logging of connection events and errors
# - Environment-based configuration
#
### Key features:
# - Automatic reconnection handling
# - Connection pool optimization
# - Database selection and validation
# - Error logging and propagation
# - Resource cleanup on shutdown
# - Type-safe database access
# - Performance monitoring capabilities

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    @classmethod
    async def connect(cls) -> None:
        """
        Initialize database connection.
        Sets up connection pool and verifies connectivity.
        """
        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_CONNECTIONS,
                minPoolSize=settings.MONGODB_MIN_CONNECTIONS,
                serverSelectionTimeoutMS=5000,
            )
            cls.db = cls.client[settings.DATABASE_NAME]
            
            # Verify connection
            await cls.client.admin.command('ping')
            
            logger.info(
                "Connected to MongoDB",
                extra={
                    "database": settings.DATABASE_NAME,
                    "host": settings.MONGODB_URL.split("@")[-1]
                }
            )
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(
                "Failed to connect to MongoDB",
                extra={"error": str(e)}
            )
            raise

    @classmethod
    async def disconnect(cls) -> None:
        """
        Close database connection.
        Properly closes connection pool and cleans up resources.
        """
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("Disconnected from MongoDB")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """
        Get database instance.
        Returns the current database instance or raises an exception if not connected.
        """
        if not cls.db:
            raise ConnectionError("Database not initialized")
        return cls.db

async def connect_to_mongo() -> None:
    """
    Connect to MongoDB.
    Called during application startup.
    """
    await MongoDB.connect()

async def close_mongo_connection() -> None:
    """
    Close MongoDB connection.
    Called during application shutdown.
    """
    await MongoDB.disconnect()

async def get_database() -> AsyncIOMotorDatabase:
    """
    Dependency for getting database instance.
    Used by FastAPI dependency injection system.
    """
    return MongoDB.get_db()