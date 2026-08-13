from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.exceptions import VideoEditorError
from app.dependencies import AuthDependency, CurrentUser
from app.modules.videos.services import VideoService
from app.modules.youtube.services import YouTubeService

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


class DownloadRequest(BaseModel):
    url: str


@router.post("/download")
async def download(body: DownloadRequest, user: CurrentUser = Depends(AuthDependency())):
    try:
        path = YouTubeService(user).download(body.url)
        result = VideoService(user).save_downloaded(path, "youtube.mp4")
        return result
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=400)
