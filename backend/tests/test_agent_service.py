import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent_repository import AgentRepository
from app.agent_service import (
    AgentServiceError,
    ChatGptConversationService,
    ConversationInputError,
    ConversationTurnDecision,
)
from app.agent_tools import AgentToolContext, AgentToolResult
from app.db import Base
from app.image_storage import StoredImage


def test_agent_service_has_no_legacy_in_memory_conversation_flow():
    source = Path("backend/app/agent_service.py").read_text(encoding="utf-8")

    forbidden_markers = [
        "class StoredAttachment",
        "class StoredMessage",
        "class ConversationState",
        "def send_message(",
        "def _send_in_memory_message(",
        "def reset(",
        "def _envelope(",
        "currentImage=",
    ]
    for marker in forbidden_markers:
        assert marker not in source


class FakeTool:
    name = "chatgpt_image_edit"
    description = "fake"

    def __init__(self):
        self.calls = []

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        self.calls.append(context)
        return AgentToolResult(
            image_bytes=b"edited-image",
            mime_type="image/png",
            prompt=context.instruction,
            revised_prompt="edited prompt",
            model="gpt-image-2",
        )


class FakeImageStorage:
    def __init__(self):
        self.objects = {}
        self.writes = []

    def write_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prefix: str = "agent-sessions",
    ) -> StoredImage:
        storage_key = f"{prefix}/image-{len(self.objects) + 1}.png"
        self.objects[storage_key] = bytes(image_bytes)
        self.writes.append(
            {
                "storage_key": storage_key,
                "image_bytes": bytes(image_bytes),
                "mime_type": mime_type,
                "prefix": prefix,
            }
        )
        return StoredImage(storage_key=storage_key, mime_type=mime_type)

    def read_image(self, storage_key: str) -> bytes:
        return self.objects[storage_key]

    def delete_image(self, storage_key: str) -> None:
        self.objects.pop(storage_key, None)


class FailingTool:
    name = "chatgpt_image_edit"
    description = "failing"

    def execute(self, context: AgentToolContext) -> AgentToolResult:
        raise RuntimeError("tool failed")


class FailingWriteStorage(FakeImageStorage):
    def write_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prefix: str = "agent-sessions",
    ) -> StoredImage:
        raise RuntimeError("storage write failed")


class FailingReadStorage(FakeImageStorage):
    def __init__(self):
        super().__init__()
        self.fail_reads = False

    def read_image(self, storage_key: str) -> bytes:
        if not self.fail_reads:
            return super().read_image(storage_key)
        raise RuntimeError("storage read failed")


def make_repo() -> AgentRepository:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return AgentRepository(Session(engine))


def make_persistent_service(
    decisions: ConversationTurnDecision | list[ConversationTurnDecision],
    tool=None,
    repo: AgentRepository | None = None,
    storage: FakeImageStorage | None = None,
    summarizer=None,
):
    planner_calls = []
    decision_list = (
        decisions if isinstance(decisions, list) else [decisions]
    )

    def fake_planner(**kwargs):
        planner_calls.append(kwargs)
        index = min(len(planner_calls) - 1, len(decision_list) - 1)
        return decision_list[index]

    image_tool = tool or FakeTool()
    image_storage = storage or FakeImageStorage()
    service = ChatGptConversationService(
        planner=fake_planner,
        tools={
            "chatgpt_image_generate": image_tool,
            "chatgpt_image_edit": image_tool,
        },
        repo=repo or make_repo(),
        storage=image_storage,
        summarizer=summarizer,
    )
    return service, planner_calls, image_tool, image_storage


