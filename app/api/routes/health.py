from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.db.mongodb import get_database

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    """
    return JSONResponse(content={"status": "healthy"}, status_code=200)

@router.get("/health/ready")
async def ready_health_check(db=Depends(get_database)):
    """
    Ready health check endpoint including database connectivity.
    """
    try:
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