from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import uuid

from app.db import Base
from app.subscription_models import (
    ImageUsageEventRow,
    SubscriptionPlanRow,
    UserSubscriptionRow,
)


def test_base_metadata_includes_subscription_tables():
    assert {
        "subscription_plans",
        "user_subscriptions",
        "image_usage_events",
    } <= set(Base.metadata.tables)


def test_subscription_plan_columns():
    assert {
        "id",
        "code",
        "name",
        "description",
        "price_cents",
        "daily_image_limit",
        "monthly_image_limit",
        "is_active",
        "is_default",
        "sort_order",
        "created_at",
        "updated_at",
    } <= set(SubscriptionPlanRow.__table__.columns.keys())
    assert SubscriptionPlanRow.__table__.columns["code"].unique is True


def test_subscription_plan_constraints():
    constraint_names = {
        constraint.name for constraint in SubscriptionPlanRow.__table__.constraints
    }

    assert "ck_subscription_plans_price_cents_non_negative" in constraint_names
    assert "ck_subscription_plans_daily_image_limit_positive" in constraint_names
    assert "ck_subscription_plans_monthly_image_limit_positive" in constraint_names
    assert "ck_subscription_plans_daily_limit_lte_monthly_limit" in constraint_names


def test_user_subscription_columns():
    assert {
        "id",
        "user_id",
        "plan_id",
        "status",
        "starts_at",
        "ends_at",
        "created_at",
        "updated_at",
    } <= set(UserSubscriptionRow.__table__.columns.keys())


def test_image_usage_event_columns():
    assert {
        "id",
        "user_id",
        "subscription_id",
        "plan_id",
        "image_count",
        "source",
        "created_at",
    } <= set(ImageUsageEventRow.__table__.columns.keys())


def test_image_usage_event_constraints():
    constraint_names = {
        constraint.name for constraint in ImageUsageEventRow.__table__.constraints
    }

    assert "ck_image_usage_events_image_count_positive" in constraint_names


def test_subscriptions_migration_exists_and_seeds_free_plan():
    migration = Path(
        "backend/alembic/versions/20260510_0007_subscriptions.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260510_0007"' in migration
    assert 'down_revision = "20260510_0006"' in migration
    assert 'op.create_table("subscription_plans"' in migration
    assert 'op.create_table("user_subscriptions"' in migration
    assert 'op.create_table("image_usage_events"' in migration
    assert 'op.batch_alter_table("payment_orders")' in migration
    assert 'batch_op.add_column(sa.Column("plan_id"' in migration
    assert 'batch_op.add_column(sa.Column("subscription_id"' in migration
    assert 'batch_op.add_column(' in migration
    assert '"order_kind"' in migration
    assert '"ix_payment_orders_subscription_id"' in migration
    assert '"free"' in migration
    assert "Free" in migration
    assert "daily_image_limit" in migration
    assert "monthly_image_limit" in migration
    assert 'op.drop_table("image_usage_events")' in migration
    assert 'op.drop_table("user_subscriptions")' in migration
    assert 'op.drop_table("subscription_plans")' in migration
    assert "import uuid" in migration
    assert 'sa.column("id", sa.Uuid())' in migration
    assert '"id": uuid.UUID(FREE_PLAN_ID)' in migration
    assert "ck_subscription_plans_price_cents_non_negative" in migration
    assert "ck_image_usage_events_image_count_positive" in migration


def test_subscriptions_migration_upgrades_sqlite_database(tmp_path):
    database_path = tmp_path / "subscription_migration.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            create table alembic_version (
                version_num varchar(32) not null primary key
            );
            insert into alembic_version (version_num) values ('20260510_0006');

            create table users (
                id char(32) not null primary key
            );

            create table payment_orders (
                id char(32) not null primary key,
                order_no text not null,
                user_id char(32) not null,
                user_public_id text not null,
                provider text not null,
                provider_trade_no text,
                subject text not null,
                amount_cents integer not null,
                pay_type text not null,
                status text not null,
                payment_url text,
                raw_callback text,
                created_at datetime not null,
                updated_at datetime not null,
                paid_at datetime,
                foreign key(user_id) references users (id)
            );
            """
        )

    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite+pysqlite:///{database_path.as_posix()}",
    }

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "upgrade",
            "20260510_0007",
        ],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }
        free_plan = connection.execute(
            "select code, name from subscription_plans where id = ?",
            (uuid.UUID("00000000-0000-0000-0000-000000000001").hex,),
        ).fetchone()

    assert "subscription_plans" in tables
    assert free_plan == ("free", "Free")
