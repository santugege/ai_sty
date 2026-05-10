import inspect
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agent_models import AgentSessionRow, ImageVersionRow
from app.agent_repository import AgentRepository
from app.db import Base


def test_set_previous_response_id_accepts_none():
    signature = inspect.signature(
        AgentRepository.set_previous_response_id, eval_str=True
    )

    assert signature.parameters["response_id"].annotation == str | None


def make_repo() -> AgentRepository:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    return AgentRepository(session)


def test_list_sessions_orders_by_recent_update():
    repo = make_repo()
    first_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    second_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    first = AgentSessionRow(
        id=first_id,
        title="First",
        created_at=datetime(2026, 5, 10, 8, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 10, 8, 0, tzinfo=timezone.utc),
    )
    second = AgentSessionRow(
        id=second_id,
        title="Second",
        created_at=datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 10, 9, 0, tzinfo=timezone.utc),
    )
    repo.db.add_all([first, second])
    repo.db.commit()

    sessions = repo.list_sessions()

    assert [row.id for row in sessions] == [second.id, first.id]


def test_list_sessions_uses_id_tiebreaker_when_timestamps_match():
    repo = make_repo()
    lower_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    higher_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    same_time = datetime(2026, 5, 10, 8, 0, tzinfo=timezone.utc)
    lower = AgentSessionRow(
        id=lower_id,
        title="Lower",
        created_at=same_time,
        updated_at=same_time,
    )
    higher = AgentSessionRow(
        id=higher_id,
        title="Higher",
        created_at=same_time,
        updated_at=same_time,
    )
    repo.db.add_all([lower, higher])
    repo.db.commit()

    sessions = repo.list_sessions()

    assert [row.id for row in sessions] == [higher_id, lower_id]


def test_update_session_summary_persists_text_and_timestamp():
    repo = make_repo()
    session = repo.create_session("Summary test")

    repo.update_session_summary(session.id, "User wants a clean product image.")

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.summary == "User wants a clean product image."
    assert state.session.summary_updated_at is not None


def test_add_message_can_link_generated_image_version():
    repo = make_repo()
    session = repo.create_session("Linked image")
    version = repo.add_image_version(
        session_id=session.id,
        parent_version_id=None,
        storage_key="agent-sessions/session/v1.png",
        mime_type="image/png",
        prompt="edit",
        model="gpt-image-2",
    )

    message = repo.add_message(
        session_id=session.id,
        role="assistant",
        content="Done.",
        image_version_id=version.id,
    )

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.messages == [message]
    assert state.messages[0].image_version_id == version.id


def test_add_message_rejects_cross_session_image_version_link():
    repo = make_repo()
    first_session = repo.create_session("First session")
    second_session = repo.create_session("Second session")
    other_version = repo.add_image_version(
        session_id=second_session.id,
        parent_version_id=None,
        storage_key="agent-sessions/other/v1.png",
        mime_type="image/png",
        prompt="edit",
        model="gpt-image-2",
    )

    message = repo.add_message(
        session_id=first_session.id,
        role="assistant",
        content="Done.",
        image_version_id=other_version.id,
    )

    state = repo.get_session_state(first_session.id)
    assert state is not None
    assert state.messages == [message]
    assert state.messages[0].image_version_id is None


def test_update_session_title_renames_existing_session():
    repo = make_repo()
    session = repo.create_session("Old")

    repo.update_session_title(session.id, "New")

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.title == "New"


def test_create_session_persists_initial_version_and_message():
    repo = make_repo()

    session = repo.create_session("Campaign hero")
    version = repo.add_image_version(
        session_id=session.id,
        parent_version_id=None,
        storage_key="images/session-1/v1.png",
        mime_type="image/png",
        prompt="make a campaign hero",
        model="gpt-image-2",
        revised_prompt="make a polished campaign hero",
        width=1024,
        height=1024,
        public_url="https://example.test/v1.png",
    )
    message = repo.add_message(
        session_id=session.id,
        role="user",
        content="make a campaign hero",
        response_id="resp_123",
        tool_call_id="tool_123",
    )
    repo.set_current_version(session.id, version.id)

    state = repo.get_session_state(session.id)

    assert state is not None
    assert state.session.id == session.id
    assert state.session.current_version_id == version.id
    assert state.messages == [message]
    assert state.versions == [version]
    assert state.messages[0].response_id == "resp_123"
    assert state.messages[0].tool_call_id == "tool_123"
    assert state.versions[0].storage_key == "images/session-1/v1.png"
    assert state.versions[0].public_url == "https://example.test/v1.png"


