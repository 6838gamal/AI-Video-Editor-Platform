from __future__ import annotations

from sqlalchemy.orm import Session

from app.modules.users.models import UserProfile


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile(self, user_id: str) -> UserProfile | None:
        return self.db.get(UserProfile, user_id)
