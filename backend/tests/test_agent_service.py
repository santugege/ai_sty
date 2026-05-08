from uuid import uuid4

import pytest
from app.agent_models import AgentMessageRow, AgentSessionRow, ImageVersionRow
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.agent_openai import AgentTurnDecision
from app.agent_repository import AgentRepository
from app.agent_service import AgentInputError, AgentServiceError, ImageAgentService
from app.agent_tools import AgentToolContext, AgentToolResult
from app.db import Base
from app.image_storage import LocalImageStorage


def make_service(tmp_path, decision, tool=None):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    repo = AgentRepository(db)
    storage = LocalImageStorage(tmp_path)

    def fake_planner(**kwargs):
        return decision

    class FakeTool:
        name = "gpt_image_2_edit"
        description = "fake"

        def execute(self, context: AgentToolContext) -> AgentToolResult:
            return AgentToolResult(
                image_bytes=b"edited",
                mime_type="image/png",
                prompt=context.instruction,
                revised_prompt="edited prompt",
                model="gpt-image-2",
            )

    tools = {}
    if tool is not None:
        tools["gpt_image_2_edit"] = tool
    else:
        tools["gpt_image_2_edit"] = FakeTool()

    return ImageAgentService(repo, storage, fake_planner, tools), repo


def test_create_session_with_clear_request_creates_child_version(tmp_path):
    service, _repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="edit",
            assistant_message="I edited the image.",
            tool_name="gpt_image_2_edit",
            tool_instruction="Make it brighter.",
            response_id="resp_123",
        ),
    )

    envelope = service.create_session(
        instruction="Make it brighter",
        image_bytes=b"initial",
        image_name="product.png",
        mime_type="image/png",
        size="1536x1024",
    )

    assert envelope.session.previousResponseId == "resp_123"
    assert len(envelope.versions) == 2
    assert envelope.currentImage.model == "gpt-image-2"
    assert envelope.pendingQuestion is None


def test_follow_up_can_return_clarifying_question_without_new_version(tmp_path):
    service, _repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="clarify",
            assistant_message="Which background style do you want?",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_456",
        ),
    )
    created = service.create_session(
        instruction="Initial upload",
        image_bytes=b"initial",
        image_name="product.png",
        mime_type="image/png",
        size="1536x1024",
    )
    original_image_id = created.currentImage.id
    original_version_count = len(created.versions)

    envelope = service.send_message(created.session.id, "Make it better", size="1536x1024")

    assert envelope.pendingQuestion == "Which background style do you want?"
    assert len(envelope.versions) == original_version_count
    assert envelope.currentImage.id == original_image_id


def test_restore_version_rejects_unknown_version(tmp_path):
    service, _repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="clarify",
            assistant_message="Which background style do you want?",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_456",
        ),
    )
    created = service.create_session(
        instruction="Initial upload",
        image_bytes=b"initial",
        image_name="product.png",
        mime_type="image/png",
        size="1536x1024",
    )

    with pytest.raises(AgentInputError, match="Image version not found."):
        service.restore_version(created.session.id, uuid4())


def test_send_message_rejects_unknown_session_before_writing_user_message(tmp_path):
    service, _repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="clarify",
            assistant_message="Which background style do you want?",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_456",
        ),
    )

    with pytest.raises(AgentInputError, match="Session not found."):
        service.send_message(uuid4(), "Make it better", size="1536x1024")


def test_send_message_rejects_session_without_active_image_before_writing_user_message(
    tmp_path,
):
    service, repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="clarify",
            assistant_message="Which background style do you want?",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_456",
        ),
    )
    session = repo.create_session("Empty session")

    with pytest.raises(AgentInputError, match="Session has no active image."):
        service.send_message(session.id, "Make it better", size="1536x1024")

    state = repo.get_session_state(session.id)
    assert state.messages == []


