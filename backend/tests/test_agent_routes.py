import base64

from fastapi.testclient import TestClient

from app.image_request import MAX_IMAGE_BYTES
from app.main import app


client = TestClient(app)
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+p5qgoAAAAABJRU5ErkJggg=="
)


def test_create_agent_session_requires_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/agent/sessions",
        data={"instruction": "Make it brighter", "size": "1536x1024"},
    )

    assert response.status_code == 400
    assert "error" in response.json()


def test_create_agent_session_rejects_unsupported_image_type(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    service_was_built = False

    def fail_if_called(db):
        nonlocal service_was_built
        service_was_built = True
        raise AssertionError("service should not be built for invalid uploads")

    monkeypatch.setattr("app.main.build_agent_service", fail_if_called)

    response = client.post(
        "/api/agent/sessions",
        data={"instruction": "Make it brighter", "size": "1536x1024"},
        files={"image": ("product.gif", b"gif89a", "image/gif")},
    )

    assert response.status_code == 400
    assert "error" in response.json()
    assert service_was_built is False


def test_create_agent_session_rejects_oversized_image_before_service(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    service_was_built = False

    def fail_if_called(db):
        nonlocal service_was_built
        service_was_built = True
        raise AssertionError("service should not be built for invalid uploads")

    monkeypatch.setattr("app.main.build_agent_service", fail_if_called)

    response = client.post(
        "/api/agent/sessions",
        data={"instruction": "Make it brighter", "size": "1536x1024"},
        files={
            "image": (
                "product.png",
                b"x" * (MAX_IMAGE_BYTES + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 400
    assert "error" in response.json()
    assert service_was_built is False


def test_agent_session_routes_exist():
    routes = {route.path for route in app.routes}

    assert "/api/agent/sessions" in routes
    assert "/api/agent/sessions/{session_id}/messages" in routes
    assert "/api/agent/sessions/{session_id}" in routes
    assert "/api/agent/sessions/{session_id}/versions/{version_id}/restore" in routes


def test_send_agent_message_unexpected_failure_returns_json_500(monkeypatch):
    class FakeService:
        def send_message(self, session_id, instruction, size):
            raise RuntimeError("sk-test stack trace")

    monkeypatch.setattr("app.main.build_agent_service", lambda db: FakeService())

    response = client.post(
        "/api/agent/sessions/00000000-0000-0000-0000-000000000001/messages",
        json={"instruction": "Make it brighter", "size": "1536x1024"},
    )

    assert response.status_code == 500
    assert response.json() == {"error": "Agent request failed."}


def test_send_agent_message_offloads_service_call_to_threadpool(monkeypatch):
    offload_calls = []

    class FakeEnvelope:
        def model_dump(self, mode):
            return {"ok": True}

    class FakeService:
        def send_message(self, session_id, instruction, size):
            return FakeEnvelope()

    async def fake_run_in_threadpool(func, *args, **kwargs):
        offload_calls.append((func, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr("app.main.build_agent_service", lambda db: FakeService())
    monkeypatch.setattr("app.main.run_in_threadpool", fake_run_in_threadpool)

    response = client.post(
        "/api/agent/sessions/00000000-0000-0000-0000-000000000001/messages",
        json={"instruction": "Make it brighter", "size": "1536x1024"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert offload_calls


def test_create_agent_session_offloads_service_call_to_threadpool(monkeypatch):
    offload_calls = []

    class FakeEnvelope:
        def model_dump(self, mode):
            return {"ok": True}

    class FakeService:
        def create_session(self, **kwargs):
            return FakeEnvelope()

    async def fake_run_in_threadpool(func, *args, **kwargs):
        offload_calls.append((func, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr("app.main.build_agent_service", lambda db: FakeService())
    monkeypatch.setattr("app.main.run_in_threadpool", fake_run_in_threadpool)

    response = client.post(
        "/api/agent/sessions",
        data={"instruction": "Make it brighter", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert offload_calls


def test_create_agent_session_builds_service_inside_threadpool(monkeypatch):
    in_threadpool = False

    class FakeEnvelope:
        def model_dump(self, mode):
            return {"ok": True}

    class FakeService:
        def create_session(self, **kwargs):
            return FakeEnvelope()

    async def fake_run_in_threadpool(func, *args, **kwargs):
        nonlocal in_threadpool
        in_threadpool = True
        try:
            return func(*args, **kwargs)
        finally:
            in_threadpool = False

    def fake_build_agent_service(db):
        assert in_threadpool
        return FakeService()

    monkeypatch.setattr("app.main.build_agent_service", fake_build_agent_service)
    monkeypatch.setattr("app.main.run_in_threadpool", fake_run_in_threadpool)

    response = client.post(
        "/api/agent/sessions",
        data={"instruction": "Make it brighter", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
