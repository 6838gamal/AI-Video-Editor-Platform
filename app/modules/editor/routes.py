from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.exceptions import VideoEditorError
from app.dependencies import AuthDependency, CurrentUser
from app.modules.editor.schemas import EditingPlan
from app.modules.editor.services import EditorService

router = APIRouter(prefix="/api/editor", tags=["editor"])


class PlanRequest(BaseModel):
    video_id: str
    plan: EditingPlan


class ValidateRequest(BaseModel):
    plan: EditingPlan


@router.post("/plan")
async def save_plan(body: PlanRequest, user: CurrentUser = Depends(AuthDependency())):
    try:
        errors = body.plan.validate_plan()
        if errors:
            return JSONResponse({"error": "Invalid plan", "errors": errors}, status_code=400)
        job_id = EditorService(user).save_plan(body.video_id, body.plan)
        return {"job_id": job_id, "valid": True}
    except VideoEditorError as exc:
        return JSONResponse({"error": exc.message}, status_code=400)


@router.post("/validate")
async def validate_plan(body: ValidateRequest, user: CurrentUser = Depends(AuthDependency())):
    errors = body.plan.validate_plan()
    return {"valid": not errors, "errors": errors}
