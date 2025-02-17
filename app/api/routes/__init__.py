from fastapi import APIRouter
from app.api.routes import jobs, health

router = APIRouter()

router.include_router(health.router, tags=["health"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])