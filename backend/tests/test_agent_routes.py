import base64
import uuid

from fastapi.testclient import TestClient

import app.main as app_main
from app.agent_service import AgentInputError
from app.db import get_db_session
from app.image_request import MAX_IMAGE_BYTES
from app.main import app


client = TestClient(app)
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+p5qgoAAAAABJRU5ErkJggg=="
)


def test_conversation_routes_exist():
    routes = {route.path for route in app.routes}

    assert "/api/agent/conversation" in routes
    assert "/api/agent/conversation/reset" in routes
    assert "/api/agent/sessions" in routes
    assert "/api/agent/sessions/{session_id}" in routes
    assert "/api/agent/sessions/{session_id}/messages" in routes
    assert "/api/agent/sessions/{session_id}/versions/{version_id}/restore" not in routes


def override_db_session(db):
    def override():
        yield db

    app.dependency_overrides[get_db_session] = override


def test_build_image_storage_uses_minio_defaults(monkeypatch):
    calls = []

    class FakeStorage:
        def __init__(
            self,
            bucket,
            endpoint_url=None,
            access_key=None,
            secret_key=None,
            public_endpoint=None,
        ):
            calls.append(
                {
                    "bucket": bucket,
                    "endpoint_url": endpoint_url,
                    "access_key": access_key,
                    "secret_key": secret_key,
                    "public_endpoint": public_endpoint,
                }
            )

    monkeypatch.setattr(app_main, "MinioImageStorage", FakeStorage, raising=False)
    monkeypatch.delenv("MINIO_BUCKET", raising=False)
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    monkeypatch.delenv("MINIO_ACCESS_KEY", raising=False)
    monkeypatch.delenv("MINIO_SECRET_KEY", raising=False)
    monkeypatch.delenv("MINIO_PUBLIC_ENDPOINT", raising=False)

    storage = app_main.build_image_storage()

    assert isinstance(storage, FakeStorage)
    assert calls == [
        {
            "bucket": "agent-images",
            "endpoint_url": "http://localhost:9000",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "public_endpoint": "http://localhost:9000",
        }
    ]


