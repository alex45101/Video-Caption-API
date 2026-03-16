import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.models import JobCreation, JobInformation, JobStatus, SubtitleOptions
from app.core.settings import DB_PATH, FROMAT_DATETIME_STRING

def init_database():
    """
    Initializes the SQLite database and creates all required tables and indexes if they do not exist.
    Also inserts default values for Positions and Status tables.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Positions table and insert default positions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Positions (
            Position_ID INTEGER PRIMARY KEY NOT NULL,
            Position_Name TEXT NOT NULL            
        )
    """)

    cursor.execute("INSERT OR IGNORE INTO Positions VALUES (1, 'Bottom')")
    cursor.execute("INSERT OR IGNORE INTO Positions VALUES (2, 'Center')")
    cursor.execute("INSERT OR IGNORE INTO Positions VALUES (3, 'Top')")

    # Create Status table and insert default statuses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Status (
            Status_ID INTEGER PRIMARY KEY NOT NULL,
            Status_Name TEXT NOT NULL            
        )
    """)

    cursor.execute("INSERT OR IGNORE INTO Status VALUES (1, 'Not Started')")
    cursor.execute("INSERT OR IGNORE INTO Status VALUES (2, 'Processing')")
    cursor.execute("INSERT OR IGNORE INTO Status VALUES (3, 'Completed')")
    cursor.execute("INSERT OR IGNORE INTO Status VALUES (4, 'Failed')")

    # Create Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Jobs (
            Job_ID TEXT PRIMARY KEY NOT NULL,
            Progress INTEGER DEFAULT 0 NOT NULL,
            Input_Path TEXT NOT NULL,
            Output_Path TEXT NOT NULL,
            Original_Filename TEXT NOT NULL,
            Created_At TEXT NOT NULL,
            Completed_At TEXT NOT NULL,
            Status_ID INTEGER DEFAULT 1 NOT NULL,
            Download_URL TEXT DEFAULT '',
            Failed_Message TEXT DEFAULT '',
            File_Hash TEXT DEFAULT '',
            Retry_Count INTEGER DEFAULT 0 NOT NULL,
            FOREIGN KEY (Status_ID) REFERENCES Status (Status_ID)
        )
    """)

    # Create Subtitle_Options table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Subtitle_Options (
            Job_ID TEXT PRIMARY KEY,
            Font TEXT NOT NULL,
            Font_Size INTEGER NOT NULL,
            Font_Color TEXT NOT NULL,
            Stroke_Width INTEGER NOT NULL,
            Stroke_Color TEXT NOT NULL,
            Position_ID INTEGER NOT NULL,
            Shadow_Enabled BOOLEAN NOT NULL,    
            Max_Chars INTEGER NOT NULL,
            Max_Duration REAL NOT NULL,
            MAX_Gap REAL NOT NULL,
            FOREIGN KEY (Job_ID) REFERENCES Jobs (Job_ID),   
            FOREIGN KEY (Position_ID) REFERENCES Positions (Position_ID)  
        )
    """)

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON Jobs(Status_ID)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON Jobs(Created_At)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_subtitle_position ON Subtitle_Options(Position_ID)")

    conn.commit()
    conn.close()

def create_job_db(job_data: JobCreation, subtitle_options: SubtitleOptions) -> bool:
    """
    Inserts a new job and its subtitle options into the database.

    Args:
        job_data (JobCreation): Job metadata to insert.
        subtitle_options (SubtitleOptions): Subtitle styling options.

    Returns:
        bool: True if insertion succeeded, False otherwise.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert job metadata
        cursor.execute("""
            INSERT INTO Jobs (Job_ID, Progress, Input_Path, Output_Path, Original_Filename,
                       Created_At, Completed_At, Status_ID, File_Hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_data.job_id, job_data.progress, job_data.input_path, job_data.output_path,
              job_data.original_filename, job_data.created_at, datetime(1, 1, 1, 1, 1, 1, 1),
              job_data.status_id, job_data.file_hash
        ))

        # Insert subtitle options for the job
        cursor.execute("""
            INSERT INTO Subtitle_Options (Job_ID, Font, Font_Size, Font_Color, 
                       Stroke_Width, Stroke_Color, Position_ID, Shadow_Enabled, 
                       Max_Chars, Max_Duration, Max_Gap)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (job_data.job_id, subtitle_options.font, subtitle_options.font_size,
              subtitle_options.font_color, subtitle_options.stroke_width, subtitle_options.stroke_color,
              subtitle_options.position_id, subtitle_options.shadow, 
              subtitle_options.max_chars, subtitle_options.max_duration, subtitle_options.max_gap
        ))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return False

    return True

