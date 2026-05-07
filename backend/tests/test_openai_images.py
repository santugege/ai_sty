from types import SimpleNamespace

import pytest

from app.image_request import ValidImageRequest
from app.openai_images import normalize_openai_image_response, request_image_from_openai
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


def test_requests_text_generation_without_uploaded_image():
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
            tool=get_tool_by_id("creator"),
            prompt="a quiet studio",
            size="1024x1024",
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.src == "data:image/png;base64,abc123"
    assert fake_client.images.generate_kwargs["model"] == "gpt-image-2"
    assert "a quiet studio" in fake_client.images.generate_kwargs["prompt"]
    assert fake_client.images.generate_kwargs["size"] == "1024x1024"
    assert fake_client.images.edit_kwargs is None


def test_requests_image_edit_when_uploaded_image_is_present():
    class FakeImages:
        def __init__(self):
            self.edit_kwargs = None

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "edited"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()

    result = request_image_from_openai(
        ValidImageRequest(
            tool=get_tool_by_id("restore"),
            prompt="修复划痕",
            size="1024x1024",
            image_bytes=b"image-bytes",
            image_name="photo.png",
            image_type="image/png",
        ),
        api_key="key",
        model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    assert result.src == "data:image/png;base64,edited"
    assert fake_client.images.edit_kwargs["model"] == "gpt-image-2"
    assert fake_client.images.edit_kwargs["image"].name == "photo.png"
    assert "修复划痕" in fake_client.images.edit_kwargs["prompt"]
