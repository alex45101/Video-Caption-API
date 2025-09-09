from fastapi import APIRouter, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import os

from app.models import SubtitleOptions, JobStatus, UploadResponse
from app.services import create_job, pull_job_status, pull_job_download_url, background_video_processing
from app.services.video_service import TEMP_DIR

router = APIRouter()


@router.post("/jobs/upload", response_model=UploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    font_family: str = Form("Arial"),
    font_size: int = Form(24),
    font_color: str = Form("white"),
    stroke_color: str = Form("black"),
    stroke_width: int = Form(2),
    position: int = Form(1),
    shadow: bool = Form(False),
    max_chars: int = Form(30),
    max_duration: float = Form(2.5),
    max_gap: float = Form(1.5)
):
    """
    Upload a video file for subtitle processing.

    Accepts a video file and subtitle styling options, creates a processing job,
    saves the uploaded file, and starts background processing.

    Args:
        background_tasks (BackgroundTasks): FastAPI background task manager.
        video (UploadFile): The uploaded video file.
        font_family (str): Font family for subtitles.
        font_size (int): Font size for subtitles.
        font_color (str): Font color for subtitles.
        stroke_color (str): Stroke color for subtitles.
        stroke_width (int): Stroke width for subtitles.
        position (int): Subtitle position (1=bottom, 2=center, 3=top).
        shadow (bool): Whether to add shadow to subtitles.

    Returns:
        UploadResponse: Job ID, message, and status URL.
    """
    # Validate file type
    if not video.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    # Validate file size
    if (video.size / pow(1024, 2)) >= 250:
        raise HTTPException(status_code=400, detail="File must be 250 MB or less")

    # Build subtitle options from form data
    subtitle_options = SubtitleOptions(
        font=font_family,
        font_size=font_size,
        font_color=font_color,
        stroke_color=stroke_color,
        stroke_width=stroke_width,
        position_id=position,
        shadow=shadow,
        max_chars=max_chars,
        max_duration=max_duration,
        max_gap=max_gap
    )

    # Create a new job in the database
    job_data = create_job(video.filename, subtitle_options)
    job_id = job_data["Job_Id"]
    input_path = job_data["Input_Path"]
    output_path = job_data["Output_Path"]    

    # Save the uploaded video file to disk
    content = await video.read()
    with open(input_path, "wb") as f:
        f.write(content)

    # Start background processing for video captioning
    background_tasks.add_task(
        background_video_processing,
        job_id,
        input_path,
        output_path,
        subtitle_options
    )

    return UploadResponse(
        job_id=job_id,
        msg="Video uploaded successfully",
        status_url=f"/jobs/{job_id}/status"
    )


@router.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the status of a video processing job.

    Args:
        job_id (str): The unique job identifier.

    Returns:
        JobStatus: The current status and progress of the job.

    Raises:
        HTTPException: If the job is not found.
    """
    job_data = pull_job_status(job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_data

@router.get("/jobs/{job_id}/download", response_class=FileResponse)
async def download_job(job_id: str):
    """
    Download the processed (captioned) video for a completed job.

    Args:
        job_id (str): The unique job identifier.

    Returns:
        FileResponse: The processed video file for download.

    Raises:
        HTTPException: If the job is not found, not completed, or file is missing.
    """
    # Retrieve job information and output path
    job_data = pull_job_download_url(job_id)

    if not job_data:
        raise HTTPException(
            status_code=404, 
            detail="Job not found"
        )

    # Ensure the job is completed before allowing download
    if job_data.progress != 100 or job_data.status_id != 3:
        raise HTTPException(
            status_code=400, 
            detail=f"Video processing not completed. Current status: {job_data.status_name}"
        )

    # Check if the output file exists
    if not os.path.exists(job_data.output_path):
        raise HTTPException(
            status_code=404,
            detail="Processed video file not found"
        )
    
    # Return the processed video file as a download
    return FileResponse(
        path=job_data.output_path,
        filename=f"captioned_{Path(job_data.original_filename).stem}.mp4",
        media_type='video/mp4'
    )
