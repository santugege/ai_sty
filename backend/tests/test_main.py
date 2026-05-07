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
