"""add agent session summaries and message image links

Revision ID: 20260510_0002
Revises: 20260508_0001
Create Date: 2026-05-10 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0002"
down_revision = "20260508_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_sessions", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "agent_sessions",
        sa.Column("summary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_messages", sa.Column("image_version_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_agent_messages_image_version_id_image_versions",
        "agent_messages",
        "image_versions",
        ["image_version_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agent_messages_image_version_id_image_versions",
        "agent_messages",
        type_="foreignkey",
    )
    op.drop_column("agent_messages", "image_version_id")
    op.drop_column("agent_sessions", "summary_updated_at")
    op.drop_column("agent_sessions", "summary")
