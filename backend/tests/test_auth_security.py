from datetime import datetime, timedelta, timezone

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

    assert user_id.startswith("U")
    assert len(user_id) == 9


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
