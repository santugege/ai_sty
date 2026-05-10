from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

SESSION_COOKIE_NAME = "ai_sty_session"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_password_bytes(password), bcrypt.gensalt()).decode(
        "utf-8"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            _bcrypt_password_bytes(password),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def generate_user_id() -> str:
    return f"U{secrets.token_hex(4).upper()}"


def session_ttl_hours() -> int:
    try:
        return max(1, int(os.getenv("SESSION_TTL_HOURS", "24")))
    except ValueError:
        return 24


def session_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=session_ttl_hours())


def session_cookie_secure() -> bool:
    return os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


def make_session_token(user_internal_id: str, expires_at: datetime | None = None) -> str:
    expires = expires_at or session_expires_at()
    payload = {
        "sub": user_internal_id,
        "exp": int(expires.timestamp()),
    }
    body = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = _signature(body)
    return f"{body}.{signature}"


def read_session_token(token: str) -> str | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None

    expected = _signature(body)
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(_b64decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    try:
        expires_at = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return None
    if expires_at <= int(datetime.now(timezone.utc).timestamp()):
        return None

    subject = payload.get("sub")
    return subject if isinstance(subject, str) and subject else None


def _bcrypt_password_bytes(password: str) -> bytes:
    encoded = password.encode("utf-8")
    if len(encoded) <= 72:
        return encoded
    return hashlib.sha256(encoded).digest()


def _session_secret() -> bytes:
    secret = os.getenv("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET must be set.")
    return secret.encode("utf-8")


def _signature(body: str) -> str:
    digest = hmac.new(_session_secret(), body.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
