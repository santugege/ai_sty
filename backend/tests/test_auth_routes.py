import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth_security import SESSION_COOKIE_NAME
from app.db import Base, get_db_session
from app.main import app


def make_client():
    os.environ.setdefault("SESSION_SECRET", "test-session-secret")
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


def test_register_first_user_sets_admin_cookie_and_returns_user():
    client, _ = make_client()
    try:
        response = client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert response.json()["user"]["isAdmin"] is True
    assert response.json()["user"]["userId"].startswith("U")
    assert SESSION_COOKIE_NAME in response.cookies


def test_login_logout_and_me_flow():
    client, _ = make_client()
    try:
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
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
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
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


def test_admin_update_does_not_accept_is_admin_promotion():
    client, _ = make_client()
    try:
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
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

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "renamed@example.com"
    assert response.json()["user"]["username"] == "renamed"
    assert response.json()["user"]["isActive"] is False
    assert response.json()["user"]["isAdmin"] is False


def test_admin_password_reset_changes_user_password():
    client, _ = make_client()
    try:
        client.post(
            "/api/auth/register",
            json={
                "email": "owner@example.com",
                "username": "owner",
                "password": "password123",
            },
        )
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
