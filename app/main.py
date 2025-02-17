### FastAPI Application:
# - Configures FastAPI with proper settings
# - Sets up middleware stack
# - Initializes authentication
# - Configures CORS
# - Manages database connections
# - Implements startup/shutdown handlers
# - Sets up logging
# - Registers route handlers
# - Configures OpenAPI documentation
# - Implements health checks
# - Provides production-ready server setup

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    custom_exception_handler
)
from app.core.middleware import (
    error_handler_middleware,
    logging_middleware
)
from app.api.routes import router as api_router
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.utils.logging import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

def create_application() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs" if settings.SHOW_DOCS else None,
        redoc_url="/redoc" if settings.SHOW_DOCS else None,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(BaseHTTPMiddleware, dispatch=error_handler_middleware)
    app.add_middleware(BaseHTTPMiddleware, dispatch=logging_middleware)

    # Exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, custom_exception_handler)

    # Event handlers
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting up application...")
        await connect_to_mongo()

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down application...")
        await close_mongo_connection()

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    return app

# Create application instance
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )