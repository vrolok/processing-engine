### Core application infrastructure:
### Middleware (middleware.py):
# - Request/response logging
# - Error handling middleware
# - Performance monitoring
# - Request context tracking

import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.exception("Unhandled exception occurred")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected error occurred",
                        "status": 500
                    }
                }
            )

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "method": request.method,
                "url": str(request.url),
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
            }
        )
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "processing_time": process_time,
            }
        )
        
        response.headers["X-Process-Time"] = str(process_time)
        return response

async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    middleware = ErrorHandlerMiddleware(call_next)
    return await middleware.dispatch(request, call_next)

async def logging_middleware(request: Request, call_next: Callable) -> Response:
    middleware = LoggingMiddleware(call_next)
    return await middleware.dispatch(request, call_next)