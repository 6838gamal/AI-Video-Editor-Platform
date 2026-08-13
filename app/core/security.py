from __future__ import annotations

import hmac
import secrets

from bcrypt import checkpw, gensalt, hashpw

from app.config import settings


def hash_password(password: str) -> str:
    return hashpw(password.encode("utf-8"), gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def sign_token(token: str) -> str:
    key = settings.session_secret.encode("utf-8")
    sig = hmac.new(key, token.encode("utf-8"), "sha256").hexdigest()
    return f"{token}.{sig}"


def verify_token(signed: str) -> str | None:
    if not signed or "." not in signed:
        return None
    token, sig = signed.rsplit(".", 1)
    expected = hmac.new(settings.session_secret.encode("utf-8"), token.encode("utf-8"), "sha256").hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return token
