from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.agent_tools import (
    AgentToolContext,
    AgentToolRegistry,
    ChatGptImageEditTool,
    ChatGptImageGenerateTool,
    create_openai_image_client,
)
from app.agent_schemas import AgentEnvelope


class FakeImageClient:
    def generate(self, instruction: str, size: str, quality: str) -> bytes:
        return b"generated"

    def edit(self, context: AgentToolContext) -> bytes:
        return b"edited"


def test_agent_tool_registry_returns_tool_by_name():
    registry = AgentToolRegistry(
        [ChatGptImageEditTool(image_client=FakeImageClient())]
    )

    tool = registry.get("chatgpt_image_edit")

    assert tool is not None
    assert tool.name == "chatgpt_image_edit"


def test_agent_tool_registry_returns_none_for_missing_tool():
    registry = AgentToolRegistry(
        [ChatGptImageEditTool(image_client=FakeImageClient())]
    )

    assert registry.get("missing") is None


def test_chatgpt_image_edit_tool_uses_gpt_image_2_model(monkeypatch):
    monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
    calls = []

    class FakeTrackingImageClient:
        def edit(self, context: AgentToolContext) -> bytes:
            calls.append(context)
            return b"edited"

    context = AgentToolContext(
        image_bytes=b"original",
        image_name="product.png",
        mime_type="image/png",
        instruction="add a clean white background",
        size="1024x1024",
    )
    tool = ChatGptImageEditTool(image_client=FakeTrackingImageClient())

    result = tool.execute(context)

    assert calls == [context]
    assert calls[0].instruction == "add a clean white background"
    assert result.image_bytes == b"edited"
    assert result.model == "gpt-image-2"


def test_chatgpt_image_edit_tool_uses_openai_image_model_env(monkeypatch):
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "custom-image-model")
    context = AgentToolContext(
        image_bytes=b"original",
        image_name="product.png",
        mime_type="image/png",
        instruction="add a clean white background",
        size="1024x1024",
    )
    tool = ChatGptImageEditTool(image_client=FakeImageClient())

    result = tool.execute(context)

    assert result.model == "custom-image-model"


def test_chatgpt_image_generate_tool_uses_openai_image_model_env(monkeypatch):
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "custom-image-model")
    context = AgentToolContext(
        image_bytes=b"",
        image_name="generated-image.png",
        mime_type="image/png",
        instruction="Create a quiet mountain lake.",
        size="1024x1024",
    )
    tool = ChatGptImageGenerateTool(image_client=FakeImageClient())

    result = tool.execute(context)

    assert result.image_bytes == b"generated"
    assert result.model == "custom-image-model"


def test_chatgpt_image_generate_tool_passes_selected_quality():
    calls = []

    class FakeTrackingImageClient:
        def generate(self, instruction: str, size: str, quality: str) -> bytes:
            calls.append({"instruction": instruction, "size": size, "quality": quality})
            return b"generated"

    context = AgentToolContext(
        image_bytes=b"",
        image_name="generated-image.png",
        mime_type="image/png",
        instruction="Create a quiet mountain lake.",
        size="1024x1024",
        quality="medium",
    )
    tool = ChatGptImageGenerateTool(image_client=FakeTrackingImageClient())

    result = tool.execute(context)

    assert result.image_bytes == b"generated"
    assert calls == [
        {
            "instruction": "Create a quiet mountain lake.",
            "size": "1024x1024",
            "quality": "medium",
        }
    ]


