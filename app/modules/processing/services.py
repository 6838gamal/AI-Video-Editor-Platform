from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.exceptions import JobNotFoundError, ProcessingError, VideoEditorError
from app.core.filesystem import (
    delete_file,
    new_job_id,
    output_dir,
    temp_dir,
)
from app.dependencies import CurrentUser
from app.modules.editor.schemas import EditingPlan
from app.modules.editor.services import EditorService

_jobs: dict[str, "Job"] = {}
_jobs_lock = threading.Lock()


@dataclass
class Job:
    job_id: str
    user_id: str
    video_id: str
    status: str = "queued"  # queued | processing | completed | failed
    progress: int = 0
    message: str = ""
    output_filename: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "video_id": self.video_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "output": self.output_filename,
            "error": self.error,
        }


class ProcessingService:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user

    def start(self, video_id: str, plan: EditingPlan) -> str:
        job_id = new_job_id()
        job = Job(job_id=job_id, user_id=self.user.id, video_id=video_id)
        with _jobs_lock:
            _jobs[job_id] = job
        thread = threading.Thread(target=self._run, args=(job, plan), daemon=True)
        thread.start()
        return job_id

    def start_from_saved(self, job_id: str) -> str:
        payload = EditorService(self.user).load_plan(job_id)
        plan = EditingPlan(**payload["plan"])
        video_id = payload["video_id"]
        # Reuse same job_id for continuity
        job = Job(job_id=job_id, user_id=self.user.id, video_id=video_id)
        with _jobs_lock:
            _jobs[job_id] = job
        thread = threading.Thread(target=self._run, args=(job, plan), daemon=True)
        thread.start()
        return job_id

    def _run(self, job: Job, plan: EditingPlan) -> None:
        self._update(job, status="processing", progress=10, message="Starting FFmpeg...")
        try:
            self._update(job, progress=30, message="Processing video...")
            output = EditorService(self.user).process(job.video_id, plan, job.job_id)
            self._update(job, status="completed", progress=100, message="Done", output_filename=output.name)
        except VideoEditorError as exc:
            self._update(job, status="failed", progress=0, error=exc.message, message="Failed")
        except Exception as exc:  # noqa: BLE001
            self._update(job, status="failed", progress=0, error="Unexpected error.", message="Failed")

    @staticmethod
    def _update(job: Job, **kwargs: Any) -> None:
        with _jobs_lock:
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.updated_at = time.time()

    def get_job(self, job_id: str) -> Job:
        with _jobs_lock:
            job = _jobs.get(job_id)
        if job is None or job.user_id != self.user.id:
            raise JobNotFoundError()
        return job

    def get_output_path(self, job_id: str) -> str:
        job = self.get_job(job_id)
        if job.status != "completed" or not job.output_filename:
            raise ProcessingError("Output not ready.")
        path = output_dir(self.user.id) / job.output_filename
        if not path.exists():
            raise ProcessingError("Output file missing.")
        return str(path)
