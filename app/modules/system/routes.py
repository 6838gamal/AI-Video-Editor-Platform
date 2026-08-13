from __future__ import annotations

from fastapi import APIRouter

from app.modules.system.services import SystemService

router = APIRouter(tags=["system"])


@router.get("/api/system/status")
async def system_status():
    return SystemService.status()
