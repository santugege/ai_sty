import uuid
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.payment_models import PaymentOrderRow
from app.payment_repository import PaymentRepository
from app.payment_service import (
    PaymentService,
    PaymentServiceError,
    amount_cents,
    cents_to_money,
    load_zpay_settings,
)
from app.subscription_models import SubscriptionPlanRow, UserSubscriptionRow
from app.subscription_repository import SubscriptionRepository
from app.subscription_service import SubscriptionService
from app.user_models import UserRow
from app.zpay_client import signed_params


def make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db: Session) -> UserRow:
    user = UserRow(
        user_id="U00000001",
        email="tester@example.com",
        username="tester",
        password_hash="hash",
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_plan(
    db: Session,
    *,
    code: str = "pro",
    name: str = "Pro Plan",
    price_cents: int = 1990,
) -> SubscriptionPlanRow:
    plan = SubscriptionPlanRow(
        code=code,
        name=name,
        description="Paid image quota.",
        price_cents=price_cents,
        daily_image_limit=20,
        monthly_image_limit=500,
        is_active=True,
        is_default=False,
        sort_order=10,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_amount_cents_accepts_two_decimal_yuan_values():
    assert amount_cents("9.90") == 990
    assert cents_to_money(990) == "9.90"


def test_amount_cents_rejects_invalid_values():
    with pytest.raises(PaymentServiceError):
        amount_cents("0")

    with pytest.raises(PaymentServiceError):
        amount_cents("1.001")


def test_load_zpay_settings_requires_pid_and_key(monkeypatch):
    monkeypatch.delenv("ZPAY_PID", raising=False)
    monkeypatch.delenv("ZPAY_KEY", raising=False)

    with pytest.raises(PaymentServiceError) as error:
        load_zpay_settings()

    assert str(error.value) == "ZPAY is not configured."


def test_create_zpay_order_persists_pending_order_with_signed_payment_url(monkeypatch):
    db = make_session()
    user = make_user(db)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    monkeypatch.setenv("ZPAY_SUBMIT_URL", "https://zpayz.cn/submit.php")
    monkeypatch.setenv("BACKEND_PUBLIC_ORIGIN", "https://api.example.com")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")

    order = PaymentService(PaymentRepository(db)).create_zpay_order(
        user=user,
        subject="Image credits",
        amount="9.90",
        pay_type="alipay",
    )

    stored = db.query(PaymentOrderRow).one()
    parsed = urlsplit(order.payment_url)
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}

    assert stored.order_no == order.order_no
    assert stored.user_id == user.id
    assert stored.user_public_id == "U00000001"
    assert stored.provider == "zpay"
    assert stored.status == "pending"
    assert stored.amount_cents == 990
    assert parsed.netloc == "zpayz.cn"
    assert query["pid"] == "merchant-1"
    assert query["name"] == "Image credits"
    assert query["money"] == "9.90"
    assert query["notify_url"] == "https://api.example.com/api/payments/zpay/notify"
    assert query["return_url"] == "https://app.example.com/payments/return"
    assert query["param"] == "user_id=U00000001"
    assert query["sign_type"] == "MD5"


def test_create_zpay_order_rejects_unsupported_pay_type(monkeypatch):
    db = make_session()
    user = make_user(db)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")

    with pytest.raises(PaymentServiceError) as error:
        PaymentService(PaymentRepository(db)).create_zpay_order(
            user=user,
            subject="Image credits",
            amount="9.90",
            pay_type="unionpay",
        )

    assert str(error.value) == "Unsupported payment method."


def test_create_subscription_zpay_order_uses_plan_price_and_name(monkeypatch):
    db = make_session()
    user = make_user(db)
    plan = make_plan(db, price_cents=1990)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    monkeypatch.setenv("ZPAY_SUBMIT_URL", "https://zpayz.cn/submit.php")
    monkeypatch.setenv("BACKEND_PUBLIC_ORIGIN", "https://api.example.com")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")

    order = PaymentService(PaymentRepository(db)).create_subscription_zpay_order(
        user=user,
        plan=plan,
        pay_type="alipay",
    )

    stored = db.query(PaymentOrderRow).one()
    parsed = urlsplit(order.payment_url)
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}

    assert stored.order_no == order.order_no
    assert stored.plan_id == plan.id
    assert stored.order_kind == "subscription"
    assert stored.subject == "Pro Plan"
    assert stored.amount_cents == plan.price_cents
    assert query["name"] == "Pro Plan"
    assert query["money"] == "19.90"
    assert query["param"] == f"user_id={user.user_id};plan_id={plan.id}"


