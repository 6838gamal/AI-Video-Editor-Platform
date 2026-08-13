from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, is_database_available


@dataclass
class CurrentUser:
    id: str
    email: str
    is_fallback: bool


class AuthDependency:
    """Resolves the current user from a signed session cookie.

    Falls back to the demo user when the database is unavailable or no
    session is present and ALLOW_FALLBACK_USER is true.
    """

    def __init__(self, require_auth: bool = True) -> None:
        self.require_auth = require_auth

    async def __call__(self, request: Request) -> CurrentUser:
        user = self._resolve(request)
        if user is None and self.require_auth:
            from app.core.exceptions import NotAuthenticatedError

            raise NotAuthenticatedError()
        return user

    def _resolve(self, request: Request) -> Optional[CurrentUser]:
        from app.core.security import verify_token

        signed = request.cookies.get("session")
        token = verify_token(signed) if signed else None
        if token and is_database_available():
            with get_db() as db:
                if db is not None:
                    from app.modules.auth.services import AuthService

                    user = AuthService(db).user_from_token(token)
                    if user is not None:
                        return CurrentUser(id=str(user.id), email=user.email, is_fallback=False)

        if settings.allow_fallback_user:
            return CurrentUser(
                id=settings.fallback_user_id,
                email=settings.fallback_user_email,
                is_fallback=True,
            )
        return None


def get_current_user(request: Request) -> CurrentUser:
    return AuthDependency(require_auth=False)(request)  # type: ignore[arg-type]


def get_db_session() -> Session | None:
    with get_db() as db:
        return db
