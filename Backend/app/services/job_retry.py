import asyncio
import os

from app.services.database import get_retriable_jobs_db, get_subtitle_options_db, reset_job_for_retry_db


async def start_retry_agent(check_interval_seconds: int = 300, max_retries: int = 3):
    """
    RetryAgent: Background task that automatically re-queues eligible failed jobs.

    Polls on a fixed interval for jobs in Failed status that have not yet hit the
    retry limit and were not caused by a permanent error. Eligible jobs are reset
    to Not Started and re-submitted for processing with their original subtitle options.

    Transient failures (FFmpeg crash, Whisper error, unexpected exceptions) are
    retried. Permanent failures (JobWatchdog timeout) are skipped.

    Args:
        check_interval_seconds (int): How often to poll for failed jobs in seconds.
                                      Defaults to 300 (5 minutes).
        max_retries (int): Maximum retry attempts per job before it is left as Failed.
                           Defaults to 3.
    """
    print(f"RetryAgent started (interval={check_interval_seconds}s, max_retries={max_retries})")

    while True:
        try:
            await asyncio.sleep(check_interval_seconds)
            await _retry_failed_jobs(max_retries)
        except asyncio.CancelledError:
            print("RetryAgent stopped")
            break
        except Exception as e:
            print(f"RetryAgent error: {e}")


async def _retry_failed_jobs(max_retries: int):
    """
    Finds retriable jobs and re-queues each one as a new asyncio task.

    Skips jobs whose input file no longer exists on disk (e.g. cleaned by
    DiskGuardian before the retry window) or whose subtitle options cannot
    be retrieved from the database.

    Args:
        max_retries (int): Maximum retry attempts allowed per job.
    """
    # Import here to avoid a circular import at module load time
    from app.services.video_service import background_video_processing

    candidates = get_retriable_jobs_db(max_retries)

    if not candidates:
        return

    print(f"RetryAgent: Found {len(candidates)} job(s) eligible for retry")

    for job in candidates:
        job_id = job["job_id"]
        input_path = job["input_path"]
        output_path = job["output_path"]

        # Input file must still exist — DiskGuardian may have removed it
        if not os.path.exists(input_path):
            print(f"RetryAgent: Skipping job {job_id} — input file no longer exists")
            continue

        subtitle_options = get_subtitle_options_db(job_id)
        if not subtitle_options:
            print(f"RetryAgent: Skipping job {job_id} — could not retrieve subtitle options")
            continue

        success = reset_job_for_retry_db(job_id)
        if not success:
            print(f"RetryAgent: Failed to reset job {job_id} for retry")
            continue

        print(f"RetryAgent: Re-queuing job {job_id} (attempt {job.get('retry_count', '?') + 1})")
        asyncio.create_task(background_video_processing(job_id, input_path, output_path, subtitle_options))
