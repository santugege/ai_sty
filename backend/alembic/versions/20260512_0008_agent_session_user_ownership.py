"""add agent session user ownership

Revision ID: 20260512_0008
Revises: 20260510_0007
Create Date: 2026-05-12 00:08:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260512_0008"
down_revision = "20260510_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_sessions", sa.Column("user_id", sa.Uuid(), nullable=True))
    bind = op.get_bind()
    orphaned_session_count = bind.scalar(
        sa.text(
            """
            SELECT count(*)
            FROM agent_sessions
            WHERE NOT EXISTS (SELECT 1 FROM users)
            """
        )
    )
    if orphaned_session_count:
        raise RuntimeError(
            "Cannot assign existing agent sessions to an owner because no users exist."
        )
    op.execute(
        """
        UPDATE agent_sessions
        SET user_id = (
            SELECT users.id
            FROM users
            ORDER BY users.created_at ASC, users.id ASC
            LIMIT 1
        )
        WHERE user_id IS NULL
        """
    )
    op.alter_column("agent_sessions", "user_id", nullable=False)
    op.create_index(
        "ix_agent_sessions_user_id",
        "agent_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_agent_sessions_user_id_users",
        "agent_sessions",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agent_sessions_user_id_users",
        "agent_sessions",
        type_="foreignkey",
    )
    op.drop_index("ix_agent_sessions_user_id", table_name="agent_sessions")
    op.drop_column("agent_sessions", "user_id")
