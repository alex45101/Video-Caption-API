import asyncio

from app.services.database import get_stuck_jobs_db, update_job_failed_db


async def start_job_watchdog(
    check_interval_seconds: int = 300,
    stuck_threshold_minutes: int = 30
):
    """
    JobWatchdog: Background task that periodically detects and resolves stuck jobs.

    Runs on a fixed interval and marks any job that has been in Processing status
    longer than the stuck threshold as Failed, preventing silent hangs from
    clogging the job queue indefinitely.

    Args:
        check_interval_seconds (int): How often to poll for stuck jobs in seconds.
                                      Defaults to 300 (5 minutes).
        stuck_threshold_minutes (int): Minutes after which a Processing job is
                                       considered stuck. Defaults to 30.
    """
    print(f"JobWatchdog started (interval={check_interval_seconds}s, threshold={stuck_threshold_minutes}m)")

    while True:
        try:
            await asyncio.sleep(check_interval_seconds)
            await _resolve_stuck_jobs(stuck_threshold_minutes)
        except asyncio.CancelledError:
            print("JobWatchdog stopped")
            break
        except Exception as e:
            print(f"JobWatchdog error: {e}")


async def _resolve_stuck_jobs(stuck_threshold_minutes: int):
    """
    Queries for stuck jobs and marks each one as Failed.

    Args:
        stuck_threshold_minutes (int): Age threshold in minutes for a Processing job
                                       to be considered stuck.
    """
    stuck_job_ids = get_stuck_jobs_db(stuck_threshold_minutes)

    if not stuck_job_ids:
        return

    print(f"JobWatchdog: Found {len(stuck_job_ids)} stuck job(s)")

    for job_id in stuck_job_ids:
        failed_message = f"Error: Job exceeded the {stuck_threshold_minutes}-minute processing timeout and was automatically failed"
        success = update_job_failed_db(job_id, failed_message)
        if success:
            print(f"JobWatchdog: Marked job {job_id} as failed (stuck timeout)")
        else:
            print(f"JobWatchdog: Failed to update stuck job {job_id}")
