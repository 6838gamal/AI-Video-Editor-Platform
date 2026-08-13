from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from app.core.exceptions import VideoEditorError
from app.dependencies import AuthDependency, CurrentUser
from app.modules.videos.services import VideoService

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(AuthDependency()),
):
    data = await file.read()
    try:
        result = VideoService(user).save_upload(file.filename or "video.mp4", data)
        return result
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=400)


@router.get("/{video_id}")
async def get_video(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    try:
        meta = VideoService(user).get_metadata(video_id)
        return {"video_id": video_id, **meta}
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=404)


@router.get("/{video_id}/metadata")
async def get_metadata(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    try:
        return VideoService(user).get_metadata(video_id)
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=404)


@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    try:
        path = VideoService(user).get_video_path(video_id)
        return FileResponse(path, media_type="video/mp4")
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=404)


@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    try:
        VideoService(user).delete(video_id)
        return {"ok": True}
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=404)