def test_restore_version_updates_only_current_version():
    repo = make_repo()
    session = repo.create_session("Restore test")
    first = repo.add_image_version(
        session_id=session.id,
        parent_version_id=None,
        storage_key="images/session-1/v1.png",
        mime_type="image/png",
        prompt="first prompt",
        model="gpt-image-2",
    )
    second = repo.add_image_version(
        session_id=session.id,
        parent_version_id=first.id,
        storage_key="images/session-1/v2.png",
        mime_type="image/png",
        prompt="second prompt",
        model="gpt-image-2",
    )
    repo.set_current_version(session.id, second.id)

    repo.restore_version(session.id, first.id)

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.current_version_id == first.id
    assert [version.id for version in state.versions] == [first.id, second.id]


def test_versions_are_returned_in_parent_chain_order_when_timestamps_match():
    repo = make_repo()
    session = repo.create_session("Stable ordering")
    first_id = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")
    second_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    same_time = datetime(2026, 5, 10, tzinfo=timezone.utc)
    first = ImageVersionRow(
        id=first_id,
        session_id=session.id,
        parent_version_id=None,
        storage_key="images/session-1/v1.png",
        mime_type="image/png",
        prompt="first prompt",
        model="gpt-image-2",
        created_at=same_time,
    )
    second = ImageVersionRow(
        id=second_id,
        session_id=session.id,
        parent_version_id=first.id,
        storage_key="images/session-1/v2.png",
        mime_type="image/png",
        prompt="second prompt",
        model="gpt-image-2",
        created_at=same_time,
    )
    repo.db.add_all([first, second])
    repo.db.commit()

    state = repo.get_session_state(session.id)

    assert state is not None
    assert [version.id for version in state.versions] == [first_id, second_id]


def test_restore_version_rejects_version_from_another_session():
    repo = make_repo()
    first_session = repo.create_session("First session")
    second_session = repo.create_session("Second session")
    first_version = repo.add_image_version(
        session_id=first_session.id,
        parent_version_id=None,
        storage_key="images/session-1/v1.png",
        mime_type="image/png",
        prompt="first prompt",
        model="gpt-image-2",
    )
    second_version = repo.add_image_version(
        session_id=second_session.id,
        parent_version_id=None,
        storage_key="images/session-2/v1.png",
        mime_type="image/png",
        prompt="second prompt",
        model="gpt-image-2",
    )
    repo.set_current_version(first_session.id, first_version.id)

    repo.restore_version(first_session.id, second_version.id)

    state = repo.get_session_state(first_session.id)
    assert state is not None
    assert state.session.current_version_id == first_version.id


def test_set_current_version_rejects_version_from_another_session():
    repo = make_repo()
    first_session = repo.create_session("First session")
    second_session = repo.create_session("Second session")
    first_version = repo.add_image_version(
        session_id=first_session.id,
        parent_version_id=None,
        storage_key="images/session-1/v1.png",
        mime_type="image/png",
        prompt="first prompt",
        model="gpt-image-2",
    )
    second_version = repo.add_image_version(
        session_id=second_session.id,
        parent_version_id=None,
        storage_key="images/session-2/v1.png",
        mime_type="image/png",
        prompt="second prompt",
        model="gpt-image-2",
    )
    repo.set_current_version(first_session.id, first_version.id)

    repo.set_current_version(first_session.id, second_version.id)

    state = repo.get_session_state(first_session.id)
    assert state is not None
    assert state.session.current_version_id == first_version.id


def test_remove_turn_artifacts_deletes_messages_and_versions_and_restores_current_version():
    repo = make_repo()
    session = repo.create_session("Rollback test")
    original = repo.add_image_version(
        session_id=session.id,
        parent_version_id=None,
        storage_key="images/session-1/original.png",
        mime_type="image/png",
        prompt="original",
        model="user-upload",
    )
    repo.set_current_version(session.id, original.id)
    transient = repo.add_image_version(
        session_id=session.id,
        parent_version_id=original.id,
        storage_key="images/session-1/transient.png",
        mime_type="image/png",
        prompt="transient",
        model="user-upload",
    )
    repo.set_current_version(session.id, transient.id)
    message = repo.add_message(
        session_id=session.id,
        role="user",
        content="Bad turn",
        image_version_id=transient.id,
    )

    repo.remove_turn_artifacts(
        session_id=session.id,
        message_ids=[message.id],
        version_ids=[transient.id],
        restored_current_version_id=original.id,
    )

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.current_version_id == original.id
    assert [item.id for item in state.messages] == []
    assert [item.id for item in state.versions] == [original.id]


def test_set_previous_response_id_persists_and_can_be_cleared():
    repo = make_repo()
    session = repo.create_session("Response continuity")

    repo.set_previous_response_id(session.id, "resp_x")

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.previous_response_id == "resp_x"

    repo.set_previous_response_id(session.id, None)

    state = repo.get_session_state(session.id)
    assert state is not None
    assert state.session.previous_response_id is None


def test_missing_session_returns_none():
    repo = make_repo()

    assert repo.get_session_state(uuid.uuid4()) is None
