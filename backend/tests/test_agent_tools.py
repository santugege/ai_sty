from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.agent_tools import (
    AgentToolContext,
    AgentToolRegistry,
    GptImage2EditTool,
    create_openai_image_client,
)
from app.agent_schemas import AgentEnvelope


def test_agent_tool_registry_returns_tool_by_name():
    registry = AgentToolRegistry(
        [GptImage2EditTool(image_client=lambda context: None)]
    )

    tool = registry.get("gpt_image_2_edit")

    assert tool is not None
    assert tool.name == "gpt_image_2_edit"


def test_agent_tool_registry_returns_none_for_missing_tool():
    registry = AgentToolRegistry(
        [GptImage2EditTool(image_client=lambda context: None)]
    )

    assert registry.get("missing") is None


def test_gpt_image_2_edit_tool_uses_gpt_image_2_model(monkeypatch):
    monkeypatch.delenv("OPENAI_IMAGE_MODEL", raising=False)
    calls = []

    def fake_image_client(context: AgentToolContext) -> bytes:
        calls.append(context)
        return b"edited"

    context = AgentToolContext(
        image_bytes=b"original",
        image_name="product.png",
        mime_type="image/png",
        instruction="add a clean white background",
        size="1024x1024",
    )
    tool = GptImage2EditTool(image_client=fake_image_client)

    result = tool.execute(context)

    assert calls == [context]
    assert calls[0].instruction == "add a clean white background"
    assert result.image_bytes == b"edited"
    assert result.model == "gpt-image-2"


def test_gpt_image_2_edit_tool_uses_openai_image_model_env(monkeypatch):
    monkeypatch.setenv("OPENAI_IMAGE_MODEL", "custom-image-model")
    context = AgentToolContext(
        image_bytes=b"original",
        image_name="product.png",
        mime_type="image/png",
        instruction="add a clean white background",
        size="1024x1024",
    )
    tool = GptImage2EditTool(image_client=lambda context: b"edited")

    result = tool.execute(context)

    assert result.model == "custom-image-model"


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

    image_client(
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
    image_id = "img_123"
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
                "createdAt": created_at,
            }
        ],
        currentImage={
            "id": image_id,
            "src": "data:image/png;base64,abc",
            "mimeType": "image/png",
            "prompt": "Make it brighter",
            "revisedPrompt": None,
            "model": "gpt-image-2",
            "createdAt": created_at,
        },
    )

    dumped = envelope.model_dump(mode="json")

    assert dumped["conversation"]["id"] == "default"
    assert dumped["conversation"]["createdAt"] == "2026-05-08T10:30:00Z"
    assert dumped["messages"][0]["id"] == str(message_id)
    assert dumped["messages"][0]["attachments"][0]["id"] == attachment_id
    assert dumped["currentImage"]["createdAt"] == "2026-05-08T10:30:00Z"


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

    result = image_client(
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
        image_client(
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
        image_client(
            AgentToolContext(
                image_bytes=b"original",
                image_name="product.png",
                mime_type="image/png",
                instruction="Make it brighter",
                size="1536x1024",
            )
        )
