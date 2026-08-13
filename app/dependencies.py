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

    is_fallback:
        True when the application is running with the configured
        fallback/demo user instead of a real database user.
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

    1. Read the "session" cookie.
    2. Verify the signed token.
    3. If the database is available, resolve the real user.
    4. If no real user can be resolved and fallback is enabled,
       return the configured fallback user.
    5. Otherwise return None.
    """

    from app.core.security import verify_token

    # ---------------------------------------------------------
    # Read session cookie
    # ---------------------------------------------------------

    signed = request.cookies.get("session")

    token = (
        verify_token(signed)
        if signed
        else None
    )

    # ---------------------------------------------------------
    # Resolve real authenticated user
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
    # No authenticated user
    # ---------------------------------------------------------

    return None


async def get_current_user(
    request: Request,
) -> CurrentUser:
    """
    Required authentication dependency.

    Raises NotAuthenticatedError when there is no
    authenticated or fallback user.
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

    Used by endpoints such as /api/auth/me where a guest
    is a valid state and should not produce an authentication error.
    """

    return resolve_current_user(request)


def get_db_session() -> Session | None:
    """
    Return the current database session when available.
    """

    with get_db() as db:
        return db
