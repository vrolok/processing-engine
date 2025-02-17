import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    custom_exception_handler,
)
from app.core.middleware import error_handler_middleware, logging_middleware
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.utils.logging import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    await connect_to_mongo()
    yield
    logger.info("Shutting down application...")
    await close_mongo_connection()

def create_application() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application.
    Uses a lifespan context for startup and shutdown events.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs" if settings.SHOW_DOCS else None,
        redoc_url="/redoc" if settings.SHOW_DOCS else None,
        lifespan=lifespan,
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

    # Register exception handlers
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, custom_exception_handler)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    return app

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