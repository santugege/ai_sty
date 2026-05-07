from fastapi.testclient import TestClient

from app.main import app
from app.openai_images import GeneratedImageResult


client = TestClient(app)


def test_health_route_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_image_route_returns_missing_key_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "a quiet studio", "size": "1024x1024"},
    )

    assert response.status_code == 500
    assert response.json() == {"error": "服务器未配置 OPENAI_API_KEY。"}


def test_image_route_returns_validation_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "   ", "size": "1024x1024"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "请输入画面描述。"}


def test_image_route_returns_generated_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")

    def fake_request_image_from_openai(valid_request, api_key, model):
        assert valid_request.tool.id == "creator"
        assert valid_request.prompt == "a quiet studio"
        assert api_key == "key"
        assert model == "gpt-image-2"
        return GeneratedImageResult(src="data:image/png;base64,abc123")

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "a quiet studio", "size": "1024x1024"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "image": {
            "src": "data:image/png;base64,abc123",
            "mimeType": "image/png",
            "revisedPrompt": None,
        }
    }


def test_image_route_offloads_openai_request_to_threadpool(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    offload_calls = []

    def fake_request_image_from_openai(valid_request, api_key, model):
        return GeneratedImageResult(src="data:image/png;base64,abc123")

    async def fake_run_in_threadpool(func, *args, **kwargs):
        offload_calls.append((func, args, kwargs))
        return func(*args, **kwargs)

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )
    monkeypatch.setattr(
        "app.main.run_in_threadpool",
        fake_run_in_threadpool,
        raising=False,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "a quiet studio", "size": "1024x1024"},
    )

    assert response.status_code == 200
    assert offload_calls
    assert offload_calls[0][0] is fake_request_image_from_openai
    assert offload_calls[0][1][0].tool.id == "creator"
    assert offload_calls[0][2] == {"api_key": "key", "model": "gpt-image-2"}


def test_image_route_passes_uploaded_image_to_openai_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    captured_request = {}

    def fake_request_image_from_openai(valid_request, api_key, model):
        captured_request["valid_request"] = valid_request
        return GeneratedImageResult(src="data:image/png;base64,edited")

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "restore", "prompt": "修复划痕", "size": "1024x1024"},
        files={"image": ("photo.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 200
    valid_request = captured_request["valid_request"]
    assert valid_request.tool.id == "restore"
    assert valid_request.image_bytes == b"image-bytes"
    assert valid_request.image_name == "photo.png"
    assert valid_request.image_type == "image/png"


def test_image_route_sanitizes_unexpected_error_message(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    def fake_request_image_from_openai(valid_request, api_key, model):
        raise Exception("sk-test stack trace")

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "a quiet studio", "size": "1024x1024"},
    )

    assert response.status_code == 502
    assert response.json() == {"error": "图片生成失败，请稍后重试。"}
