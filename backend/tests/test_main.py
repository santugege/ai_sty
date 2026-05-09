import base64

from fastapi.testclient import TestClient

from app.main import app
from app.openai_images import GeneratedImageResult


client = TestClient(app)
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4//8/AwAI/AL+p5qgoAAAAABJRU5ErkJggg=="
)


def test_health_route_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


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
        data={"toolId": "product", "prompt": "商品场景", "size": "1536x1024"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "请上传商品图。"}


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

    def fake_request_image_from_openai(valid_request, api_key, model):
        assert valid_request.tool.id == "product"
        assert valid_request.prompt == "保留瓶身居中"
        assert valid_request.image_bytes == TINY_PNG
        assert api_key == "key"
        assert model == "gpt-image-2"
        return GeneratedImageResult(src="data:image/png;base64,abc123")

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
        data={"toolId": "product", "prompt": "保留瓶身居中", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    valid_request = captured_request["valid_request"]
    assert valid_request.tool.id == "product"
    assert valid_request.image_bytes == TINY_PNG
    assert valid_request.image_name == "product.png"
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
        data={"toolId": "product", "prompt": "保留瓶身居中", "size": "1536x1024"},
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 502
    assert response.json() == {"error": "图片生成失败，请稍后重试。"}
def test_image_route_passes_product_fields_to_openai_request(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    captured_request = {}

    def fake_request_image_from_openai(valid_request, api_key, model):
        captured_request["valid_request"] = valid_request
        return GeneratedImageResult(src="data:image/png;base64,product")

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
        },
        files={"image": ("product.png", TINY_PNG, "image/png")},
    )

    assert response.status_code == 200
    valid_request = captured_request["valid_request"]
    assert valid_request.tool.id == "product"
    assert valid_request.product_fields.platform_style == "pinduoduo"
    assert valid_request.product_fields.image_purpose == "promotion-image"
    assert valid_request.product_fields.product_category == "小家电"
