from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from app.core.exceptions import VideoEditorError
from app.dependencies import (
    CurrentUser,
    get_current_user,
)
from app.modules.videos.services import VideoService


router = APIRouter(
    prefix="/api/videos",
    tags=["videos"],
)


# =========================================================
# Upload Video
# =========================================================

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(
        get_current_user
    ),
):
    """
    Upload a video for the current user.
    """

    if not file:

        return JSONResponse(
            {
                "ok": False,
                "error": "لم يتم إرسال ملف.",
            },
            status_code=400,
        )

    filename = file.filename or "video.mp4"

    try:

        data = await file.read()

        if not data:

            return JSONResponse(
                {
                    "ok": False,
                    "error": "الملف فارغ.",
                },
                status_code=400,
            )

        result = VideoService(
            user
        ).save_upload(
            filename,
            data,
        )

        return result

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=400,
        )

    except Exception as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": "حدث خطأ أثناء رفع الفيديو.",
                "detail": str(exc),
            },
            status_code=500,
        )


# =========================================================
# Get Video
# =========================================================

@router.get("/{video_id}")
async def get_video(
    video_id: str,
    user: CurrentUser = Depends(
        get_current_user
    ),
):
    """
    Get video metadata for the current user.
    """

    try:

        meta = VideoService(
            user
        ).get_metadata(
            video_id
        )

        return {
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

    except Exception as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": "تعذر تحميل بيانات الفيديو.",
                "detail": str(exc),
            },
            status_code=500,
        )


# =========================================================
# Video Metadata
# =========================================================

@router.get("/{video_id}/metadata")
async def get_metadata(
    video_id: str,
    user: CurrentUser = Depends(
        get_current_user
    ),
):
    """
    Return video metadata.
    """

    try:

        return VideoService(
            user
        ).get_metadata(
            video_id
        )

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=404,
        )

    except Exception as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": "تعذر تحميل البيانات.",
                "detail": str(exc),
            },
            status_code=500,
        )


# =========================================================
# Stream Video
# =========================================================

@router.get("/{video_id}/stream")
async def stream_video(
    video_id: str,
    user: CurrentUser = Depends(
        get_current_user
    ),
):
    """
    Stream the requested video.
    """

    try:

        path = VideoService(
            user
        ).get_video_path(
            video_id
        )

        return FileResponse(
            path,
            media_type="video/mp4",
        )

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=404,
        )

    except Exception as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": "تعذر تشغيل الفيديو.",
                "detail": str(exc),
            },
            status_code=500,
        )


# =========================================================
# Delete Video
# =========================================================

@router.delete("/{video_id}")
async def delete_video(
    video_id: str,
    user: CurrentUser = Depends(
        get_current_user
    ),
):
    """
    Delete a video belonging to the current user.
    """

    try:

        VideoService(
            user
        ).delete(
            video_id
        )

        return {
            "ok": True,
        }

    except VideoEditorError as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": exc.message,
            },
            status_code=404,
        )

    except Exception as exc:

        return JSONResponse(
            {
                "ok": False,
                "error": "تعذر حذف الفيديو.",
                "detail": str(exc),
            },
            status_code=500,
        )
