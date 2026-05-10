from pathlib import Path

from app.agent_models import (
    AgentMessageImageVersionRow,
    AgentMessageRow,
    AgentSessionRow,
    ImageVersionRow,
)
from app.db import Base


def test_base_metadata_includes_agent_tables():
    assert {
        "agent_sessions",
        "agent_messages",
        "agent_message_image_versions",
        "image_versions",
    } <= set(Base.metadata.tables)


def test_agent_session_columns():
    assert {
        "id",
        "title",
        "current_version_id",
        "previous_response_id",
        "status",
        "created_at",
        "updated_at",
    } <= set(AgentSessionRow.__table__.columns.keys())


def test_agent_session_summary_columns():
    assert {"summary", "summary_updated_at"} <= set(
        AgentSessionRow.__table__.columns.keys()
    )


def test_image_version_columns():
    assert {"parent_version_id", "storage_key", "prompt", "model"} <= set(
        ImageVersionRow.__table__.columns.keys()
    )


def test_agent_message_session_relationship_targets_agent_session():
    assert AgentMessageRow.session.property.mapper.class_ is AgentSessionRow


def test_agent_message_can_reference_image_version():
    assert "image_version_id" in AgentMessageRow.__table__.columns.keys()
    assert AgentMessageRow.image_version.property.mapper.class_ is ImageVersionRow


def test_agent_message_image_version_association_columns_and_relationships():
    assert {"message_id", "image_version_id", "position"} <= set(
        AgentMessageImageVersionRow.__table__.columns.keys()
    )
    assert (
        AgentMessageImageVersionRow.message.property.mapper.class_
        is AgentMessageRow
    )
    assert (
        AgentMessageImageVersionRow.image_version.property.mapper.class_
        is ImageVersionRow
    )


def test_alembic_config_uses_repo_root_script_location():
    alembic_config = Path("backend/alembic.ini").read_text(encoding="utf-8")

    assert "script_location = backend/alembic" in alembic_config
