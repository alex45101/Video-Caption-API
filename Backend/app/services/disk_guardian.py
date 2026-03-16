import asyncio
import shutil
from pathlib import Path

from app.services.database import get_completed_jobs_for_cleanup_db
from app.core.settings import TEMP_DIR

# Default free-space threshold: 1 GB
_DEFAULT_FREE_THRESHOLD_BYTES = 1 * 1024 * 1024 * 1024


async def start_disk_guardian(
    check_interval_seconds: int = 900,
    free_threshold_bytes: int = _DEFAULT_FREE_THRESHOLD_BYTES
):
    """
    DiskGuardian: Background task that frees disk space when it falls below a threshold.

    Runs on a fixed interval and checks the free space on the TEMP_DIR volume.
    When free space is low, it removes the output files of the oldest completed jobs
    one-by-one until the threshold is met or all candidates are exhausted.

    Completed job records are preserved in the database — only the physical output
    file is deleted. Download attempts after cleanup will receive a 404 from the
    existing route handler.

    Args:
        check_interval_seconds (int): How often to check disk space in seconds.
                                      Defaults to 900 (15 minutes).
        free_threshold_bytes (int): Minimum acceptable free bytes on the TEMP_DIR
                                    volume. Defaults to 1 GB.
    """
    threshold_gb = free_threshold_bytes / (1024 ** 3)
    print(f"DiskGuardian started (interval={check_interval_seconds}s, threshold={threshold_gb:.1f} GB free)")

    while True:
        try:
            await asyncio.sleep(check_interval_seconds)
            await _enforce_disk_threshold(free_threshold_bytes)
        except asyncio.CancelledError:
            print("DiskGuardian stopped")
            break
        except Exception as e:
            print(f"DiskGuardian error: {e}")


async def _enforce_disk_threshold(free_threshold_bytes: int):
    """
    Checks disk usage and removes oldest completed job output files if space is low.

    Args:
        free_threshold_bytes (int): Target minimum free bytes before cleanup stops.
    """
    usage = shutil.disk_usage(TEMP_DIR)

    if usage.free >= free_threshold_bytes:
        return

    free_gb = usage.free / (1024 ** 3)
    print(f"DiskGuardian: Low disk space ({free_gb:.2f} GB free). Starting cleanup...")

    candidates = get_completed_jobs_for_cleanup_db()
    removed_count = 0

    for job_id, output_path in candidates:
        if not output_path:
            continue

        output_file = Path(output_path)
        if not output_file.exists():
            continue

        try:
            output_file.unlink()
            removed_count += 1
            print(f"DiskGuardian: Removed output file for job {job_id}")
        except Exception as e:
            print(f"DiskGuardian: Failed to remove {output_path} for job {job_id}: {e}")
            continue

        # Re-check space after each deletion — stop as soon as threshold is met
        if shutil.disk_usage(TEMP_DIR).free >= free_threshold_bytes:
            break

    final_free_gb = shutil.disk_usage(TEMP_DIR).free / (1024 ** 3)
    print(f"DiskGuardian: Cleanup complete. Removed {removed_count} file(s). Free space: {final_free_gb:.2f} GB")
