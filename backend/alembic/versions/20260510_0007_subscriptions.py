"""create subscription tables

Revision ID: 20260510_0007
Revises: 20260510_0006
Create Date: 2026-05-10 00:07:00.000000
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260510_0007"
down_revision = "20260510_0006"
branch_labels = None
depends_on = None

FREE_PLAN_ID = "00000000-0000-0000-0000-000000000001"
FREE_PLAN_CODE = "free"
FREE_PLAN_NAME = "Free"
subscription_plans_table = sa.table(
    "subscription_plans",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.Text()),
    sa.column("name", sa.Text()),
    sa.column("description", sa.Text()),
    sa.column("price_cents", sa.Integer()),
    sa.column("daily_image_limit", sa.Integer()),
    sa.column("monthly_image_limit", sa.Integer()),
    sa.column("is_active", sa.Boolean()),
    sa.column("is_default", sa.Boolean()),
    sa.column("sort_order", sa.Integer()),
    sa.column("created_at", sa.DateTime(timezone=True)),
    sa.column("updated_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    op.create_table("subscription_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("daily_image_limit", sa.Integer(), nullable=False),
        sa.Column("monthly_image_limit", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "price_cents >= 0",
            name="ck_subscription_plans_price_cents_non_negative",
        ),
        sa.CheckConstraint(
            "daily_image_limit > 0",
            name="ck_subscription_plans_daily_image_limit_positive",
        ),
        sa.CheckConstraint(
            "monthly_image_limit > 0",
            name="ck_subscription_plans_monthly_image_limit_positive",
        ),
        sa.CheckConstraint(
            "daily_image_limit <= monthly_image_limit",
            name="ck_subscription_plans_daily_limit_lte_monthly_limit",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_subscription_plans_code",
        "subscription_plans",
        ["code"],
        unique=True,
    )
    op.create_table("user_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_subscriptions_plan_id",
        "user_subscriptions",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_subscriptions_user_id",
        "user_subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_table("image_usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=True),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("image_count", sa.Integer(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["user_subscriptions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.CheckConstraint(
            "image_count > 0",
            name="ck_image_usage_events_image_count_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_image_usage_events_created_at",
        "image_usage_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_image_usage_events_plan_id",
        "image_usage_events",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_image_usage_events_subscription_id",
        "image_usage_events",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_image_usage_events_user_id",
        "image_usage_events",
        ["user_id"],
        unique=False,
    )
    with op.batch_alter_table("payment_orders") as batch_op:
        batch_op.add_column(sa.Column("plan_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("subscription_id", sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "order_kind",
                sa.Text(),
                nullable=False,
                server_default="payment",
            )
        )
        batch_op.create_index("ix_payment_orders_plan_id", ["plan_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_payment_orders_plan_id_subscription_plans",
            "subscription_plans",
            ["plan_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_payment_orders_subscription_id",
            ["subscription_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_payment_orders_subscription_id_user_subscriptions",
            "user_subscriptions",
            ["subscription_id"],
            ["id"],
        )

    now = datetime.now(timezone.utc)
    op.bulk_insert(
        subscription_plans_table,
        [
            {
                "id": uuid.UUID(FREE_PLAN_ID),
                "code": FREE_PLAN_CODE,
                "name": FREE_PLAN_NAME,
                "description": "Default free image quota.",
                "price_cents": 0,
                "daily_image_limit": 5,
                "monthly_image_limit": 50,
                "is_active": True,
                "is_default": True,
                "sort_order": 0,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    with op.batch_alter_table("payment_orders") as batch_op:
        batch_op.drop_constraint(
            "fk_payment_orders_subscription_id_user_subscriptions",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_payment_orders_plan_id_subscription_plans",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_payment_orders_subscription_id")
        batch_op.drop_index("ix_payment_orders_plan_id")
        batch_op.drop_column("order_kind")
        batch_op.drop_column("subscription_id")
        batch_op.drop_column("plan_id")
    op.drop_index("ix_image_usage_events_user_id", table_name="image_usage_events")
    op.drop_index("ix_image_usage_events_subscription_id", table_name="image_usage_events")
    op.drop_index("ix_image_usage_events_plan_id", table_name="image_usage_events")
    op.drop_index("ix_image_usage_events_created_at", table_name="image_usage_events")
    op.drop_table("image_usage_events")
    op.drop_index("ix_user_subscriptions_user_id", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_plan_id", table_name="user_subscriptions")
    op.drop_table("user_subscriptions")
    op.drop_index("ix_subscription_plans_code", table_name="subscription_plans")
    op.drop_table("subscription_plans")
