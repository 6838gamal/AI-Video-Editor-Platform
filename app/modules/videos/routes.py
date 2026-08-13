from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.core.exceptions import VideoEditorError
from app.dependencies import AuthDependency, CurrentUser
from app.modules.videos.services import VideoService


router = APIRouter(
    prefix="/api/videos",
    tags=["videos"],
)


# =========================================================
# List Videos
# =========================================================

@router.get("")
async def list_videos(
    user: CurrentUser = Depends(AuthDependency()),
):
    """
    Return all videos belonging to the current user.
    """

    try:
        videos = VideoService(user).list_videos()

        return {
            "videos": videos,
            "count": len(videos),
        }

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=400,
        )


# =========================================================
# Upload Video
# =========================================================

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(AuthDependency()),
):
    """
    Upload a video for the current user.
    """

    if not file.filename:

        return JSONResponse(
            {
                "ok": False,
                "error": "No filename was provided.",
            },
            status_code=400,
        )

    try:

        data = await file.read()

        result = VideoService(user).save_upload(
            file.filename,
            data,
        )

        return {
            "ok": True,
            **result,
        }

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=400,
        )

    except Exception:

        return JSONResponse(
            {
                "ok": False,
                "error": "Failed to upload video.",
            },
            status_code=500,
        )


# =========================================================
# Video Information
# =========================================================

@router.get("/{video_id}")
async def get_video(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    """
    Return video metadata.
    """

    try:

        meta = VideoService(user).get_metadata(
            video_id
        )

        return {
            "ok": True,
            "video_id": video_id,
            **meta,
        }

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=404,
        )


# =========================================================
# Metadata
# =========================================================

@router.get("/{video_id}/metadata")
async def get_metadata(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    """
    Return metadata for a specific video.
    """

    try:

        metadata = VideoService(user).get_metadata(
            video_id
        )

        return {
            "ok": True,
            "video_id": video_id,
            "metadata": metadata,
        }

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=404,
        )


# =========================================================
# Stream Video
# =========================================================

@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    """
    Stream the original video.
    """

    try:

        path = VideoService(user).get_video_path(
            video_id
        )

        return FileResponse(
            path,
            media_type="video/mp4",
            filename=path.name,
        )

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=404,
        )


# =========================================================
# Delete Video
# =========================================================

@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    user: CurrentUser = Depends(AuthDependency()),
):
    """
    Delete a video belonging to the current user.
    """

    try:

        VideoService(user).delete(video_id)

        return {
            "ok": True,
            "video_id": video_id,
        }

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=404,
        )
