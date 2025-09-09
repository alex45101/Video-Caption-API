from fastapi import APIRouter
from datetime import datetime

from app.models import HealthResponse

router = APIRouter()


@router.get("/")
async def root():
    """
    Root endpoint for the API.

    Returns:
        dict: A welcome message for the Video Caption API.
    """
    return {"message": "Video Caption API - Welcome!"}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthResponse: An object indicating the API is healthy and the current timestamp.
    """
    # Return a simple health status and current server time
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now()
    )
