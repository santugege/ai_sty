import uuid

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


class FakeTool:
    name = "gpt_image_2_edit"
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


def make_service(decision: ConversationTurnDecision, tool=None):
    planner_calls = []

    def fake_planner(**kwargs):
        planner_calls.append(kwargs)
        return decision

    image_tool = tool or FakeTool()
    service = ChatGptConversationService(
        planner=fake_planner,
        tools={"gpt_image_2_edit": image_tool},
    )
    return service, planner_calls, image_tool


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
        tools={"gpt_image_2_edit": image_tool},
        repo=repo or make_repo(),
        storage=image_storage,
        summarizer=summarizer,
    )
    return service, planner_calls, image_tool, image_storage


def test_first_turn_stores_messages_and_uploaded_image_in_memory():
    service, planner_calls, tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="已按你的要求调整图片。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Make the background cleaner.",
            response_id="resp_1",
        )
    )

    envelope = service.send_message(
        message="背景更干净一些",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    assert envelope.conversation.id == "default"
    assert envelope.conversation.previousResponseId == "resp_1"
    assert [message.role for message in envelope.messages] == ["user", "assistant"]
    assert envelope.messages[0].attachments[0].src.startswith("data:image/png;base64,")
    assert envelope.currentImage.src.startswith("data:image/png;base64,")
    assert envelope.currentImage.prompt == "Make the background cleaner."
    assert tool.calls[0].image_bytes == b"input-image"
    assert planner_calls[0]["recent_messages"][0]["role"] == "user"


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
    assert envelope.currentImage is not None
    assert envelope.currentImage.model == "user-upload"
    assert envelope.messages[0].imageVersionId == str(state.versions[0].id)


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


def test_persistent_edit_turn_uses_stored_current_image_and_persists_generated_version():
    service, _planner_calls, tool, storage = make_persistent_service(
        [
            ConversationTurnDecision("answer", "I can edit it.", None, None, "resp_1"),
            ConversationTurnDecision(
                action="edit",
                assistant_message="Edited against the current image.",
                tool_name="gpt_image_2_edit",
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
    assert edited.currentImage is not None
    assert edited.currentImage.src.endswith("ZWRpdGVkLWltYWdl")
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
            "gpt_image_2_edit",
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


def test_follow_up_without_new_upload_uses_current_image_context():
    service, _planner_calls, tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="已生成第一版。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Create a clean ecommerce scene.",
            response_id="resp_1",
        )
    )
    service.send_message(
        message="先做成电商主图",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    service.planner = lambda **kwargs: ConversationTurnDecision(
        action="edit",
        assistant_message="已继续在当前图上调整。",
        tool_name="gpt_image_2_edit",
        tool_instruction="Make it warmer.",
        response_id="resp_2",
    )
    envelope = service.send_message(
        message="再暖一点",
        attachments=[],
        size="1536x1024",
    )

    assert len(envelope.messages) == 4
    assert envelope.messages[-2].content == "再暖一点"
    assert envelope.messages[-1].content == "已继续在当前图上调整。"
    assert tool.calls[-1].image_bytes == b"edited-image"
    assert envelope.conversation.previousResponseId == "resp_2"


def test_text_only_clarification_does_not_require_image_after_context_exists():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="已生成第一版。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Create a clean ecommerce scene.",
            response_id="resp_1",
        )
    )
    service.send_message(
        message="先做成电商主图",
        attachments=[
            {
                "image_bytes": b"input-image",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    service.planner = lambda **kwargs: ConversationTurnDecision(
        action="answer",
        assistant_message="可以，我会沿用当前图片方向。",
        tool_name=None,
        tool_instruction=None,
        response_id="resp_2",
    )
    envelope = service.send_message("明白了吗？", [], "1536x1024")

    assert envelope.messages[-1].role == "assistant"
    assert envelope.messages[-1].content == "可以，我会沿用当前图片方向。"
    assert envelope.currentImage is not None


def test_uploaded_image_remains_context_when_turn_only_answers():
    service, _planner_calls, tool = make_service(
        ConversationTurnDecision(
            action="answer",
            assistant_message="我看到了这张商品图。",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_1",
        )
    )
    first = service.send_message(
        message="先看看这张图",
        attachments=[
            {
                "image_bytes": b"uploaded-context",
                "image_name": "product.png",
                "mime_type": "image/png",
            }
        ],
        size="1536x1024",
    )

    assert first.currentImage is not None
    assert first.currentImage.model == "user-upload"

    service.planner = lambda **kwargs: ConversationTurnDecision(
        action="edit",
        assistant_message="已基于刚才的图片编辑。",
        tool_name="gpt_image_2_edit",
        tool_instruction="Change the background to white.",
        response_id="resp_2",
    )
    service.send_message(
        message="换成白底",
        attachments=[],
        size="1536x1024",
    )

    assert tool.calls[-1].image_bytes == b"uploaded-context"


def test_first_turn_requires_message_or_image():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision("answer", "请上传图片或输入需求。", None, None, "resp")
    )

    with pytest.raises(ConversationInputError, match="请输入消息或上传图片。"):
        service.send_message("", [], "1536x1024")


def test_image_edit_requires_uploaded_or_current_image():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision(
            action="edit",
            assistant_message="我需要图片才能编辑。",
            tool_name="gpt_image_2_edit",
            tool_instruction="Edit it.",
            response_id="resp_1",
        )
    )

    with pytest.raises(ConversationInputError, match="请先上传一张图片。"):
        service.send_message("把背景换成白色", [], "1536x1024")


def test_reset_clears_the_single_in_memory_conversation():
    service, _planner_calls, _tool = make_service(
        ConversationTurnDecision(
            action="answer",
            assistant_message="好的。",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_1",
        )
    )
    service.send_message("你好", [], "1536x1024")

    envelope = service.reset()

    assert envelope.messages == []
    assert envelope.currentImage is None
    assert envelope.conversation.previousResponseId is None
