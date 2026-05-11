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
    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("summary_updated_at", sa.DateTime(timezone=True), nullable=True)
        )

    with op.batch_alter_table("agent_messages") as batch_op:
        batch_op.add_column(sa.Column("image_version_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_agent_messages_image_version_id_image_versions",
            "image_versions",
            ["image_version_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_messages") as batch_op:
        batch_op.drop_constraint(
            "fk_agent_messages_image_version_id_image_versions",
            type_="foreignkey",
        )
        batch_op.drop_column("image_version_id")

    with op.batch_alter_table("agent_sessions") as batch_op:
        batch_op.drop_column("summary_updated_at")
        batch_op.drop_column("summary")
