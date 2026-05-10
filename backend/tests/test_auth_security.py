import base64
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from app.auth_security import (
    generate_user_id,
    hash_password,
    make_session_token,
    read_session_token,
    verify_password,
)


def test_hash_password_does_not_store_plaintext_and_verifies():
    password_hash = hash_password("strong-password")

    assert password_hash != "strong-password"
    assert verify_password("strong-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_generate_user_id_is_business_readable():
    user_id = generate_user_id()

    assert re.match(r"^U[0-9A-F]{8}$", user_id)


def test_signed_session_token_round_trips_user_id(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    token = make_session_token("00000000-0000-0000-0000-000000000001", expires_at)

    assert read_session_token(token) == "00000000-0000-0000-0000-000000000001"


def test_expired_session_token_returns_none(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    token = make_session_token("00000000-0000-0000-0000-000000000001", expires_at)

    assert read_session_token(token) is None


def test_tampered_session_token_returns_none(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    token = make_session_token("00000000-0000-0000-0000-000000000001", expires_at)

    assert read_session_token(token + "x") is None


def test_signed_malformed_session_payload_returns_none(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    payload = {"sub": "00000000-0000-0000-0000-000000000001", "exp": None}
    body = _b64encode(json.dumps(payload).encode("utf-8"))
    signature = _signature("test-secret", body)

    assert read_session_token(f"{body}.{signature}") is None


def test_signed_non_object_session_payload_returns_none(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    body = _b64encode(json.dumps([]).encode("utf-8"))
    signature = _signature("test-secret", body)

    assert read_session_token(f"{body}.{signature}") is None


def test_session_token_requires_configured_secret(monkeypatch):
    monkeypatch.delenv("SESSION_SECRET", raising=False)

    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        make_session_token("00000000-0000-0000-0000-000000000001")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _signature(secret: str, body: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)
