from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from app.core.exceptions import VideoEditorError
from app.database import get_db, is_database_available
from app.dependencies import (
    CurrentUser,
    get_optional_current_user,
)
from app.modules.auth.services import AuthService


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


# =========================================================
# Request Schemas
# =========================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =========================================================
# Session Cookie
# =========================================================

def _set_session_cookie(
    response: JSONResponse,
    signed_token: str,
) -> None:
    """
    Store the signed authentication token in a secure
    HTTP-only session cookie.
    """

    response.set_cookie(
        key="session",
        value=signed_token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 7,
        path="/",
    )


# =========================================================
# Register
# =========================================================

@router.post("/register")
async def register(
    body: RegisterRequest,
):
    """
    Register a new user.

    Registration requires the database to be available.
    """

    if not is_database_available():

        return JSONResponse(
            {
                "ok": False,
                "error": (
                    "Database unavailable. "
                    "Registration is disabled "
                    "in degraded mode."
                ),
            },
            status_code=503,
        )

    with get_db() as db:

        if db is None:

            return JSONResponse(
                {
                    "ok": False,
                    "error": "Database unavailable.",
                },
                status_code=503,
            )

        try:

            service = AuthService(db)

            user = service.register(
                body.email,
                body.password,
            )

            token, signed = (
                AuthService.issue_session(user)
            )

            response = JSONResponse(
                {
                    "ok": True,
                    "id": str(user.id),
                    "email": user.email,
                }
            )

            _set_session_cookie(
                response,
                signed,
            )

            return response

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
                    "error": "تعذر إنشاء الحساب.",
                },
                status_code=500,
            )


# =========================================================
# Login
# =========================================================

@router.post("/login")
async def login(
    body: LoginRequest,
):
    """
    Authenticate a user and create a session cookie.
    """

    if not is_database_available():

        return JSONResponse(
            {
                "ok": False,
                "error": (
                    "Database unavailable. "
                    "Login is disabled "
                    "in degraded mode."
                ),
            },
            status_code=503,
        )

    with get_db() as db:

        if db is None:

            return JSONResponse(
                {
                    "ok": False,
                    "error": "Database unavailable.",
                },
                status_code=503,
            )

        try:

            service = AuthService(db)

            user = service.login(
                body.email,
                body.password,
            )

            token, signed = (
                AuthService.issue_session(user)
            )

            response = JSONResponse(
                {
                    "ok": True,
                    "id": str(user.id),
                    "email": user.email,
                }
            )

            _set_session_cookie(
                response,
                signed,
            )

            return response

        except VideoEditorError as exc:

            return JSONResponse(
                {
                    "ok": False,
                    "error": exc.message,
                },
                status_code=401,
            )

        except Exception:

            return JSONResponse(
                {
                    "ok": False,
                    "error": "تعذر تسجيل الدخول.",
                },
                status_code=500,
            )


# =========================================================
# Logout
# =========================================================

@router.post("/logout")
async def logout():
    """
    Clear the current session cookie.
    """

    response = JSONResponse(
        {
            "ok": True,
        }
    )

    response.delete_cookie(
        key="session",
        path="/",
    )

    return response


# =========================================================
# Current User
# =========================================================

@router.get("/me")
async def me(
    user: Optional[CurrentUser] = Depends(
        get_optional_current_user
    ),
):
    """
    Return the current authentication state.

    Possible states:

    authenticated:
        A real authenticated database user.

    fallback:
        The configured fallback user.

    guest:
        No session and no fallback user.
    """

    # ---------------------------------------------------------
    # Guest
    # ---------------------------------------------------------

    if user is None:

        return {
            "authenticated": False,
            "fallback": False,
            "guest": True,
            "id": None,
            "email": None,
        }

    # ---------------------------------------------------------
    # Authenticated / Fallback
    # ---------------------------------------------------------

    return {
        "authenticated": not user.is_fallback,
        "fallback": user.is_fallback,
        "guest": False,
        "id": user.id,
        "email": user.email,
    }
