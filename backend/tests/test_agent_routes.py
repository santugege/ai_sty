from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_agent_session_requires_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/agent/sessions",
        data={"instruction": "Make it brighter", "size": "1536x1024"},
    )

    assert response.status_code == 400
    assert "error" in response.json()


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
        files={"image": ("product.png", b"image-bytes", "image/png")},
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
        files={"image": ("product.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