def test_handle_zpay_notify_marks_matching_order_paid_and_is_idempotent(monkeypatch):
    db = make_session()
    user = make_user(db)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    service = PaymentService(PaymentRepository(db))
    order = PaymentOrderRow(
        id=uuid.uuid4(),
        order_no="P202605100001",
        user_id=user.id,
        user_public_id=user.user_id,
        provider="zpay",
        subject="Image credits",
        amount_cents=990,
        pay_type="alipay",
        status="pending",
    )
    db.add(order)
    db.commit()

    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200001",
            "out_trade_no": "P202605100001",
            "type": "alipay",
            "name": "Image credits",
            "money": "9.90",
            "trade_status": "TRADE_SUCCESS",
            "param": "user_id=U00000001",
        },
        "secret",
    )

    paid = service.handle_zpay_notify(callback)
    paid_again = service.handle_zpay_notify(callback)

    db.refresh(order)
    assert paid.order_no == order.order_no
    assert paid_again.order_no == order.order_no
    assert order.status == "paid"
    assert order.provider_trade_no == "202605102200001"
    assert order.paid_at is not None
    assert '"trade_status": "TRADE_SUCCESS"' in (order.raw_callback or "")


def test_handle_zpay_notify_activates_paid_subscription_order(monkeypatch):
    db = make_session()
    user = make_user(db)
    plan = make_plan(db, price_cents=1990)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    service = PaymentService(PaymentRepository(db))
    subscription_service = SubscriptionService(SubscriptionRepository(db))
    order = PaymentOrderRow(
        id=uuid.uuid4(),
        order_no="P202605100002",
        user_id=user.id,
        user_public_id=user.user_id,
        provider="zpay",
        plan_id=plan.id,
        order_kind="subscription",
        subject=plan.name,
        amount_cents=plan.price_cents,
        pay_type="alipay",
        status="pending",
    )
    db.add(order)
    db.commit()
    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200002",
            "out_trade_no": "P202605100002",
            "type": "alipay",
            "name": plan.name,
            "money": "19.90",
            "trade_status": "TRADE_SUCCESS",
            "param": f"user_id={user.user_id};plan_id={plan.id}",
        },
        "secret",
    )

    paid = service.handle_zpay_notify(
        callback,
        subscription_service=subscription_service,
        user=user,
    )
    paid_again = service.handle_zpay_notify(
        callback,
        subscription_service=subscription_service,
        user=user,
    )

    subscriptions = db.query(UserSubscriptionRow).all()
    assert paid.order_no == order.order_no
    assert paid_again.order_no == order.order_no
    assert len(subscriptions) == 1
    assert subscriptions[0].user_id == user.id
    assert subscriptions[0].plan_id == plan.id
    assert subscriptions[0].status == "active"
    assert paid.subscription_id == subscriptions[0].id
    assert paid_again.subscription_id == subscriptions[0].id


def test_handle_zpay_notify_activates_paid_subscription_order_missing_subscription(
    monkeypatch,
):
    db = make_session()
    user = make_user(db)
    plan = make_plan(db, price_cents=1990)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    service = PaymentService(PaymentRepository(db))
    subscription_service = SubscriptionService(SubscriptionRepository(db))
    order = PaymentOrderRow(
        id=uuid.uuid4(),
        order_no="P202605100003",
        user_id=user.id,
        user_public_id=user.user_id,
        provider="zpay",
        provider_trade_no="202605102200003",
        plan_id=plan.id,
        order_kind="subscription",
        subject=plan.name,
        amount_cents=plan.price_cents,
        pay_type="alipay",
        status="paid",
    )
    db.add(order)
    db.commit()
    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200003",
            "out_trade_no": "P202605100003",
            "type": "alipay",
            "name": plan.name,
            "money": "19.90",
            "trade_status": "TRADE_SUCCESS",
            "param": f"user_id={user.user_id};plan_id={plan.id}",
        },
        "secret",
    )

    paid = service.handle_zpay_notify(
        callback,
        subscription_service=subscription_service,
        user=user,
    )
    paid_again = service.handle_zpay_notify(
        callback,
        subscription_service=subscription_service,
        user=user,
    )

    subscriptions = db.query(UserSubscriptionRow).all()
    assert paid.order_no == order.order_no
    assert paid_again.order_no == order.order_no
    assert len(subscriptions) == 1
    assert subscriptions[0].user_id == user.id
    assert subscriptions[0].plan_id == plan.id
    assert subscriptions[0].status == "active"
    assert paid.subscription_id == subscriptions[0].id
    assert paid_again.subscription_id == subscriptions[0].id


