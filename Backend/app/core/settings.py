import os
from pathlib import Path

# Datetime format string used throughout the application for consistency
FROMAT_DATETIME_STRING = "%Y-%m-%d %H:%M:%S.%f"

# Detect if the application is running inside a Docker container
RUNNING_IN_DOCKER = os.path.exists('/.dockerenv')

# Set the base directory depending on the environment (Docker or local)
if RUNNING_IN_DOCKER:
    BASE_DIR = Path("/app")
else:
    # Go up three levels from this file to reach the project root
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    
# Directory for storing the SQLite database file
DATABASE_DIR = BASE_DIR / "data"
DATABASE_DIR.mkdir(exist_ok=True) # Ensure the directory exists

# Path to the SQLite database file
DB_PATH = DATABASE_DIR / "jobs.db"

# Directory for storing temporary files (can be overridden by environment variable)
TEMP_DIR = Path(os.environ.get("TEMP_DIR", BASE_DIR / "temp" / "video_captioning"))

# Directory for storing generated subtitle files (can be overridden by environment variable)
SUBTITLE_DIR = Path(os.environ.get("SUBTITLE_DIR", BASE_DIR / "data" / "subtitles"))

# Ensure the temp and subtitle directories exist
TEMP_DIR.mkdir(parents=True, exist_ok=True)
SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)