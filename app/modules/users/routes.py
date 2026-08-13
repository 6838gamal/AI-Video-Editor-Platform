from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import CurrentUser, AuthDependency

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
async def me(user: CurrentUser = Depends(AuthDependency(require_auth=False))):
    return {"id": user.id, "email": user.email, "fallback": user.is_fallback}
