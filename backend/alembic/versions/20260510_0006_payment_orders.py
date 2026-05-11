"""create payment orders

Revision ID: 20260510_0006
Revises: 20260510_0005
Create Date: 2026-05-10 00:06:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0006"
down_revision = "20260510_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("payment_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_no", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_public_id", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_trade_no", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("pay_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("payment_url", sa.Text(), nullable=True),
        sa.Column("raw_callback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_orders_order_no",
        "payment_orders",
        ["order_no"],
        unique=True,
    )
    op.create_index("ix_payment_orders_user_id",
        "payment_orders",
        ["user_id"],
        unique=False,
    )
    op.create_index("ix_payment_orders_user_public_id",
        "payment_orders",
        ["user_public_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payment_orders_user_public_id", table_name="payment_orders")
    op.drop_index("ix_payment_orders_user_id", table_name="payment_orders")
    op.drop_index("ix_payment_orders_order_no", table_name="payment_orders")
    op.drop_table("payment_orders")
