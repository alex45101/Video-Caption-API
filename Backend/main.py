from app.core.config import create_app
from app.routes import video_routes, health_routes

import sqlite3

# Create the FastAPI app
app = create_app()

# Include routers 
app.include_router(health_routes.router, tags=["health"])
app.include_router(video_routes.router, prefix="/api/v1", tags=["video"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)