from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from app.config import settings
from app.core.exceptions import VideoNotFoundError


def _safe_join(base: Path, *parts: str) -> Path:
    """Join paths while preventing traversal outside base."""
    base = base.resolve()
    target = base.joinpath(*parts).resolve()
    if base not in target.parents and target != base:
        raise VideoNotFoundError("Invalid path.")
    return target


def user_root(user_id: str) -> Path:
    return _safe_join(settings.storage_root, "users", user_id)


def ensure_user_dirs(user_id: str) -> Path:
    root = user_root(user_id)
    for sub in ("videos", "outputs", "temp", "projects"):
        root.joinpath(sub).mkdir(parents=True, exist_ok=True)
    return root


def video_dir(user_id: str, video_id: str) -> Path:
    return _safe_join(user_root(user_id), "videos", video_id)


def video_path(user_id: str, video_id: str, filename: str = "original.mp4") -> Path:
    return _safe_join(video_dir(user_id, video_id), filename)


def output_dir(user_id: str) -> Path:
    return _safe_join(user_root(user_id), "outputs")


def temp_dir(user_id: str) -> Path:
    return _safe_join(user_root(user_id), "temp")


def projects_dir(user_id: str) -> Path:
    return _safe_join(user_root(user_id), "projects")


def new_video_id() -> str:
    return str(uuid.uuid4())


def new_job_id() -> str:
    return str(uuid.uuid4())


def delete_video_files(user_id: str, video_id: str) -> None:
    d = video_dir(user_id, video_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def delete_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


def safe_filename(name: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    cleaned = "".join(c for c in name if c in keep)
    return cleaned or "file"
