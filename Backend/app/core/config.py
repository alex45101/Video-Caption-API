import asyncio
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services import cleanup_temp_files


async def lifespan(app: FastAPI):
    """
    Handles FastAPI application lifespan events.

    This function is called at startup and shutdown of the FastAPI app.
    On startup, it initializes the database, cleans up temporary files,
    and starts the JobWatchdog background task.
    On shutdown, the JobWatchdog task is cancelled gracefully.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None
    """
    # Startup: initialize database and clean temp files
    from app.services.database import init_database
    from app.services.job_monitor import start_job_watchdog
    from app.services.job_retry import start_retry_agent
    from app.services.disk_guardian import start_disk_guardian

    init_database()
    cleanup_temp_files()

    if not os.path.exists('/.dockerenv'):
        try:
            from moviepy.config import change_settings
            change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})
            print("ImageMagik path configured for local dev")
        except Exception as e:
            print(f"Could not configure ImageMagick: {e}")

    # Start background tasks
    watchdog_task = asyncio.create_task(start_job_watchdog())      # detects stuck jobs
    retry_task = asyncio.create_task(start_retry_agent())          # retries transient failures
    disk_task = asyncio.create_task(start_disk_guardian())         # frees disk when space is low

    yield

    # Shutdown
    for task in (watchdog_task, retry_task, disk_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application instance.

    Sets up API metadata, attaches the lifespan handler, and configures CORS middleware.

    Returns:
        FastAPI: The configured FastAPI application.
    """
    app = FastAPI(
        title="Video Captioning API",
        version="1.0.0",
        description="API for adding subtitles to videos",
        lifespan=lifespan,
        redirect_slashes=False
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    return app
