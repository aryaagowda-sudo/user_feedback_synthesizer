import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from threading import Lock

logger = logging.getLogger("feedbackiq.jobs")

class JobManager:
    """Thread-safe in-memory manager for background AI analysis jobs."""
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def create_job(self, total_items: int = 0, dataset_name: str = "Dataset") -> str:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",  # "queued", "processing", "completed", "failed"
                "current_stage": "Data preprocessing",
                "stage_index": 1,
                "total_stages": 6,
                "progress_percentage": 2,
                "total_items": total_items,
                "processed_items": 0,
                "message": f"Queued analysis for {total_items} feedback items...",
                "dataset_name": dataset_name,
                "result": None,
                "error": None,
                "created_at": now,
                "updated_at": now
            }
        logger.info(f"Created analysis job {job_id} for {total_items} items ({dataset_name})")
        return job_id

    def update_job(
        self,
        job_id: str,
        current_stage: Optional[str] = None,
        stage_index: Optional[int] = None,
        progress_percentage: Optional[int] = None,
        processed_items: Optional[int] = None,
        total_items: Optional[int] = None,
        message: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        **kwargs
    ):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            if status is not None:
                job["status"] = status
            if current_stage is not None:
                job["current_stage"] = current_stage
            if stage_index is not None:
                job["stage_index"] = stage_index
            if progress_percentage is not None:
                job["progress_percentage"] = min(100, max(0, progress_percentage))
            if processed_items is not None:
                job["processed_items"] = processed_items
            if total_items is not None:
                job["total_items"] = total_items
            if message is not None:
                job["message"] = message
            if result is not None:
                job["result"] = result
            if error is not None:
                job["error"] = error
            for k, v in kwargs.items():
                job[k] = v
            job["updated_at"] = datetime.now(timezone.utc).isoformat()

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return dict(job)

job_manager = JobManager()