def test_create_session_cleans_up_first_turn_failure(tmp_path):
    service, repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="edit",
            assistant_message="I edited the image.",
            tool_name="missing_tool",
            tool_instruction="Make it brighter.",
            response_id="resp_failed",
        ),
        tool={},
    )

    with pytest.raises(AgentServiceError, match="not available"):
        service.create_session(
            instruction="Make it brighter",
            image_bytes=b"initial",
            image_name="product.png",
            mime_type="image/png",
            size="1536x1024",
        )

    assert repo.db.scalars(select(AgentSessionRow)).all() == []
    assert repo.db.scalars(select(AgentMessageRow)).all() == []
    assert repo.db.scalars(select(ImageVersionRow)).all() == []
    assert list(tmp_path.iterdir()) == []


def test_missing_edit_tool_does_not_persist_assistant_turn(tmp_path):
    service, _repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="clarify",
            assistant_message="Which background style do you want?",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_initial",
        ),
    )
    created = service.create_session(
        instruction="Initial upload",
        image_bytes=b"initial",
        image_name="product.png",
        mime_type="image/png",
        size="1536x1024",
    )
    original_message_count = len(created.messages)
    original_previous_response_id = created.session.previousResponseId

    service.planner = lambda **kwargs: AgentTurnDecision(
        action="edit",
        assistant_message="I edited the image.",
        tool_name="missing_tool",
        tool_instruction="Make it brighter.",
        response_id="resp_failed",
    )

    with pytest.raises(AgentServiceError, match="not available"):
        service.send_message(created.session.id, "Make it brighter", size="1536x1024")

    envelope = service.get_session(created.session.id)
    assert envelope.session.previousResponseId == original_previous_response_id
    assert len(envelope.messages) == original_message_count + 1
    assert envelope.messages[-1].role == "user"
    assert len(envelope.versions) == len(created.versions)
    assert envelope.currentImage.id == created.currentImage.id


def test_failing_edit_tool_does_not_persist_assistant_turn(tmp_path):
    class FailingTool:
        name = "gpt_image_2_edit"
        description = "failing"

        def execute(self, context: AgentToolContext) -> AgentToolResult:
            raise RuntimeError("image edit failed")

    service, _repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="clarify",
            assistant_message="Which background style do you want?",
            tool_name=None,
            tool_instruction=None,
            response_id="resp_initial",
        ),
        tool=FailingTool(),
    )
    created = service.create_session(
        instruction="Initial upload",
        image_bytes=b"initial",
        image_name="product.png",
        mime_type="image/png",
        size="1536x1024",
    )
    original_message_count = len(created.messages)
    original_previous_response_id = created.session.previousResponseId

    service.planner = lambda **kwargs: AgentTurnDecision(
        action="edit",
        assistant_message="I edited the image.",
        tool_name="gpt_image_2_edit",
        tool_instruction="Make it brighter.",
        response_id="resp_failed",
    )

    with pytest.raises(RuntimeError, match="image edit failed"):
        service.send_message(created.session.id, "Make it brighter", size="1536x1024")

    envelope = service.get_session(created.session.id)
    assert envelope.session.previousResponseId == original_previous_response_id
    assert len(envelope.messages) == original_message_count + 1
    assert envelope.messages[-1].role == "user"
    assert len(envelope.versions) == len(created.versions)
    assert envelope.currentImage.id == created.currentImage.id


def test_edit_tool_receives_active_storage_filename(tmp_path):
    received_names = []

    class RecordingTool:
        name = "gpt_image_2_edit"
        description = "recording"

        def execute(self, context: AgentToolContext) -> AgentToolResult:
            received_names.append(context.image_name)
            return AgentToolResult(
                image_bytes=b"edited",
                mime_type="image/png",
                prompt=context.instruction,
                revised_prompt="edited prompt",
                model="gpt-image-2",
            )

    service, _repo = make_service(
        tmp_path,
        AgentTurnDecision(
            action="edit",
            assistant_message="I edited the image.",
            tool_name="gpt_image_2_edit",
            tool_instruction="Make it brighter.",
            response_id="resp_123",
        ),
        tool=RecordingTool(),
    )

    envelope = service.create_session(
        instruction="Make it brighter",
        image_bytes=b"initial jpeg",
        image_name="product.jpg",
        mime_type="image/jpeg",
        size="1536x1024",
    )

    assert received_names == [envelope.versions[0].storageKey]
    assert received_names[0].endswith(".jpg")