def test_create_openai_image_client_passes_base_url_to_client_factory():
    calls = []

    class FakeImages:
        def edit(self, **kwargs):
            return {"data": [{"b64_json": "ZWRpdGVk"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    def fake_client_factory(**kwargs):
        calls.append(kwargs)
        return FakeClient()

    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        base_url="https://api.example.test/v1",
        client_factory=fake_client_factory,
    )

    image_client.edit(
        AgentToolContext(
            image_bytes=b"original",
            image_name="product.png",
            mime_type="image/png",
            instruction="Make it brighter",
            size="1024x1024",
        )
    )

    assert calls == [
        {"api_key": "key", "base_url": "https://api.example.test/v1"}
    ]


def test_agent_envelope_accepts_camel_case_fields_and_dumps_json_safe_values():
    attachment_id = "att_123"
    message_id = uuid4()
    created_at = datetime(2026, 5, 8, 10, 30, tzinfo=timezone.utc)
    updated_at = datetime(2026, 5, 8, 10, 31, tzinfo=timezone.utc)

    envelope = AgentEnvelope(
        conversation={
            "id": "default",
            "title": "ChatGPT 对话",
            "previousResponseId": "resp_previous",
            "status": "ready",
            "createdAt": created_at,
            "updatedAt": updated_at,
        },
        messages=[
            {
                "id": str(message_id),
                "role": "user",
                "content": "Make it brighter",
                "attachments": [
                    {
                        "id": attachment_id,
                        "name": "product.png",
                        "mimeType": "image/png",
                        "src": "data:image/png;base64,abc",
                        "createdAt": created_at,
                    }
                ],
                "imageVersionId": attachment_id,
                "createdAt": created_at,
            }
        ],
    )

    dumped = envelope.model_dump(mode="json")

    assert dumped["conversation"]["id"] == "default"
    assert dumped["conversation"]["createdAt"] == "2026-05-08T10:30:00Z"
    assert dumped["messages"][0]["id"] == str(message_id)
    assert dumped["messages"][0]["attachments"][0]["id"] == attachment_id
    assert dumped["messages"][0]["imageVersionId"] == attachment_id
    assert "currentImage" not in dumped


def test_create_openai_image_client_edits_image_with_gpt_image_2():
    class FakeImages:
        def __init__(self):
            self.edit_kwargs = None

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "ZWRpdGVk"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    result = image_client.edit(
        AgentToolContext(
            image_bytes=b"original",
            image_name="product.png",
            mime_type="image/png",
            instruction="Make it brighter",
            size="1536x1024",
        )
    )

    assert result == b"edited"
    assert fake_client.images.edit_kwargs["model"] == "gpt-image-2"
    assert fake_client.images.edit_kwargs["prompt"] == "Make it brighter"
    assert fake_client.images.edit_kwargs["size"] == "1536x1024"
    assert fake_client.images.edit_kwargs["quality"] == "auto"
    assert fake_client.images.edit_kwargs["image"].name == "product.png"


def test_create_openai_image_client_generates_image_with_selected_quality():
    class FakeImages:
        def __init__(self):
            self.generate_kwargs = None

        def generate(self, **kwargs):
            self.generate_kwargs = kwargs
            return {"data": [{"b64_json": "Z2VuZXJhdGVk"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    result = image_client.generate("Create a mountain lake.", "1536x1024", "medium")

    assert result == b"generated"
    assert fake_client.images.generate_kwargs["model"] == "gpt-image-2"
    assert fake_client.images.generate_kwargs["prompt"] == "Create a mountain lake."
    assert fake_client.images.generate_kwargs["size"] == "1536x1024"
    assert fake_client.images.generate_kwargs["quality"] == "medium"


def test_create_openai_image_client_edits_image_with_selected_quality():
    class FakeImages:
        def __init__(self):
            self.edit_kwargs = None

        def edit(self, **kwargs):
            self.edit_kwargs = kwargs
            return {"data": [{"b64_json": "ZWRpdGVk"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: fake_client,
    )

    result = image_client.edit(
        AgentToolContext(
            image_bytes=b"original",
            image_name="current.png",
            mime_type="image/png",
            instruction="Make the sky warmer.",
            size="1536x1024",
            quality="low",
        )
    )

    assert result == b"edited"
    assert fake_client.images.edit_kwargs["quality"] == "low"
    assert fake_client.images.edit_kwargs["prompt"] == "Make the sky warmer."


def test_create_openai_image_client_raises_for_missing_base64_image_response():
    class FakeImages:
        def edit(self, **kwargs):
            return {"data": [{"b64_json": ""}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: FakeClient(),
    )

    with pytest.raises(RuntimeError, match="OpenAI did not return image data."):
        image_client.edit(
            AgentToolContext(
                image_bytes=b"original",
                image_name="product.png",
                mime_type="image/png",
                instruction="Make it brighter",
                size="1536x1024",
            )
        )


def test_create_openai_image_client_raises_for_invalid_base64_image_response():
    class FakeImages:
        def edit(self, **kwargs):
            return {"data": [{"b64_json": "not base64"}]}

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    image_client = create_openai_image_client(
        api_key="key",
        image_model="gpt-image-2",
        client_factory=lambda api_key: FakeClient(),
    )

    with pytest.raises(RuntimeError, match="OpenAI returned invalid base64 image data."):
        image_client.edit(
            AgentToolContext(
                image_bytes=b"original",
                image_name="product.png",
                mime_type="image/png",
                instruction="Make it brighter",
                size="1536x1024",
            )
        )
