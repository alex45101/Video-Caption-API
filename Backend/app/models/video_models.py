from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class JobCreation(BaseModel):
    """
    Represents the metadata required to create a new video captioning job.

    Attributes:
        job_id (str): Unique identifier for the job.
        status_id (int): Current status ID of the job.
        progress (int): Progress percentage (0-100).
        created_at (datetime): Timestamp when the job was created.
        input_path (str): Path to the input video file.
        output_path (str): Path to the output (captioned) video file.
        original_filename (str): Original filename uploaded by the user.
    """
    job_id: str
    status_id: int
    progress: int
    created_at: datetime
    input_path: str
    output_path: str
    original_filename: str

class JobInformation(BaseModel):
    """
    Contains detailed information about a video captioning job, including download info.

    Attributes:
        job_id (str): Unique identifier for the job.
        status_id (int): Current status ID of the job.
        status_name (str): Human-readable status name.
        progress (int): Progress percentage (0-100).
        created_at (datetime): Timestamp when the job was created.
        completed_at (datetime): Timestamp when the job was completed.
        input_path (str): Path to the input video file.
        output_path (str): Path to the output (captioned) video file.
        download_url (str): URL to download the processed video.
        original_filename (str): Original filename uploaded by the user.
    """
    job_id: str
    status_id: int
    status_name: str
    progress: int
    created_at: datetime
    completed_at: datetime
    input_path: str
    output_path: str
    download_url: str
    original_filename: str

class SubtitleOptions(BaseModel):
    """
    Stores user-selected subtitle styling options for a job.

    Attributes:
        font (str): Font family for subtitles.
        font_size (int): Font size for subtitles.
        font_color (str): Font color for subtitles.
        stroke_color (str): Outline color for subtitles.
        stroke_width (int): Outline thickness for subtitles.
        position_id (int): Position of subtitles (1=bottom, 2=center, 3=top).
        shadow (bool): Whether to add a shadow effect to subtitles.
        max_chars(int):
        max_duration(float):
        max_gap(float):
    """
    font: str = "Arial"
    font_size: int = 24
    font_color: str = "white"
    stroke_color: str = "black"
    stroke_width: int = 2
    position_id: int = 1
    shadow: bool = False
    max_chars: int = 30
    max_duration: float = 2.5
    max_gap: float = 1.5


class JobStatus(BaseModel):
    """
    Represents the current status and progress of a video captioning job.

    Attributes:
        job_id (str): Unique identifier for the job.
        status_name (str): Human-readable status name.
        status_id (int): Current status ID of the job.
        progress (int): Progress percentage (0-100).
        created_at (datetime): Timestamp when the job was created.
        completed_at (Optional[datetime]): Timestamp when the job was completed (if any).
        download_url (Optional[str]): URL to download the processed video (if available).
    """
    job_id: str
    status_name: str
    status_id: int
    progress: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None
    download_url: Optional[str] = None

class UploadResponse(BaseModel):
    """
    Response model for a successful video upload.

    Attributes:
        job_id (str): Unique identifier for the created job.
        msg (str): Status message.
        status_url (str): URL to check the job's status.
    """
    job_id: str
    msg: str
    status_url: str


class HealthResponse(BaseModel):
    """
    Response model for the API health check endpoint.

    Attributes:
        status (str): Health status message.
        timestamp (datetime): Current server timestamp.
    """
    status: str
    timestamp: datetime