def test_build_agent_service_wires_persistent_dependencies(monkeypatch):
    db = object()
    storage = object()
    image_client = object()
    repo_calls = []
    tool_calls = []
    turn_calls = []
    summary_calls = []

    class FakeRepo:
        def __init__(self, session):
            repo_calls.append(session)

    class FakeTool:
        def __init__(self, image_client, image_model):
            tool_calls.append(
                {"image_client": image_client, "image_model": image_model}
            )

    def fake_image_client(**kwargs):
        return image_client

    def fake_turn(**kwargs):
        turn_calls.append(kwargs)
        return "turn"

    def fake_summary(**kwargs):
        summary_calls.append(kwargs)
        return "summary"

    monkeypatch.setattr(app_main, "AgentRepository", FakeRepo, raising=False)
    monkeypatch.setattr(app_main, "GptImage2EditTool", FakeTool)
    monkeypatch.setattr(app_main, "build_image_storage", lambda: storage, raising=False)
    monkeypatch.setattr(app_main, "create_openai_image_client", fake_image_client)
    monkeypatch.setattr(app_main, "request_conversation_turn", fake_turn)
    monkeypatch.setattr(app_main, "request_conversation_summary", fake_summary, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-test")
    monkeypatch.setenv("OPENAI_AGENT_MODEL", "gpt-agent-test")

    service = app_main.build_agent_service(db)

    assert repo_calls == [db]
    assert service.storage is storage
    assert "gpt_image_2_edit" in service.tools
    assert tool_calls == [
        {"image_client": image_client, "image_model": "gpt-image-test"}
    ]
    assert service.planner(
        user_message="hello",
        recent_messages=[],
        has_current_image=False,
        uploaded_image_count=0,
        previous_response_id=None,
        summary="keep this context",
    ) == "turn"
    assert turn_calls[0]["summary"] == "keep this context"
    assert turn_calls[0]["api_key"] == "sk-test"
    assert turn_calls[0]["agent_model"] == "gpt-agent-test"
    assert service.summarizer(previous_summary="old", recent_messages=[]) == "summary"
    assert summary_calls[0]["previous_summary"] == "old"


def test_create_session_route_accepts_message_size_and_multiple_images(monkeypatch):
    db = object()
    build_calls = []
    service_calls = []

    class FakeEnvelope:
        def model_dump(self, mode):
            return {"conversation": {"id": "session-1"}, "messages": []}

    class FakeService:
        def create_session(self, message, attachments, size):
            service_calls.append(
                {"message": message, "attachments": attachments, "size": size}
            )
            return FakeEnvelope()

    def build_service(session):
        build_calls.append(session)
        return FakeService()

    override_db_session(db)
    monkeypatch.setattr(app_main, "build_agent_service", build_service, raising=False)
    try:
        response = client.post(
            "/api/agent/sessions",
            data={"message": "start session", "size": "1024x1024"},
            files=[
                ("images", ("first.png", TINY_PNG, "image/png")),
                ("images", ("second.png", TINY_PNG, "image/png")),
            ],
        )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    assert response.json() == {"conversation": {"id": "session-1"}, "messages": []}
    assert build_calls == [db]
    assert service_calls == [
        {
            "message": "start session",
            "attachments": [
                {
                    "image_bytes": TINY_PNG,
                    "image_name": "first.png",
                    "mime_type": "image/png",
                },
                {
                    "image_bytes": TINY_PNG,
                    "image_name": "second.png",
                    "mime_type": "image/png",
                },
            ],
            "size": "1024x1024",
        }
    ]


def test_list_sessions_route_returns_service_json(monkeypatch):
    db = object()
    build_calls = []

    class FakeEnvelope:
        def model_dump(self, mode):
            return {"sessions": [{"id": "session-1", "title": "One"}]}

    class FakeService:
        def list_sessions(self):
            return FakeEnvelope()

    def build_service(session):
        build_calls.append(session)
        return FakeService()

    override_db_session(db)
    monkeypatch.setattr(app_main, "build_agent_service", build_service, raising=False)
    try:
        response = client.get("/api/agent/sessions")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    assert response.json() == {"sessions": [{"id": "session-1", "title": "One"}]}
    assert build_calls == [db]


def test_get_session_route_passes_uuid_to_service(monkeypatch):
    db = object()
    session_id = uuid.uuid4()
    service_calls = []

    class FakeEnvelope:
        def model_dump(self, mode):
            return {"conversation": {"id": str(session_id)}}

    class FakeService:
        def get_session(self, session_uuid):
            service_calls.append(session_uuid)
            return FakeEnvelope()

    override_db_session(db)
    monkeypatch.setattr(
        app_main, "build_agent_service", lambda session: FakeService(), raising=False
    )
    try:
        response = client.get(f"/api/agent/sessions/{session_id}")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    assert response.json() == {"conversation": {"id": str(session_id)}}
    assert service_calls == [session_id]


def test_session_message_route_passes_uuid_message_size_and_images(monkeypatch):
    db = object()
    session_id = uuid.uuid4()
    service_calls = []

    class FakeEnvelope:
        def model_dump(self, mode):
            return {"conversation": {"id": str(session_id)}, "messages": []}

    class FakeService:
        def send_session_message(self, session_uuid, message, attachments, size):
            service_calls.append(
                {
                    "session_id": session_uuid,
                    "message": message,
                    "attachments": attachments,
                    "size": size,
                }
            )
            return FakeEnvelope()

    override_db_session(db)
    monkeypatch.setattr(
        app_main, "build_agent_service", lambda session: FakeService(), raising=False
    )
    try:
        response = client.post(
            f"/api/agent/sessions/{session_id}/messages",
            data={"message": "edit this", "size": "1536x1024"},
            files={"images": ("product.png", TINY_PNG, "image/png")},
        )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    assert response.json() == {"conversation": {"id": str(session_id)}, "messages": []}
    assert service_calls == [
        {
            "session_id": session_id,
            "message": "edit this",
            "attachments": [
                {
                    "image_bytes": TINY_PNG,
                    "image_name": "product.png",
                    "mime_type": "image/png",
                }
            ],
            "size": "1536x1024",
        }
    ]


def test_session_route_uses_agent_error_response(monkeypatch):
    db = object()

    class FakeService:
        def create_session(self, message, attachments, size):
            raise AgentInputError("bad session input")

    override_db_session(db)
    monkeypatch.setattr(
        app_main, "build_agent_service", lambda session: FakeService(), raising=False
    )
    try:
        response = client.post(
            "/api/agent/sessions",
            data={"message": "", "size": "1536x1024"},
        )
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 400
    assert response.json() == {"error": "bad session input"}


def test_conversation_accepts_text_and_image_attachment(monkeypatch):
    class FakeEnvelope:
        def model_dump(self, mode):
            return {"messages": [{"role": "assistant", "content": "ok"}]}

    class FakeService:
        def send_message(self, message, attachments, size):
            assert message == "把背景换成白色"
            assert size == "1536x1024"
            assert attachments == [
                {
                    "image_bytes": TINY_PNG,
                    "image_name": "product.png",
                    "mime_type": "image/png",
                }
            ]
            return FakeEnvelope()

    monkeypatch.setattr("app.main.build_conversation_service", lambda: FakeService())

    response = client.post(
        "/api/agent/conversation",
        data={"message": "把背景换成白色", "size": "1536x1024"},
        files={"images": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {"messages": [{"role": "assistant", "content": "ok"}]}


def test_conversation_allows_text_follow_up_without_attachment(monkeypatch):
    class FakeEnvelope:
        def model_dump(self, mode):
            return {"ok": True}

    class FakeService:
        def send_message(self, message, attachments, size):
            assert message == "再亮一点"
            assert attachments == []
            return FakeEnvelope()

    monkeypatch.setattr("app.main.build_conversation_service", lambda: FakeService())

    response = client.post(
        "/api/agent/conversation",
        data={"message": "再亮一点", "size": "1536x1024"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_conversation_rejects_unsupported_image_type_before_service(monkeypatch):
    service_was_built = False

    def fail_if_called():
        nonlocal service_was_built
        service_was_built = True
        raise AssertionError("service should not be built for invalid uploads")

    monkeypatch.setattr("app.main.build_conversation_service", fail_if_called)

    response = client.post(
        "/api/agent/conversation",
        data={"message": "编辑这张图"},
        files={"images": ("product.gif", b"gif89a", "image/gif")},
    )

    assert response.status_code == 400
    assert "error" in response.json()
    assert service_was_built is False


def test_conversation_rejects_oversized_image_before_service(monkeypatch):
    service_was_built = False

    def fail_if_called():
        nonlocal service_was_built
        service_was_built = True
        raise AssertionError("service should not be built for invalid uploads")

    monkeypatch.setattr("app.main.build_conversation_service", fail_if_called)

    response = client.post(
        "/api/agent/conversation",
        data={"message": "编辑这张图"},
        files={
            "images": (
                "product.png",
                b"x" * (MAX_IMAGE_BYTES + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 400
    assert "error" in response.json()
    assert service_was_built is False


def test_conversation_unexpected_failure_returns_json_500(monkeypatch):
    class FakeService:
        def send_message(self, message, attachments, size):
            raise RuntimeError("sk-test stack trace")

    monkeypatch.setattr("app.main.build_conversation_service", lambda: FakeService())

    response = client.post(
        "/api/agent/conversation",
        data={"message": "再亮一点", "size": "1536x1024"},
    )

    assert response.status_code == 500
    assert response.json() == {"error": "Agent request failed."}


def test_reset_conversation_returns_empty_envelope(monkeypatch):
    class FakeEnvelope:
        def model_dump(self, mode):
            return {"messages": [], "currentImage": None}

    class FakeService:
        def reset(self):
            return FakeEnvelope()

    monkeypatch.setattr("app.main.build_conversation_service", lambda: FakeService())

    response = client.post("/api/agent/conversation/reset")

    assert response.status_code == 200
    assert response.json() == {"messages": [], "currentImage": None}
