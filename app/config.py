from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(value: Optional[str], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


class Settings:
    def __init__(self) -> None:
        env = os.environ

        self.app_name: str = env.get("APP_NAME", "Video Editor")
        self.debug: bool = _bool(env.get("DEBUG"), True)
        self.environment: str = env.get("ENVIRONMENT", "development")

        self.database_url: str = env.get(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@db:5432/video_editor",
        )
        self.secret_key: str = env.get("SECRET_KEY", "dev-secret-key")
        self.session_secret: str = env.get("SESSION_SECRET", "dev-session-secret")

        self.storage_root: Path = Path(env.get("STORAGE_ROOT", "/app/storage"))
        self.max_upload_size_mb: int = _int(env.get("MAX_UPLOAD_SIZE_MB"), 500)
        self.max_video_duration_seconds: int = _int(env.get("MAX_VIDEO_DURATION_SECONDS"), 3600)

        self.ffmpeg_path: str = env.get("FFMPEG_PATH", "ffmpeg")
        self.ffprobe_path: str = env.get("FFPROBE_PATH", "ffprobe")
        self.yt_dlp_path: str = env.get("YT_DLP_PATH", "yt-dlp")

        self.ai_provider: str = env.get("AI_PROVIDER", "").strip()
        self.ai_api_key: str = env.get("AI_API_KEY", "").strip()
        self.ai_model: str = env.get("AI_MODEL", "").strip()

        self.allow_fallback_user: bool = _bool(env.get("ALLOW_FALLBACK_USER"), True)

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_provider and self.ai_api_key)

    @property
    def fallback_user_id(self) -> str:
        return "00000000-0000-0000-0000-000000000001"

    @property
    def fallback_user_email(self) -> str:
        return "demo@example.com"


settings = Settings()
