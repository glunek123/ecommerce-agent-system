from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "service": "ecommerce-agent"}


@router.get("/ready")
async def readiness_check():
    return {"status": "ready"}
