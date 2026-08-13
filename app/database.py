from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger("video_editor.database")

engine: Engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    connect_args={"connect_timeout": 3},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


_db_available: Optional[bool] = None


def check_database() -> bool:
    global _db_available
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _db_available = True
        return True
    except Exception:
        _db_available = False
        return False


def is_database_available() -> bool:
    if _db_available is None:
        return check_database()
    return _db_available


def mark_database_unavailable() -> None:
    global _db_available
    _db_available = False


def init_db() -> None:
    try:
        from app.modules.auth.models import User  # noqa: F401
        from app.modules.users.models import UserProfile  # noqa: F401

        Base.metadata.create_all(bind=engine)
        _db_available = True
        logger.info("Database initialized and available.")
    except Exception as exc:
        _db_available = False
        logger.warning("Database unavailable at init: %s", exc)


@contextmanager
def get_db() -> Iterator[Optional[Session]]:
    if not is_database_available():
        yield None
        return
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        mark_database_unavailable()
        yield None
    finally:
        session.close()
