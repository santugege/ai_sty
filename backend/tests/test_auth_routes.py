import os
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth_security import SESSION_COOKIE_NAME
from app.db import Base, get_db_session
from app.main import app, http_exception_handler
from app.user_models import UserRow


def make_client(monkeypatch=None, secure_cookie=False):
    if monkeypatch is None:
        os.environ.setdefault("SESSION_SECRET", "test-session-secret")
        os.environ["SESSION_COOKIE_SECURE"] = "true" if secure_cookie else "false"
    else:
        monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
        monkeypatch.setenv(
            "SESSION_COOKIE_SECURE",
            "true" if secure_cookie else "false",
        )
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)

    def override():
        yield session

    app.dependency_overrides[get_db_session] = override
    return TestClient(app), session


def cleanup_overrides():
    app.dependency_overrides.pop(get_db_session, None)


def register_owner(client):
    return client.post(
        "/api/auth/register",
        json={
            "email": "owner@example.com",
            "username": "owner",
            "password": "password123",
        },
    )


def assert_session_cookie_flags(response, secure=False):
    set_cookie = response.headers["set-cookie"]

    assert f"{SESSION_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()
    assert "expires=" in set_cookie.lower() or "max-age=" in set_cookie.lower()
    assert ("Secure" in set_cookie) is secure


def test_register_first_user_sets_admin_cookie_and_returns_user():
    client, _ = make_client()
    try:
        response = register_owner(client)
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert response.json()["user"]["isAdmin"] is True
    assert response.json()["user"]["userId"].startswith("U")
    assert SESSION_COOKIE_NAME in response.cookies


def test_register_sets_secure_session_cookie_when_configured(monkeypatch):
    client, _ = make_client(monkeypatch, secure_cookie=True)
    try:
        response = register_owner(client)
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert_session_cookie_flags(response, secure=True)


def test_login_sets_session_cookie_flags():
    client, _ = make_client()
    try:
        register_owner(client)
        client.post("/api/auth/logout")
        response = client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert_session_cookie_flags(response)


def test_logout_deletes_session_cookie():
    client, _ = make_client()
    try:
        register_owner(client)
        response = client.post("/api/auth/logout")
    finally:
        cleanup_overrides()

    set_cookie = response.headers["set-cookie"]
    assert response.status_code == 200
    assert f"{SESSION_COOKIE_NAME}=" in set_cookie
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie
    assert "HttpOnly" in set_cookie


@pytest.mark.anyio
async def test_http_exception_handler_preserves_headers():
    response = await http_exception_handler(
        None,
        HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        ),
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_logout_and_me_flow():
    client, _ = make_client()
    try:
        register_owner(client)
        client.post("/api/auth/logout")
        assert client.get("/api/auth/me").json() == {"user": None}

        login = client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        me = client.get("/api/auth/me")
    finally:
        cleanup_overrides()

    assert login.status_code == 200
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "owner@example.com"


def test_admin_users_rejects_regular_user_and_allows_admin():
    client, _ = make_client()
    try:
        register_owner(client)
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "username": "user",
                "password": "password123",
            },
        )
        regular_response = client.get("/api/admin/users")
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        admin_response = client.get("/api/admin/users")
    finally:
        cleanup_overrides()

    assert regular_response.status_code == 403
    assert admin_response.status_code == 200
    assert [item["email"] for item in admin_response.json()["users"]] == [
        "owner@example.com",
        "user@example.com",
    ]


def test_admin_users_rejects_missing_and_tampered_cookie():
    client, _ = make_client()
    try:
        missing_cookie_response = client.get("/api/admin/users")
        client.cookies.set(SESSION_COOKIE_NAME, "tampered.session.token")
        tampered_cookie_response = client.get("/api/admin/users")
    finally:
        cleanup_overrides()

    assert missing_cookie_response.status_code == 401
    assert missing_cookie_response.json() == {"error": "请先登录。"}
    assert tampered_cookie_response.status_code == 401
    assert tampered_cookie_response.json() == {"error": "请先登录。"}


def test_inactive_user_is_treated_as_unauthenticated():
    client, session = make_client()
    try:
        response = register_owner(client)
        user = session.get(UserRow, UUID(response.json()["user"]["id"]))
        user.is_active = False
        session.commit()

        me = client.get("/api/auth/me")
        admin_response = client.get("/api/admin/users")
    finally:
        cleanup_overrides()

    assert me.status_code == 200
    assert me.json() == {"user": None}
    assert admin_response.status_code == 401


def test_admin_cors_preflight_allows_patch():
    client, _ = make_client()
    try:
        response = client.options(
            "/api/admin/users/U00000001",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "PATCH",
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_admin_update_does_not_accept_is_admin_promotion():
    client, _ = make_client()
    try:
        register_owner(client)
        client.post("/api/auth/logout")
        user_response = client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "username": "user",
                "password": "password123",
            },
        )
        user_id = user_response.json()["user"]["userId"]
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        response = client.patch(
            f"/api/admin/users/{user_id}",
            json={
                "email": "renamed@example.com",
                "username": "renamed",
                "isActive": False,
                "isAdmin": True,
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 422


def test_admin_password_reset_changes_user_password():
    client, _ = make_client()
    try:
        register_owner(client)
        client.post("/api/auth/logout")
        user_response = client.post(
            "/api/auth/register",
            json={
                "email": "user@example.com",
                "username": "user",
                "password": "password123",
            },
        )
        user_id = user_response.json()["user"]["userId"]
        client.post("/api/auth/logout")
        client.post(
            "/api/auth/login",
            json={"email": "owner@example.com", "password": "password123"},
        )
        reset_response = client.post(
            f"/api/admin/users/{user_id}/password",
            json={"password": "new-password123"},
        )
        client.post("/api/auth/logout")
        login_response = client.post(
            "/api/auth/login",
            json={"email": "user@example.com", "password": "new-password123"},
        )
    finally:
        cleanup_overrides()

    assert reset_response.status_code == 200
    assert login_response.status_code == 200


def test_image_generation_requires_login():
    client, _ = make_client()
    try:
        response = client.post(
            "/api/images/generate",
            data={"toolId": "product", "prompt": "商品图", "size": "1536x1024"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}


def test_agent_sessions_require_login():
    client, _ = make_client()
    try:
        response = client.get("/api/agent/sessions")
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}


def test_create_agent_session_requires_login():
    client, _ = make_client()
    try:
        response = client.post(
            "/api/agent/sessions",
            data={"message": "商品图", "size": "1536x1024"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}


def test_get_agent_session_requires_login():
    client, _ = make_client()
    try:
        response = client.get("/api/agent/sessions/11111111-1111-1111-1111-111111111111")
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}


def test_send_agent_session_message_requires_login():
    client, _ = make_client()
    try:
        response = client.post(
            "/api/agent/sessions/11111111-1111-1111-1111-111111111111/messages",
            data={"message": "商品图", "size": "1536x1024"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}


def test_agent_conversation_requires_login():
    client, _ = make_client()
    try:
        response = client.post(
            "/api/agent/conversation",
            data={"message": "商品图", "size": "1536x1024"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}


def test_agent_conversation_reset_requires_login():
    client, _ = make_client()
    try:
        response = client.post("/api/agent/conversation/reset")
    finally:
        cleanup_overrides()

    assert response.status_code == 401
    assert response.json() == {"error": "请先登录。"}
