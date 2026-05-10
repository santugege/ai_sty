"""allow only one admin user

Revision ID: 20260510_0005
Revises: 20260510_0004
Create Date: 2026-05-10 00:05:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0005"
down_revision = "20260510_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    admin_count = bind.scalar(
        sa.text("select count(*) from users where is_admin = true")
    )
    if admin_count > 1:
        raise RuntimeError(
            "Cannot add single-admin constraint while multiple admin users exist. "
            "deactivate extra admins before retrying this migration."
        )

    op.create_index("ix_users_single_admin",
        "users",
        ["is_admin"],
        unique=True,
        postgresql_where=sa.text("is_admin = true"),
        sqlite_where=sa.text("is_admin = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_single_admin", table_name="users")
