# Video Caption API

A full-stack project for generating and serving video captions via a RESTful API, with a web-based frontend for user interaction.

## Project Structure

```
Backend/
  main.py
  requirements.txt
  app/
    core/
    models/
    routes/
    services/
    utils/
    data/
    temp/
Frontend/
  html/
  scripts/
```

## Features
- Upload videos and generate captions automatically
- REST API for video and caption management
- Health check endpoint
- SQLite database for job and subtitle storage
- Frontend web interface for uploading and viewing captions

## Backend
- **Framework:** FastAPI (Python)
- **Database:** SQLite (via `jobs.db`)
- **Key files:**
  - `main.py`: FastAPI app entry point
  - `app/routes/`: API endpoints (health, video)
  - `app/services/`: Business logic (database, video processing)
  - `app/models/`: Pydantic models
  - `app/core/`: Configuration and settings

### Running the Backend
1. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
2. Start the server:
   ```sh
   uvicorn main:app --reload
   ```
   (Run from the `Backend` directory)

## Frontend
- **HTML/JS** web interface
- **Key files:**
  - `html/main.html`: Main UI
  - `scripts/api.js`: API interaction logic
  - `scripts/main.js`: UI logic

### Running the Frontend
Open `Frontend/html/main.html` in your browser. Make sure the backend server is running.

## API Endpoints
- `GET /`  
  Root endpoint. Returns a welcome message.

- `GET /health`  
  Health check endpoint. Returns API status and timestamp.

- `POST /api/v1/jobs/upload`  
  Upload a video for captioning.  
  **Form fields:**  
    - `video`: Video file (MP4, AVI, MOV, MKV, max 250MB)  
    - Subtitle options: `font_family`, `font_size`, `font_color`, `stroke_color`, `stroke_width`, `position`, `shadow`, `max_chars`, `max_duration`, `max_gap`

- `GET /api/v1/jobs/{job_id}/status`  
  Get the status and progress of a video processing job.

- `GET /api/v1/jobs/{job_id}/download`  
  Download the processed (captioned) video for a completed job.

## Data Storage
- Uploaded videos and temporary processing files are stored in `Backend/app/temp/`
- The SQLite database (`jobs.db`) is stored in `Backend/app/data/`

## Requirements
- Python 3.11+
- Node.js (for advanced frontend development, optional)

## License
MIT License

---

*Feel free to contribute or open issues!*