def test_create_session_persists_conversation_and_uploaded_image():
    service, _planner_calls, _tool, storage = make_persistent_service(
        ConversationTurnDecision(
            action="answer",
            assistant_message="I can edit this image.",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_1",
        )
    )

    envelope = service.create_session(
        message="Make this image cleaner.",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    session_id = uuid.UUID(envelope.conversation.id)
    state = service.repo.get_session_state(session_id)
    assert state is not None
    assert [message.role for message in state.messages] == ["user", "assistant"]
    assert state.messages[0].content == "Make this image cleaner."
    assert state.messages[1].content == "I can edit this image."
    assert len(storage.objects) == 1
    assert state.session.current_version_id == state.versions[0].id
    assert envelope.messages[0].imageVersionId == str(state.versions[0].id)


def test_create_session_rejects_blank_input_without_persisting_session():
    repo = make_repo()
    service, _planner_calls, _tool, _storage = make_persistent_service(
        ConversationTurnDecision("answer", "No input.", None, None, "resp_1"),
        repo=repo,
    )

    with pytest.raises(ConversationInputError, match="Please enter a message"):
        service.create_session("", [], "1536x1024")

    assert repo.list_sessions() == []


def test_failed_create_session_planner_turn_deletes_new_session():
    repo = make_repo()

    def failing_planner(**kwargs):
        raise RuntimeError("planner failed")

    service = ChatGptConversationService(
        planner=failing_planner,
        tools={"chatgpt_image_edit": FakeTool()},
        repo=repo,
        storage=FakeImageStorage(),
    )

    with pytest.raises(RuntimeError, match="planner failed"):
        service.create_session("Start", [], "1536x1024")

    assert repo.list_sessions() == []


def test_failed_create_session_tool_turn_deletes_new_session_and_uploads():
    repo = make_repo()
    storage = FakeImageStorage()
    service, _planner_calls, _tool, _storage = make_persistent_service(
        ConversationTurnDecision(
            "edit",
            "I will edit it.",
            "chatgpt_image_edit",
            "Edit it.",
            "resp_1",
        ),
        tool=FailingTool(),
        repo=repo,
        storage=storage,
    )

    with pytest.raises(RuntimeError, match="tool failed"):
        service.create_session(
            "Use this image.",
            [
                {
                    "image_bytes": b"input-image",
                    "image_name": "product.png",
                    "mime_type": "image/png",
                }
            ],
            "1536x1024",
        )

    assert repo.list_sessions() == []
    assert storage.objects == {}


def test_failed_create_session_storage_turn_deletes_new_session():
    repo = make_repo()
    service, _planner_calls, _tool, _storage = make_persistent_service(
        ConversationTurnDecision("answer", "Stored.", None, None, "resp_1"),
        repo=repo,
        storage=FailingWriteStorage(),
    )

    with pytest.raises(RuntimeError, match="storage write failed"):
        service.create_session(
            "Use this image.",
            [
                {
                    "image_bytes": b"input-image",
                    "image_name": "product.png",
                    "mime_type": "image/png",
                }
            ],
            "1536x1024",
        )

    assert repo.list_sessions() == []


def test_persistent_user_uploads_are_returned_as_attachments_not_generated_images():
    service, _planner_calls, _tool, _storage = make_persistent_service(
        ConversationTurnDecision("answer", "I can edit this image.", None, None, "resp_1")
    )

    envelope = service.create_session(
        message="Use this upload.",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    user_message = envelope.messages[0]
    assert user_message.image is None
    assert len(user_message.attachments) == 1
    assert user_message.attachments[0].name == "Uploaded image"
    assert user_message.attachments[0].src.startswith("data:image/png;base64,")
    assert envelope.messages[1].image is None


def test_persistent_create_session_returns_and_reloads_all_user_upload_attachments():
    service, _planner_calls, _tool, storage = make_persistent_service(
        ConversationTurnDecision("answer", "I can edit these.", None, None, "resp_1")
    )

    created = service.create_session(
        message="Use both uploads.",
        attachments=[
            {
                "image_bytes": b"first-image",
                "image_name": "first.png",
                "mime_type": "image/png",
            },
            {
                "image_bytes": b"second-image",
                "image_name": "second.png",
                "mime_type": "image/png",
            },
        ],
        size="1536x1024",
    )
    reloaded = service.get_session(created.conversation.id)

    for envelope in (created, reloaded):
        user_message = envelope.messages[0]
        assert user_message.image is None
        assert len(user_message.attachments) == 2
        assert user_message.attachments[0].src.endswith("Zmlyc3QtaW1hZ2U=")
        assert user_message.attachments[1].src.endswith("c2Vjb25kLWltYWdl")
        assert user_message.imageVersionId == user_message.attachments[1].id

    assert len(storage.objects) == 2
    state = service.repo.get_session_state(uuid.UUID(created.conversation.id))
    assert state is not None
    assert state.session.current_version_id == state.versions[-1].id


def test_sessions_keep_separate_previous_response_ids():
    repo = make_repo()
    storage = FakeImageStorage()
    service, _planner_calls, _tool, _storage = make_persistent_service(
        [
            ConversationTurnDecision("answer", "First done.", None, None, "resp_1"),
            ConversationTurnDecision("answer", "Second done.", None, None, "resp_2"),
        ],
        repo=repo,
        storage=storage,
    )

    first = service.create_session("First session", [], "1536x1024")
    second = service.create_session("Second session", [], "1536x1024")

    first_state = repo.get_session_state(uuid.UUID(first.conversation.id))
    second_state = repo.get_session_state(uuid.UUID(second.conversation.id))
    assert first_state is not None
    assert second_state is not None
    assert first_state.session.previous_response_id == "resp_1"
    assert second_state.session.previous_response_id == "resp_2"


def test_send_message_uses_target_session_summary_and_recent_messages():
    service, planner_calls, _tool, _storage = make_persistent_service(
        [
            ConversationTurnDecision("answer", "First answer.", None, None, "resp_1"),
            ConversationTurnDecision("answer", "Follow-up answer.", None, None, "resp_2"),
        ]
    )
    envelope = service.create_session("Start a session", [], "1536x1024")
    session_id = uuid.UUID(envelope.conversation.id)
    service.repo.update_session_summary(session_id, "Existing summary")

    service.send_session_message(
        session_id=session_id,
        message="Use the previous direction.",
        attachments=[],
        size="1536x1024",
    )

    follow_up_call = planner_calls[1]
    assert follow_up_call["summary"] == "Existing summary"
    assert follow_up_call["previous_response_id"] == "resp_1"
    assert [message["content"] for message in follow_up_call["recent_messages"]] == [
        "Start a session",
        "First answer.",
        "Use the previous direction.",
    ]


def test_persistent_send_message_returns_and_reloads_all_user_upload_attachments():
    service, _planner_calls, _tool, _storage = make_persistent_service(
        [
            ConversationTurnDecision("answer", "Ready.", None, None, "resp_1"),
            ConversationTurnDecision("answer", "I see both uploads.", None, None, "resp_2"),
        ]
    )
    envelope = service.create_session("Start a session", [], "1536x1024")

    updated = service.send_session_message(
        session_id=envelope.conversation.id,
        message="Use these two images.",
        attachments=[
            {
                "image_bytes": b"followup-first",
                "image_name": "first.png",
                "mime_type": "image/png",
            },
            {
                "image_bytes": b"followup-second",
                "image_name": "second.png",
                "mime_type": "image/png",
            },
        ],
        size="1536x1024",
    )
    reloaded = service.get_session(envelope.conversation.id)

    for envelope in (updated, reloaded):
        user_message = envelope.messages[-2]
        assert user_message.role == "user"
        assert user_message.image is None
        assert len(user_message.attachments) == 2
        assert user_message.attachments[0].src.endswith("Zm9sbG93dXAtZmlyc3Q=")
        assert user_message.attachments[1].src.endswith("Zm9sbG93dXAtc2Vjb25k")
        assert user_message.imageVersionId == user_message.attachments[1].id
    state = service.repo.get_session_state(uuid.UUID(updated.conversation.id))
    assert state is not None
    assert state.session.current_version_id == state.versions[-1].id


def test_persistent_edit_turn_uses_stored_current_image_and_persists_generated_version():
    service, _planner_calls, tool, storage = make_persistent_service(
        [
            ConversationTurnDecision("answer", "I can edit it.", None, None, "resp_1"),
            ConversationTurnDecision(
                action="edit",
                assistant_message="Edited against the current image.",
                tool_name="chatgpt_image_edit",
                tool_instruction="Make the background white.",
                response_id="resp_2",
            ),
        ]
    )
    envelope = service.create_session(
        "Use this product photo",
        [
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        "1536x1024",
    )

    edited = service.send_session_message(
        session_id=envelope.conversation.id,
        message="Make it white.",
        attachments=[],
        size="1536x1024",
    )

    state = service.repo.get_session_state(uuid.UUID(envelope.conversation.id))
    assert state is not None
    assert tool.calls[-1].image_bytes == b"input-image"
    assert len(state.versions) == 2
    assert state.session.current_version_id == state.versions[-1].id
    assert state.versions[-1].parent_version_id == state.versions[0].id
    assert state.messages[-1].role == "assistant"
    assert state.messages[-1].image_version_id == state.versions[-1].id
    assert storage.read_image(state.versions[-1].storage_key) == b"edited-image"
    assistant_message = edited.messages[-1]
    assert assistant_message.imageVersionId == str(state.versions[-1].id)
    assert assistant_message.attachments == []
    assert assistant_message.image is not None
    assert assistant_message.image.model == "gpt-image-2"
    assert assistant_message.image.prompt == "Make the background white."
    assert assistant_message.image.src.endswith("ZWRpdGVkLWltYWdl")


def test_failed_persistent_edit_without_current_image_rolls_back_user_message():
    repo = make_repo()
    session = repo.create_session("No image")
    service, _planner_calls, _tool, storage = make_persistent_service(
        ConversationTurnDecision(
            "edit",
            "I need an image.",
            "chatgpt_image_edit",
            "Edit it.",
            "resp_1",
        ),
        repo=repo,
    )

    with pytest.raises(ConversationInputError, match="Please upload an image first."):
        service.send_session_message(session.id, "Make it brighter.", [], "1536x1024")

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.messages == []
    assert state.versions == []
    assert state.session.current_version_id is None
    assert storage.objects == {}


def test_persistent_generate_turn_does_not_require_current_image():
    service, _planner_calls, tool, storage = make_persistent_service(
        ConversationTurnDecision(
            action="generate",
            assistant_message="I created it.",
            tool_name="chatgpt_image_generate",
            tool_instruction="Create a mountain lake.",
            response_id="resp_generate",
        )
    )

    envelope = service.create_session(
        message="Generate a mountain lake.",
        attachments=[],
        size="1536x1024",
    )

    state = service.repo.get_session_state(uuid.UUID(envelope.conversation.id))
    assert state is not None
    assert tool.calls[-1].image_bytes == b""
    assert tool.calls[-1].instruction == "Create a mountain lake."
    assert len(state.versions) == 1
    assert state.session.current_version_id == state.versions[-1].id
    assert state.messages[-1].role == "assistant"
    assert state.messages[-1].image_version_id == state.versions[-1].id
    assert storage.read_image(state.versions[-1].storage_key) == b"edited-image"
    assistant_message = envelope.messages[-1]
    assert assistant_message.image is not None
    assert assistant_message.image.prompt == "Create a mountain lake."


def test_failed_persistent_edit_with_unavailable_tool_rolls_back_upload_side_effects():
    repo = make_repo()
    session = repo.create_session("Bad tool")
    storage = FakeImageStorage()
    service, _planner_calls, _tool, _storage = make_persistent_service(
        ConversationTurnDecision(
            "edit",
            "I will edit it.",
            "missing_tool",
            "Edit it.",
            "resp_1",
        ),
        repo=repo,
        storage=storage,
    )

    with pytest.raises(AgentServiceError, match="selected agent tool is not available"):
        service.send_session_message(
            session.id,
            "Use this product photo.",
            [
                {
                    "image_bytes": b"input-image",
                    "image_name": "product.png",
                    "mime_type": "image/png",
                }
            ],
            "1536x1024",
        )

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.messages == []
    assert state.versions == []
    assert state.session.current_version_id is None
    assert storage.objects == {}


def test_failed_persistent_turn_after_session_updates_restores_original_session_state():
    repo = make_repo()
    storage = FailingReadStorage()
    original_summary_updated_at = None
    service, _planner_calls, _tool, _storage = make_persistent_service(
        [
            ConversationTurnDecision("answer", "I can edit it.", None, None, "resp_1"),
            ConversationTurnDecision("answer", "Assistant 2.", None, None, "resp_2"),
            ConversationTurnDecision("answer", "Assistant 3.", None, None, "resp_3"),
        ],
        repo=repo,
        storage=storage,
        summarizer=lambda **kwargs: "Transient summary",
    )
    original = service.create_session(
        "Use this product photo",
        [
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        "1536x1024",
    )
    session_id = uuid.UUID(original.conversation.id)
    repo.update_session_summary(session_id, "Original summary")
    original_state = repo.get_session_state(session_id)
    assert original_state is not None
    original_summary_updated_at = original_state.session.summary_updated_at
    original_current_version_id = original_state.session.current_version_id
    original_message_ids = [message.id for message in original_state.messages]

    service.send_session_message(session_id, "User 2", [], "1536x1024")
    storage.fail_reads = True

    with pytest.raises(RuntimeError, match="storage read failed"):
        service.send_session_message(session_id, "User 3", [], "1536x1024")

    state = repo.get_session_state(session_id)
    assert state is not None
    assert [message.id for message in state.messages] == original_message_ids + [
        state.messages[-2].id,
        state.messages[-1].id,
    ]
    assert [message.content for message in state.messages] == [
        "Use this product photo",
        "I can edit it.",
        "User 2",
        "Assistant 2.",
    ]
    assert state.session.current_version_id == original_current_version_id
    assert state.session.previous_response_id == "resp_2"
    assert state.session.summary == "Original summary"
    assert state.session.summary_updated_at == original_summary_updated_at


def test_summary_refresh_persists_summarizer_result_with_recent_messages():
    summarizer_calls = []

    def fake_summarizer(**kwargs):
        summarizer_calls.append(kwargs)
        return "Session summary"

    service, _planner_calls, _tool, _storage = make_persistent_service(
        [
            ConversationTurnDecision("answer", "Assistant 1.", None, None, "resp_1"),
            ConversationTurnDecision("answer", "Assistant 2.", None, None, "resp_2"),
            ConversationTurnDecision("answer", "Assistant 3.", None, None, "resp_3"),
        ],
        summarizer=fake_summarizer,
    )
    envelope = service.create_session("User 1", [], "1536x1024")
    session_id = uuid.UUID(envelope.conversation.id)

    service.send_session_message(session_id, "User 2", [], "1536x1024")
    service.send_session_message(session_id, "User 3", [], "1536x1024")

    state = service.repo.get_session_state(session_id)
    assert state is not None
    assert state.session.summary == "Session summary"
    assert summarizer_calls
    assert summarizer_calls[-1]["previous_summary"] is None
    assert [message["content"] for message in summarizer_calls[-1]["recent_messages"]] == [
        "User 1",
        "Assistant 1.",
        "User 2",
        "Assistant 2.",
        "User 3",
        "Assistant 3.",
    ]
