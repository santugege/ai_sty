from datetime import datetime, timezone
from uuid import uuid4

from app.agent_tools import AgentToolContext, AgentToolRegistry, GptImage2EditTool
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


def test_agent_envelope_accepts_camel_case_fields_and_dumps_json_safe_values():
    session_id = uuid4()
    image_version_id = uuid4()
    message_id = uuid4()
    created_at = datetime(2026, 5, 8, 10, 30, tzinfo=timezone.utc)
    updated_at = datetime(2026, 5, 8, 10, 31, tzinfo=timezone.utc)

    envelope = AgentEnvelope(
        session={
            "id": session_id,
            "title": "Product edit",
            "currentVersionId": image_version_id,
            "previousResponseId": "resp_previous",
            "status": "ready",
            "createdAt": created_at,
            "updatedAt": updated_at,
        },
        messages=[
            {
                "id": message_id,
                "sessionId": session_id,
                "role": "user",
                "content": "Make it brighter",
                "responseId": None,
                "toolCallId": None,
                "createdAt": created_at,
            }
        ],
        currentImage={
            "id": image_version_id,
            "sessionId": session_id,
            "parentVersionId": None,
            "src": "data:image/png;base64,abc",
            "storageKey": "sessions/image.png",
            "mimeType": "image/png",
            "width": 1024,
            "height": 1024,
            "prompt": "Make it brighter",
            "revisedPrompt": None,
            "model": "gpt-image-2",
            "createdAt": created_at,
        },
        versions=[],
    )

    dumped = envelope.model_dump(mode="json")

    assert dumped["session"]["id"] == str(session_id)
    assert dumped["session"]["currentVersionId"] == str(image_version_id)
    assert dumped["session"]["createdAt"] == "2026-05-08T10:30:00Z"
    assert dumped["messages"][0]["id"] == str(message_id)
    assert dumped["currentImage"]["createdAt"] == "2026-05-08T10:30:00Z"
