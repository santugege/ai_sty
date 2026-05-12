from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.main as app_main
from app.agent_service import ConversationTurnDecision
from app.db import Base, get_db_session
from app.main import app


def make_client(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
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
    return TestClient(app)


def cleanup_overrides():
    app.dependency_overrides.pop(get_db_session, None)


def register(client: TestClient, email: str, username: str):
    return client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "password123",
        },
    )


def test_agent_sessions_are_isolated_between_users(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(app_main, "build_image_storage", lambda: object())
    monkeypatch.setattr(app_main, "create_openai_image_client", lambda **kwargs: object())
    monkeypatch.setattr(
        app_main,
        "request_conversation_turn",
        lambda **kwargs: ConversationTurnDecision(
            action="answer",
            assistant_message="Owner-only answer.",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_owner",
        ),
    )
    monkeypatch.setattr(
        app_main,
        "request_conversation_summary",
        lambda **kwargs: "summary",
        raising=False,
    )
    monkeypatch.setattr(
        app_main,
        "ChatGptImageGenerateTool",
        lambda image_client, image_model: object(),
    )
    monkeypatch.setattr(
        app_main,
        "ChatGptImageEditTool",
        lambda image_client, image_model: object(),
    )
    client = make_client(monkeypatch)
    try:
        register(client, "owner@example.com", "owner")
        owner_create = client.post(
            "/api/agent/sessions",
            data={"message": "Owner private prompt.", "size": "1536x1024"},
        )
        owner_session_id = owner_create.json()["conversation"]["id"]
        owner_list = client.get("/api/agent/sessions")

        client.post("/api/auth/logout")
        register(client, "user@example.com", "user")
        other_list = client.get("/api/agent/sessions")
        other_get = client.get(f"/api/agent/sessions/{owner_session_id}")
        other_send = client.post(
            f"/api/agent/sessions/{owner_session_id}/messages",
            data={"message": "Should not write.", "size": "1536x1024"},
        )
    finally:
        cleanup_overrides()

    assert owner_create.status_code == 200
    assert [item["id"] for item in owner_list.json()["sessions"]] == [owner_session_id]
    assert other_list.status_code == 200
    assert other_list.json()["sessions"] == []
    assert other_get.status_code == 400
    assert other_get.json() == {"error": "Conversation not found."}
    assert other_send.status_code == 400
    assert other_send.json() == {"error": "Conversation not found."}
