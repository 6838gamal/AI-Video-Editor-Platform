from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError, UserExistsError
from app.core.security import generate_session_token, hash_password, sign_token, verify_password
from app.modules.auth.models import User


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, email: str, password: str) -> User:
        email = email.strip().lower()
        try:
            existing = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        except SQLAlchemyError:
            existing = None
        if existing is not None:
            raise UserExistsError()
        if len(password) < 6:
            raise InvalidCredentialsError("Password must be at least 6 characters.")
        user = User(email=email, password_hash=hash_password(password))
        self.db.add(user)
        self.db.flush()
        return user

    def login(self, email: str, password: str) -> User:
        email = email.strip().lower()
        try:
            user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        except SQLAlchemyError:
            user = None
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return user

    def user_from_token(self, token: str) -> Optional[User]:
        try:
            return self.db.execute(select(User).where(User.id == _token_to_id(token))).scalar_one_or_none()
        except SQLAlchemyError:
            return None

    @staticmethod
    def issue_session(user: User) -> tuple[str, str]:
        token = f"{user.id}:{generate_session_token()}"
        return token, sign_token(token)


def _token_to_id(token: str) -> str:
    return token.split(":", 1)[0]
