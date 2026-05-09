import base64

from fastapi.testclient import TestClient

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
    assert "/api/agent/sessions" not in routes
    assert "/api/agent/sessions/{session_id}/versions/{version_id}/restore" not in routes


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