def get_job_download_URL_db(job_id: str) -> JobInformation:    
    """
    Retrieves job information including download URL for a given job ID.

    Args:
        job_id (str): Unique job identifier.

    Returns:
        JobInformation or None: Job information if found, else None.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query job and status info
        cursor.execute("""
            SELECT 
                j.Job_ID,                
                s.Status_Name,
                s.Status_ID,
                j.Progress,
                j.Created_At,
                j.Completed_At,
                j.Input_Path,
                j.Output_Path,
                j.Download_URL,
                j.Original_Filename
            FROM Jobs j
            LEFT JOIN Status s ON j.Status_ID = s.Status_ID
            WHERE j.Job_ID = ?
        """, (job_id,))

        row = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return None

    if not row:
        return None 

    # Convert DB row to JobInformation dataclass
    return JobInformation(
        job_id=row[0],
        status_name=row[1],
        status_id=row[2],
        progress=row[3],
        created_at=datetime.strptime(row[4], FROMAT_DATETIME_STRING),
        completed_at=datetime.strptime(row[5], FROMAT_DATETIME_STRING),
        input_path=row[6],
        output_path=row[7],
        download_url=row[8],
        original_filename=row[9]
    )
    

def get_job_status_db(job_id: str) -> JobStatus:
    """
    Retrieves job status information for a given job ID.

    Args:
        job_id (str): Unique job identifier.

    Returns:
        JobStatus or None: Job status if found, else None.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query job and status info
        cursor.execute("""
            SELECT 
                j.Job_ID,                
                s.Status_Name,
                s.Status_ID,
                j.Progress,
                j.Created_At,
                j.Completed_At,
                j.Download_URL
            FROM Jobs j
            LEFT JOIN Status s ON j.Status_ID = s.Status_ID
            WHERE j.Job_ID = ?
        """, (job_id,))

        row = cursor.fetchone()
        conn.close()

    except Exception as e:
        print(f"Database error: {e}")
        return None
    
    if not row:
        return None

    # Convert DB row to JobStatus dataclass
    return JobStatus(
        job_id=row[0],            
        status_name=row[1],
        status_id=row[2],
        progress=row[3],
        created_at=datetime.strptime(row[4], FROMAT_DATETIME_STRING),
        completed_at=datetime.strptime(row[5], FROMAT_DATETIME_STRING),            
        download_url=row[6]            
    )    

def update_job_status_db(job_id: str, status_id: int, progress: int) -> bool:
    """
    Updates the status and progress of a job.

    Args:
        job_id (str): Unique job identifier.
        status_id (int): New status ID.
        progress (int): New progress value.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    try:
        conn = sqlite3.connect(DB_PATH)

        # Update status and progress
        conn.execute("""
            UPDATE Jobs 
            SET 
                Status_ID = ?,
                Progress = ?
            WHERE Job_ID = ? 
        """, (status_id, progress, job_id))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return False

    return True

def update_job_failed_db(job_id: str, failed_message: str) -> bool:
    """
    Marks a job as failed and records the failure message.

    Args:
        job_id (str): Unique job identifier.
        failed_message (str): Description of the failure.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    try:
        conn = sqlite3.connect(DB_PATH)        

        # Set status to Failed and record message
        conn.execute("""
            UPDATE Jobs 
            SET 
                Status_ID = ?,
                Progress = ?,
                Failed_Message = ?
            WHERE Job_ID = ? 
        """, (4, 0, failed_message, job_id))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return False

    return True

