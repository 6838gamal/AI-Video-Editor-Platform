from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.exceptions import (
    FileTooLargeError,
    InvalidVideoError,
    VideoError,
    VideoNotFoundError,
    VideoTooLongError,
)
from app.core.filesystem import (
    delete_video_files,
    ensure_user_dirs,
    new_video_id,
    video_dir,
    video_path,
)
from app.dependencies import CurrentUser

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


class VideoService:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user
        ensure_user_dirs(user.id)

    def save_upload(self, filename: str, file_bytes: bytes) -> dict[str, Any]:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise InvalidVideoError("Unsupported video format.")
        if len(file_bytes) > settings.max_upload_size_bytes:
            raise FileTooLargeError()
        video_id = new_video_id()
        vdir = video_dir(self.user.id, video_id)
        vdir.mkdir(parents=True, exist_ok=True)
        target = vdir / f"original{ext}"
        target.write_bytes(file_bytes)
        meta = self._probe(target)
        if meta is None:
            shutil.rmtree(vdir, ignore_errors=True)
            raise InvalidVideoError()
        if meta.get("duration", 0) > settings.max_video_duration_seconds:
            shutil.rmtree(vdir, ignore_errors=True)
            raise VideoTooLongError()
        # Normalize to .mp4 name for streaming simplicity
        if ext != ".mp4":
            target.rename(vdir / "original.mp4")
        self._save_meta(vdir, meta, filename)
        return {"video_id": video_id, "metadata": meta, "filename": filename}

    def save_downloaded(self, source: Path, original_title: str) -> dict[str, Any]:
        meta = self._probe(source)
        if meta is None:
            raise InvalidVideoError()
        if meta.get("duration", 0) > settings.max_video_duration_seconds:
            raise VideoTooLongError()
        video_id = new_video_id()
        vdir = video_dir(self.user.id, video_id)
        vdir.mkdir(parents=True, exist_ok=True)
        target = vdir / "original.mp4"
        shutil.move(str(source), str(target))
        self._save_meta(vdir, meta, original_title)
        return {"video_id": video_id, "metadata": meta, "filename": original_title}

    def list_videos(self) -> list[dict[str, Any]]:
        root = video_dir(self.user.id, "")
        if not root.parent.exists():
            return []
        videos: list[dict[str, Any]] = []
        for vdir in sorted(root.parent.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not vdir.is_dir():
                continue
            meta_path = vdir / "meta.json"
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            videos.append({"video_id": vdir.name, **meta})
        return videos

    def get_video_path(self, video_id: str) -> Path:
        path = video_path(self.user.id, video_id)
        if not path.exists():
            raise VideoNotFoundError()
        return path

    def get_metadata(self, video_id: str) -> dict[str, Any]:
        vdir = video_dir(self.user.id, video_id)
        meta_path = vdir / "meta.json"
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text())
            except (OSError, json.JSONDecodeError):
                pass
        path = self.get_video_path(video_id)
        meta = self._probe(path)
        if meta is None:
            raise InvalidVideoError()
        self._save_meta(vdir, meta, "video")
        return meta

    def delete(self, video_id: str) -> None:
        path = video_path(self.user.id, video_id)
        if not path.exists():
            raise VideoNotFoundError()
        delete_video_files(self.user.id, video_id)

    def _probe(self, path: Path) -> dict[str, Any] | None:
        try:
            result = subprocess.run(
                [
                    settings.ffprobe_path,
                "-v", "error",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.SubprocessError, OSError):
            return None
        if result.returncode != 0:
            return None
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
        vstream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        astream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
        fps = _parse_fps(vstream.get("avg_frame_rate") or vstream.get("r_frame_rate") or "0/1")
        return {
            "duration": float(data.get("format", {}).get("duration", 0) or 0),
            "width": int(vstream.get("width", 0) or 0),
            "height": int(vstream.get("height", 0) or 0),
            "fps": fps,
            "video_codec": vstream.get("codec_name", "unknown"),
            "audio_codec": astream.get("codec_name", "none"),
            "size": int(data.get("format", {}).get("size", 0) or 0),
        }

    @staticmethod
    def _save_meta(vdir: Path, meta: dict[str, Any], filename: str) -> None:
        meta_with_name = {"filename": filename, **meta}
        (vdir / "meta.json").write_text(json.dumps(meta_with_name))


def _parse_fps(rate: str) -> float:
    try:
        num, den = rate.split("/", 1)
        den_f = float(den)
        return round(float(num) / den_f, 3) if den_f else 0.0
    except (ValueError, ZeroDivisionError):
        return 0.0
