"""add agent message image version links

Revision ID: 20260510_0003
Revises: 20260510_0002
Create Date: 2026-05-10 00:03:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0003"
down_revision = "20260510_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_message_image_versions",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("image_version_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["image_version_id"], ["image_versions.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["agent_messages.id"]),
        sa.PrimaryKeyConstraint("message_id", "image_version_id"),
    )


def downgrade() -> None:
    op.drop_table("agent_message_image_versions")
