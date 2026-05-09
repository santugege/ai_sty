import base64

from fastapi.testclient import TestClient

from app.main import app
from app.main import frontend_origins
from app.openai_images import GeneratedImageEnvelope, GeneratedImageResult


client = TestClient(app)
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+p5qgoAAAAABJRU5ErkJggg=="
)


def test_health_route_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_frontend_origins_allows_localhost_and_127_by_default(monkeypatch):
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)

    assert frontend_origins() == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_frontend_origins_allows_comma_separated_values(monkeypatch):
    monkeypatch.setenv(
        "FRONTEND_ORIGIN",
        "http://localhost:3000, http://127.0.0.1:3000",
    )

    assert frontend_origins() == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_frontend_origins_adds_127_alias_for_localhost(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:3000")

    assert frontend_origins() == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_image_route_returns_missing_key_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post(
        "/api/images/generate",
        data={"toolId": "product", "prompt": "商品场景", "size": "1536x1024"},
    )

    assert response.status_code == 500
    assert response.json() == {"error": "服务器未配置 OPENAI_API_KEY。"}


def test_image_route_returns_validation_error(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/images/generate",
        data={"toolId": "product", "size": "1536x1024", "imageCount": "3"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "生成数量仅支持 1、2 或 4 张。"}


def test_image_route_rejects_removed_tool_id(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/images/generate",
        data={"toolId": "creator", "prompt": "a quiet studio", "size": "1024x1024"},
        files={"image": ("input.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "请选择有效的图片工具。"}


def test_image_route_returns_generated_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)

    def fake_request_image_from_openai(valid_request, api_key, model):
        assert valid_request.tool.id == "product"
        assert valid_request.prompt == "保留瓶身居中"
        assert valid_request.image_bytes == TINY_PNG
        assert api_key == "key"
        assert model == "gpt-image-2"
        return GeneratedImageEnvelope.from_images(
            [GeneratedImageResult(src="data:image/png;base64,abc123")]
        )

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "product", "prompt": "保留瓶身居中", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "image": {
            "src": "data:image/png;base64,abc123",
            "mimeType": "image/png",
            "revisedPrompt": None,
        },
        "images": [
            {
                "src": "data:image/png;base64,abc123",
                "mimeType": "image/png",
                "revisedPrompt": None,
            }
        ],
    }


def test_image_route_passes_openai_base_url_when_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.example.test/v1")
    captured_kwargs = {}

    def fake_request_image_from_openai(valid_request, **kwargs):
        captured_kwargs.update(kwargs)
        return GeneratedImageEnvelope.from_images(
            [GeneratedImageResult(src="data:image/png;base64,abc123")]
        )

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "product", "prompt": "淇濈暀鐡惰韩灞呬腑", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    assert captured_kwargs["api_key"] == "key"
    assert captured_kwargs["base_url"] == "https://api.example.test/v1"


def test_image_route_offloads_openai_request_to_threadpool(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    offload_calls = []

    def fake_request_image_from_openai(valid_request, api_key, model):
        return GeneratedImageEnvelope.from_images(
            [GeneratedImageResult(src="data:image/png;base64,abc123")]
        )

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
        data={"toolId": "product", "prompt": "保留瓶身居中", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    assert offload_calls
    assert offload_calls[0][0] is fake_request_image_from_openai
    assert offload_calls[0][1][0].tool.id == "product"
    assert offload_calls[0][2] == {"api_key": "key", "model": "gpt-image-2"}


def test_image_route_passes_uploaded_product_image_to_openai_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    captured_request = {}

    def fake_request_image_from_openai(valid_request, api_key, model):
        captured_request["valid_request"] = valid_request
        return GeneratedImageEnvelope.from_images(
            [GeneratedImageResult(src="data:image/png;base64,edited")]
        )

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={"toolId": "product", "prompt": "保留瓶身居中", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    valid_request = captured_request["valid_request"]
    assert valid_request.tool.id == "product"
    assert valid_request.image_bytes == TINY_PNG
    assert valid_request.image_name == "product.png"
    assert valid_request.image_type == "image/png"


def test_image_route_rejects_generation_without_uploaded_image(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")

    response = client.post(
        "/api/images/generate",
        data={
            "toolId": "product",
            "prompt": "平台：拼多多",
            "size": "2048x2048",
            "platformStyle": "pinduoduo",
            "imagePurpose": "main-image",
            "aspectRatio": "1:1",
            "imageCount": "2",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"error": "请上传商品图。"}


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
        data={"toolId": "product", "prompt": "保留瓶身居中", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 502
    assert response.json() == {"error": "图片生成失败，请稍后重试。"}
def test_image_route_passes_product_fields_to_openai_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    captured_request = {}

    def fake_request_image_from_openai(valid_request, api_key, model):
        captured_request["valid_request"] = valid_request
        return GeneratedImageEnvelope.from_images(
            [GeneratedImageResult(src="data:image/png;base64,product")]
        )

    monkeypatch.setattr(
        "app.main.request_image_from_openai",
        fake_request_image_from_openai,
    )

    response = client.post(
        "/api/images/generate",
        data={
            "toolId": "product",
            "prompt": "保留瓶身居中",
            "size": "1536x1024",
            "platformStyle": "pinduoduo",
            "imagePurpose": "promotion-image",
            "productCategory": "小家电",
            "sellingPoints": "三档风力，静音，USB 充电",
            "sceneStyle": "夏季桌面",
            "visualTone": "高转化促销",
            "promotionText": "限时立减 20 元",
            "preserveRequirements": "保留品牌 logo",
            "avoidElements": "不要额外配件",
            "aspectRatio": "2:3",
            "imageCount": "4",
        },
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    valid_request = captured_request["valid_request"]
    assert valid_request.tool.id == "product"
    assert valid_request.product_fields.platform_style == "pinduoduo"
    assert valid_request.product_fields.image_purpose == "promotion-image"
    assert valid_request.product_fields.product_category == "小家电"
    assert valid_request.generation_settings.aspect_ratio == "2:3"
    assert valid_request.generation_settings.image_count == 4
