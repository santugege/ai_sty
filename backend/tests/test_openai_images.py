from types import SimpleNamespace

import pytest

from app.image_request import (
    ProductGenerationSettings,
    ProductImageFields,
    ValidImageRequest,
)
from app.openai_images import (
    normalize_openai_image_response,
    request_image_from_openai,
)
from app.tools import get_tool_by_id


def test_normalizes_base64_image_data():
    result = normalize_openai_image_response(
        {"data": [{"b64_json": "abc123", "revised_prompt": "a refined prompt"}]}
    )

    assert result.src == "data:image/png;base64,abc123"
    assert result.mime_type == "image/png"
    assert result.revised_prompt == "a refined prompt"


def test_normalizes_hosted_image_url():
    result = normalize_openai_image_response(
        SimpleNamespace(data=[SimpleNamespace(url="https://example.test/image.png")])
    )

    assert result.src == "https://example.test/image.png"
    assert result.mime_type == "image/png"
    assert result.revised_prompt is None


def test_raises_stable_error_when_no_image_is_returned():
    with pytest.raises(RuntimeError, match="OpenAI 没有返回图片结果。"):
        normalize_openai_image_response({"data": []})


def test_requests_product_image_generation_without_uploaded_image():
    class FakeImages:
        def __init__(self):
            self.generate_kwargs = None
            self.edit_kwargs = None

        def generate(self, **kwargs):
            self.generate_kwargs = kwargs
            return {"data": [{"b64_json": "abc123"}]}

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "should-not-happen"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("product"),
            prompt="商品场景",
            size="2048x2048",
            generation_settings=ProductGenerationSettings(
                aspect_ratio="1:1",
                image_count=1,
            ),
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.images[0].src == "data:image/png;base64,abc123"
    assert fake_client.images.generate_kwargs["model"] == "gpt-image-2"
    assert fake_client.images.generate_kwargs["size"] == "2048x2048"
    assert fake_client.images.generate_kwargs["quality"] == "auto"
    assert "商品场景" in fake_client.images.generate_kwargs["prompt"]
    assert fake_client.images.edit_kwargs is None


def test_request_image_from_openai_passes_base_url_to_client_factory():
    class FakeImages:
        def generate(self, **kwargs):
            return {"data": [{"b64_json": "abc123"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    calls = []

    def fake_client_factory(**kwargs):
        calls.append(kwargs)
        return FakeClient()

    request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("product"),
            prompt="product scene",
            size="1024x1024",
        ),
        api_key="key",
        model="gpt-image-2",
        base_url="https://api.example.test/v1",
        client_factory=fake_client_factory,
    )

    assert calls == [
        {"api_key": "key", "base_url": "https://api.example.test/v1"}
    ]


def test_requests_product_image_edit_when_uploaded_image_is_present():
    class FakeImages:
        def __init__(self):
            self.generate_kwargs = None
            self.edit_kwargs = None

        def generate(self, **kwargs):
            self.generate_kwargs = kwargs
            return {"data": [{"b64_json": "should-not-happen"}]}

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "edited"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("product"),
            prompt="保留瓶身居中",
            size="1536x1024",
            image_bytes=b"image-bytes",
            image_name="product.png",
            image_type="image/png",
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.images[0].src == "data:image/png;base64,edited"
    assert fake_client.images.edit_kwargs["model"] == "gpt-image-2"
    assert fake_client.images.edit_kwargs["image"].name == "product.png"
    assert "保留瓶身居中" in fake_client.images.edit_kwargs["prompt"]
    assert fake_client.images.edit_kwargs["size"] == "1536x1024"
    assert fake_client.images.generate_kwargs is None


def test_requests_image_edit_with_structured_product_prompt():
    class FakeImages:
        def __init__(self):
            self.edit_kwargs = None

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "product"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("product"),
            prompt="保留瓶身居中",
            size="1536x1024",
            image_bytes=b"image-bytes",
            image_name="product.png",
            image_type="image/png",
            product_fields=ProductImageFields(
                platform_style="pinduoduo",
                image_purpose="promotion-image",
                product_category="小家电",
                selling_points="三档风力",
            ),
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.images[0].src == "data:image/png;base64,product"
    assert "Platform style (拼多多):" in fake_client.images.edit_kwargs["prompt"]
    assert "Product category: 小家电" in fake_client.images.edit_kwargs["prompt"]


def test_requests_multiple_images_by_repeating_single_image_generation():
    class FakeImages:
        def __init__(self):
            self.generate_kwargs = []
            self.edit_kwargs = None

        def generate(self, **kwargs):
            self.generate_kwargs.append(kwargs)
            return {"data": [{"b64_json": f"image-{len(self.generate_kwargs)}"}]}

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "should-not-happen"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("product"),
            prompt="生成四张主图方向",
            size="1024x1024",
            generation_settings=ProductGenerationSettings(
                aspect_ratio="1:1",
                image_count=4,
            ),
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert [image.src for image in result.images] == [
        "data:image/png;base64,image-1",
        "data:image/png;base64,image-2",
        "data:image/png;base64,image-3",
        "data:image/png;base64,image-4",
    ]
    assert len(fake_client.images.generate_kwargs) == 4
    assert fake_client.images.edit_kwargs is None
