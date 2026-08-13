from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from app.core.exceptions import VideoEditorError
from app.dependencies import AuthDependency, CurrentUser
from app.modules.editor.schemas import EditingPlan
from app.modules.processing.services import ProcessingService

router = APIRouter(prefix="/api/processing", tags=["processing"])


class StartRequest(BaseModel):
    video_id: str
    plan: EditingPlan | None = None
    job_id: str | None = None


@router.post("/start")
async def start_processing(body: StartRequest, user: CurrentUser = Depends(AuthDependency())):
    try:
        svc = ProcessingService(user)
        if body.job_id:
            job_id = svc.start_from_saved(body.job_id)
        elif body.plan:
            job_id = svc.start(body.video_id, body.plan)
        else:
            return JSONResponse({"error": "Provide a plan or job_id."}, status_code=400)
        return {"job_id": job_id}
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=400)


@router.get("/{job_id}")
async def get_job(job_id: str, user: CurrentUser = Depends(AuthDependency())):
    try:
        return ProcessingService(user).get_job(job_id).to_dict()
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=404)


@router.get("/{job_id}/download")
async def download_result(job_id: str, user: CurrentUser = Depends(AuthDependency())):
    try:
        path = ProcessingService(user).get_output_path(job_id)
        return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=404)