def get_retriable_jobs_db(max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    RetryAgent: Returns failed jobs that are eligible for an automatic retry.

    Excludes jobs that failed due to a permanent error (JobWatchdog timeout) and
    jobs that have already exhausted the maximum number of retries.

    Args:
        max_retries (int): Maximum number of retry attempts per job. Defaults to 3.

    Returns:
        List[Dict]: Each entry contains job_id, input_path, and output_path.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Status_ID 4 = Failed; exclude JobWatchdog timeout errors as permanent
        cursor.execute("""
            SELECT Job_ID, Input_Path, Output_Path
            FROM Jobs
            WHERE Status_ID = 4
              AND Retry_Count < ?
              AND Failed_Message NOT LIKE 'Error: Job exceeded%'
        """, (max_retries,))

        rows = cursor.fetchall()
        conn.close()

        return [{"job_id": row[0], "input_path": row[1], "output_path": row[2]} for row in rows]
    except Exception as e:
        print(f"Database error: {e}")
        return []


def get_subtitle_options_db(job_id: str) -> Optional[SubtitleOptions]:
    """
    RetryAgent: Retrieves the subtitle options stored for a given job.

    Used when re-queuing a failed job so it can be re-processed with the
    original user-configured subtitle settings.

    Args:
        job_id (str): Unique job identifier.

    Returns:
        SubtitleOptions or None: The subtitle options if found, else None.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT Font, Font_Size, Font_Color, Stroke_Color, Stroke_Width,
                   Position_ID, Shadow_Enabled, Max_Chars, Max_Duration, MAX_Gap
            FROM Subtitle_Options
            WHERE Job_ID = ?
        """, (job_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return SubtitleOptions(
            font=row[0],
            font_size=row[1],
            font_color=row[2],
            stroke_color=row[3],
            stroke_width=row[4],
            position_id=row[5],
            shadow=bool(row[6]),
            max_chars=row[7],
            max_duration=row[8],
            max_gap=row[9]
        )
    except Exception as e:
        print(f"Database error: {e}")
        return None


def reset_job_for_retry_db(job_id: str) -> bool:
    """
    RetryAgent: Resets a failed job back to Not Started and increments its retry count.

    Args:
        job_id (str): Unique job identifier.

    Returns:
        bool: True if the reset succeeded, False otherwise.
    """
    try:
        conn = sqlite3.connect(DB_PATH)

        conn.execute("""
            UPDATE Jobs
            SET Status_ID = 1,
                Progress = 0,
                Failed_Message = '',
                Retry_Count = Retry_Count + 1
            WHERE Job_ID = ?
        """, (job_id,))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return False

    return True


def get_completed_jobs_for_cleanup_db() -> List[tuple]:
    """
    DiskGuardian: Returns (job_id, output_path) for completed jobs, oldest first.

    Used to identify which output files can be safely removed when disk space is low.

    Returns:
        List[tuple]: Each entry is (job_id, output_path), ordered by Completed_At ascending.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT Job_ID, Output_Path
            FROM Jobs
            WHERE Status_ID = 3 AND Output_Path != ''
            ORDER BY Completed_At ASC
        """)

        rows = cursor.fetchall()
        conn.close()

        return [(row[0], row[1]) for row in rows]
    except Exception as e:
        print(f"Database error: {e}")
        return []


def get_job_by_hash_db(file_hash: str) -> Optional[str]:
    """
    FileGuard: Looks up the most recent non-failed job with a matching file hash.

    Used to detect duplicate uploads and avoid reprocessing identical files.

    Args:
        file_hash (str): SHA-256 hash of the uploaded file.

    Returns:
        str or None: Existing job_id if a duplicate is found, else None.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT Job_ID FROM Jobs
            WHERE File_Hash = ? AND Status_ID != 4
            ORDER BY Created_At DESC
            LIMIT 1
        """, (file_hash,))

        row = cursor.fetchone()
        conn.close()

        return row[0] if row else None
    except Exception as e:
        print(f"Database error: {e}")
        return None


def get_stuck_jobs_db(stuck_threshold_minutes: int = 30) -> List[str]:
    """
    JobWatchdog: Returns job IDs that have been stuck in Processing status
    beyond the given threshold.

    Args:
        stuck_threshold_minutes (int): Minutes after which a Processing job is
                                       considered stuck. Defaults to 30.

    Returns:
        List[str]: List of stuck job IDs.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        threshold_time = datetime.now() - timedelta(minutes=stuck_threshold_minutes)
        threshold_str = threshold_time.strftime(FROMAT_DATETIME_STRING)

        # Status_ID 2 = Processing
        cursor.execute("""
            SELECT Job_ID FROM Jobs
            WHERE Status_ID = 2 AND Created_At < ?
        """, (threshold_str,))

        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]
    except Exception as e:
        print(f"Database error: {e}")
        return []


def update_job_completed_db(job_id: str) -> bool:
    """
    Marks a job as completed, sets progress to 100, records completion time and download URL.

    Args:
        job_id (str): Unique job identifier.

    Returns:
        bool: True if update succeeded, False otherwise.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.cursor()

        # Set status to Completed, set progress, completion time, and download URL
        conn.execute("""
            UPDATE Jobs 
            SET 
                Status_ID = ?,
                Progress = ?,
                Completed_At = ?,
                Download_URL = ?
            WHERE Job_ID = ? 
        """, (3, 100, datetime.now(), f"/jobs/{job_id}/download", job_id))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return False
    
    return True