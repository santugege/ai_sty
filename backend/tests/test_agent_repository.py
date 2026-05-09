import inspect
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
