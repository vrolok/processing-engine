from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.db.mongodb import get_database
from app.core.security import verify_api_key

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    """
    return JSONResponse(
        content={"status": "healthy"},
        status_code=200
    )

@router.get("/health/deep")
async def deep_health_check(db=Depends(get_database)):
    """
    Deep health check including database connection.
    """
    try:
        # Check database connection
        await db.command("ping")
        
        return JSONResponse(
            content={
                "status": "healthy",
                "database": "connected",
                "services": {
                    "database": "up",
                    "api": "up"
                }
            },
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "services": {
                    "database": "down",
                    "api": "up"
                }
            },
            status_code=503
        )