from __future__ import annotations

import shutil
import subprocess
from typing import Any

from app.config import settings
from app.database import is_database_available


class SystemService:
    @staticmethod
    def status() -> dict[str, Any]:
        return {
            "application": "ok",
            "app_name": settings.app_name,
            "database": "connected" if is_database_available() else "unavailable",
            "degraded": not is_database_available(),
            "ffmpeg": _tool_available(settings.ffmpeg_path),
            "ffprobe": _tool_available(settings.ffprobe_path),
            "yt_dlp": _tool_available(settings.yt_dlp_path),
            "ai": "configured" if settings.ai_enabled else "not_configured",
        }


def _tool_available(name: str) -> str:
    path = shutil.which(name)
    return "available" if path else "missing"
