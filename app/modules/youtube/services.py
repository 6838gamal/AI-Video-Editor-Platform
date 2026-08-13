from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app.config import settings
from app.core.exceptions import YouTubeError
from app.core.filesystem import ensure_user_dirs, temp_dir
from app.dependencies import CurrentUser

YOUTUBE_RE = re.compile(
    r"^(https?://)?(www\.|music\.|m\.)?(youtube\.com|youtu\.be)/.+$",
    re.IGNORECASE,
)


def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_RE.match(url.strip()))


class YouTubeService:
    def __init__(self, user: CurrentUser) -> None:
        self.user = user
        ensure_user_dirs(user.id)

    def download(self, url: str) -> Path:
        url = url.strip()
        if not is_youtube_url(url):
            raise YouTubeError("Please provide a valid YouTube URL.")
        dest = temp_dir(self.user.id)
        output = dest / "yt_download.mp4"
        try:
            result = subprocess.run(
                [
                    settings.yt_dlp_path,
                    "-f",
                    "best[ext=mp4][height<=720]/best[height<=720]/best",
                    "--no-playlist",
                    "--no-warnings",
                    "-o",
                    str(output),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except (subprocess.SubprocessError, OSError) as exc:
            raise YouTubeError(f"Download failed: {exc}") from exc
        if result.returncode != 0 or not output.exists():
            raise YouTubeError("Could not download this video. It may be private or restricted.")
        return output
