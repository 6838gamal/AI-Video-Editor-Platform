from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, is_database_available


@dataclass
class CurrentUser:
    """
    Represents the currently authenticated user.
    """

    id: str
    email: str
    is_fallback: bool


def resolve_current_user(
    request: Request,
) -> Optional[CurrentUser]:
    """
    Resolve the current user from the signed session cookie.

    Resolution order:

    1. Valid session cookie + database user.
    2. Fallback user when enabled.
    3. None.
    """

    from app.core.security import verify_token

    signed = request.cookies.get("session")

    token = (
        verify_token(signed)
        if signed
        else None
    )

    # ---------------------------------------------------------
    # Real authenticated user
    # ---------------------------------------------------------

    if token and is_database_available():

        with get_db() as db:

            if db is not None:

                from app.modules.auth.services import AuthService

                user = AuthService(db).user_from_token(
                    token
                )

                if user is not None:

                    return CurrentUser(
                        id=str(user.id),
                        email=user.email,
                        is_fallback=False,
                    )

    # ---------------------------------------------------------
    # Fallback user
    # ---------------------------------------------------------

    if settings.allow_fallback_user:

        return CurrentUser(
            id=settings.fallback_user_id,
            email=settings.fallback_user_email,
            is_fallback=True,
        )

    # ---------------------------------------------------------
    # Guest
    # ---------------------------------------------------------

    return None


class AuthDependency:
    """
    FastAPI authentication dependency.

    This class is intentionally kept for backward compatibility
    with existing modules such as editor, processing, youtube, etc.

    IMPORTANT:
    The Request object is explicitly stored in the __call__
    method so FastAPI recognizes it as a Request dependency.
    """

    def __init__(
        self,
        require_auth: bool = True,
    ) -> None:

        self.require_auth = require_auth

    async def __call__(
        self,
        request: Request,
    ) -> Optional[CurrentUser]:

        user = resolve_current_user(request)

        if user is None and self.require_auth:

            from app.core.exceptions import NotAuthenticatedError

            raise NotAuthenticatedError()

        return user


async def get_current_user(
    request: Request,
) -> CurrentUser:
    """
    Required authentication dependency.

    Use this in new routes.
    """

    user = resolve_current_user(request)

    if user is None:

        from app.core.exceptions import NotAuthenticatedError

        raise NotAuthenticatedError()

    return user


async def get_optional_current_user(
    request: Request,
) -> Optional[CurrentUser]:
    """
    Optional authentication dependency.

    A guest is allowed.
    """

    return resolve_current_user(request)


def get_db_session() -> Session | None:
    """
    Return the current database session when available.
    """

    with get_db() as db:
        return db
