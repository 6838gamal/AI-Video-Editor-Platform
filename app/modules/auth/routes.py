from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from app.core.exceptions import VideoEditorError
from app.database import get_db, is_database_available
from app.dependencies import AuthDependency, CurrentUser
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def _set_session_cookie(response: JSONResponse, signed_token: str) -> None:
    response.set_cookie(
        key="session",
        value=signed_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 7,
    )


@router.post("/register")
async def register(body: RegisterRequest):
    if not is_database_available():
        return JSONResponse(
            {"error": "Database unavailable. Registration is disabled in degraded mode."},
            status_code=503,
        )
    with get_db() as db:
        if db is None:
            return JSONResponse({"error": "Database unavailable."}, status_code=503)
        try:
            user = AuthService(db).register(body.email, body.password)
            token, signed = AuthService.issue_session(user)
            resp = JSONResponse({"id": str(user.id), "email": user.email})
            _set_session_cookie(resp, signed)
            return resp
        except VideoEditorError as exc:
            return JSONResponse({"error": exc.message}, status_code=400)


@router.post("/login")
async def login(body: LoginRequest):
    if not is_database_available():
        return JSONResponse(
            {"error": "Database unavailable. Login is disabled in degraded mode."},
            status_code=503,
        )
    with get_db() as db:
        if db is None:
            return JSONResponse({"error": "Database unavailable."}, status_code=503)
        try:
            user = AuthService(db).login(body.email, body.password)
            token, signed = AuthService.issue_session(user)
            resp = JSONResponse({"id": str(user.id), "email": user.email})
            _set_session_cookie(resp, signed)
            return resp
        except VideoEditorError as exc:
            return JSONResponse({"error": exc.message}, status_code=401)


@router.post("/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session")
    return resp


@router.get("/me")
async def me(user: CurrentUser = Depends(AuthDependency(require_auth=False))):
    return {"id": user.id, "email": user.email, "fallback": user.is_fallback}
