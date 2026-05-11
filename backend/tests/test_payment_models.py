from pathlib import Path

from app.db import Base
from app.payment_models import PaymentOrderRow


def test_base_metadata_includes_payment_orders_table():
    assert "payment_orders" in set(Base.metadata.tables)


def test_payment_order_columns_match_zpay_design():
    assert {
        "id",
        "order_no",
        "user_id",
        "user_public_id",
        "provider",
        "provider_trade_no",
        "subscription_id",
        "subject",
        "amount_cents",
        "pay_type",
        "status",
        "payment_url",
        "raw_callback",
        "created_at",
        "updated_at",
        "paid_at",
    } <= set(PaymentOrderRow.__table__.columns.keys())


def test_payment_order_unique_order_number_index():
    columns = PaymentOrderRow.__table__.columns

    assert columns["order_no"].unique is True
    assert columns["order_no"].index is True


def test_payment_orders_migration_exists():
    migration = Path(
        "backend/alembic/versions/20260510_0006_payment_orders.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260510_0006"' in migration
    assert 'down_revision = "20260510_0005"' in migration
    assert 'op.create_table("payment_orders"' in migration
    assert '"order_no"' in migration
    assert '"amount_cents"' in migration
    assert 'op.create_index("ix_payment_orders_order_no"' in migration
    assert 'op.drop_index("ix_payment_orders_order_no", table_name="payment_orders")' in migration
    assert 'op.drop_table("payment_orders")' in migration


def test_payment_order_can_reference_subscription_plan():
    assert {"plan_id", "order_kind", "subscription_id"} <= set(
        PaymentOrderRow.__table__.columns.keys()
    )