def test_handle_zpay_notify_skips_replay_for_already_activated_subscription_order(
    monkeypatch,
):
    db = make_session()
    user = make_user(db)
    old_plan = make_plan(db, code="old", name="Old Plan", price_cents=990)
    new_plan = make_plan(db, code="new", name="New Plan", price_cents=2990)
    subscription_service = SubscriptionService(SubscriptionRepository(db))
    old_subscription = subscription_service.activate_subscription(user, old_plan)
    current_subscription = subscription_service.activate_subscription(user, new_plan)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    service = PaymentService(PaymentRepository(db))
    order = PaymentOrderRow(
        id=uuid.uuid4(),
        order_no="P202605100004",
        user_id=user.id,
        user_public_id=user.user_id,
        provider="zpay",
        provider_trade_no="202605102200004",
        plan_id=old_plan.id,
        order_kind="subscription",
        subscription_id=old_subscription.id,
        subject=old_plan.name,
        amount_cents=old_plan.price_cents,
        pay_type="alipay",
        status="paid",
    )
    db.add(order)
    db.commit()
    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200004",
            "out_trade_no": "P202605100004",
            "type": "alipay",
            "name": old_plan.name,
            "money": "9.90",
            "trade_status": "TRADE_SUCCESS",
            "param": f"user_id={user.user_id};plan_id={old_plan.id}",
        },
        "secret",
    )

    paid = service.handle_zpay_notify(
        callback,
        subscription_service=subscription_service,
        user=user,
    )

    subscriptions = db.query(UserSubscriptionRow).all()
    active_subscriptions = [
        subscription
        for subscription in subscriptions
        if subscription.status == "active"
    ]
    db.refresh(current_subscription)
    db.refresh(old_subscription)

    assert paid.subscription_id == old_subscription.id
    assert len(subscriptions) == 2
    assert len(active_subscriptions) == 1
    assert active_subscriptions[0].id == current_subscription.id
    assert active_subscriptions[0].plan_id == new_plan.id
    assert old_subscription.status == "ended"


def test_handle_zpay_notify_rolls_back_payment_when_subscription_activation_fails(
    monkeypatch,
):
    db = make_session()
    user = make_user(db)
    plan = make_plan(db, price_cents=1990)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    service = PaymentService(PaymentRepository(db))
    subscription_service = SubscriptionService(SubscriptionRepository(db))
    order = PaymentOrderRow(
        id=uuid.uuid4(),
        order_no="P202605100005",
        user_id=user.id,
        user_public_id=user.user_id,
        provider="zpay",
        plan_id=plan.id,
        order_kind="subscription",
        subject=plan.name,
        amount_cents=plan.price_cents,
        pay_type="alipay",
        status="pending",
    )
    db.add(order)
    db.commit()
    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200005",
            "out_trade_no": "P202605100005",
            "type": "alipay",
            "name": plan.name,
            "money": "19.90",
            "trade_status": "TRADE_SUCCESS",
            "param": f"user_id={user.user_id};plan_id={plan.id}",
        },
        "secret",
    )

    def fail_activation(*args, **kwargs):
        raise RuntimeError("activation failed")

    subscription_service.activate_subscription = fail_activation

    with pytest.raises(RuntimeError, match="activation failed"):
        service.handle_zpay_notify(
            callback,
            subscription_service=subscription_service,
            user=user,
        )

    db.refresh(order)
    assert order.status == "pending"
    assert order.provider_trade_no is None
    assert order.subscription_id is None
    assert db.query(UserSubscriptionRow).count() == 0


def test_handle_zpay_notify_rejects_tampered_amount(monkeypatch):
    db = make_session()
    user = make_user(db)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    order = PaymentOrderRow(
        id=uuid.uuid4(),
        order_no="P202605100001",
        user_id=user.id,
        user_public_id=user.user_id,
        provider="zpay",
        subject="Image credits",
        amount_cents=990,
        pay_type="alipay",
        status="pending",
    )
    db.add(order)
    db.commit()
    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200001",
            "out_trade_no": "P202605100001",
            "type": "alipay",
            "name": "Image credits",
            "money": "0.01",
            "trade_status": "TRADE_SUCCESS",
        },
        "secret",
    )

    with pytest.raises(PaymentServiceError) as error:
        PaymentService(PaymentRepository(db)).handle_zpay_notify(callback)

    db.refresh(order)
    assert str(error.value) == "Payment amount mismatch."
    assert order.status == "pending"
