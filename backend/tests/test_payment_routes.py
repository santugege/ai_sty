from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth_dependencies import get_current_user
from app.db import Base, get_db_session
from app.main import app
from app.payment_models import PaymentOrderRow
from app.subscription_models import SubscriptionPlanRow, UserSubscriptionRow
from app.user_models import UserRow
from app.zpay_client import signed_params


client = TestClient(app)


def make_client(monkeypatch):
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    monkeypatch.setenv("ZPAY_SUBMIT_URL", "https://zpayz.cn/submit.php")
    monkeypatch.setenv("BACKEND_PUBLIC_ORIGIN", "https://api.example.com")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    user = UserRow(
        user_id="U00000001",
        email="tester@example.com",
        username="tester",
        password_hash="hash",
        is_admin=True,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    def override_db():
        yield session

    def override_user():
        return user

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return client, session


def cleanup_overrides():
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)


def make_plan(
    db: Session,
    *,
    code: str = "pro",
    name: str = "Pro Plan",
    price_cents: int = 1990,
    is_active: bool = True,
) -> SubscriptionPlanRow:
    plan = SubscriptionPlanRow(
        code=code,
        name=name,
        description="Image quota.",
        price_cents=price_cents,
        daily_image_limit=20,
        monthly_image_limit=500,
        is_active=is_active,
        is_default=False,
        sort_order=10,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_create_zpay_payment_order_route_requires_authentication():
    response = client.post(
        "/api/payments/zpay/orders",
        json={"subject": "Image credits", "amount": "9.90", "payType": "alipay"},
    )

    assert response.status_code == 401


def test_create_zpay_payment_order_route_returns_order_and_payment_url(monkeypatch):
    test_client, session = make_client(monkeypatch)
    try:
        response = test_client.post(
            "/api/payments/zpay/orders",
            json={"subject": "Image credits", "amount": "9.90", "payType": "alipay"},
        )
    finally:
        cleanup_overrides()

    payload = response.json()
    parsed = urlsplit(payload["order"]["paymentUrl"])
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    stored = session.query(PaymentOrderRow).one()

    assert response.status_code == 200
    assert payload["order"]["orderNo"] == stored.order_no
    assert payload["order"]["status"] == "pending"
    assert payload["order"]["amount"] == "9.90"
    assert payload["order"]["payType"] == "alipay"
    assert query["out_trade_no"] == stored.order_no
    assert query["sign_type"] == "MD5"


def test_create_subscription_zpay_order_route_returns_plan_price_payment_url(
    monkeypatch,
):
    test_client, session = make_client(monkeypatch)
    plan = make_plan(session, price_cents=1990)
    try:
        response = test_client.post(
            "/api/payments/zpay/subscription-orders",
            json={"planId": str(plan.id), "payType": "alipay"},
        )
    finally:
        cleanup_overrides()

    payload = response.json()
    parsed = urlsplit(payload["order"]["paymentUrl"])
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    stored = session.query(PaymentOrderRow).one()

    assert response.status_code == 200
    assert payload["order"]["orderNo"] == stored.order_no
    assert payload["order"]["subject"] == "Pro Plan"
    assert payload["order"]["amount"] == "19.90"
    assert payload["order"]["status"] == "pending"
    assert stored.plan_id == plan.id
    assert stored.order_kind == "subscription"
    assert query["out_trade_no"] == stored.order_no
    assert query["name"] == "Pro Plan"
    assert query["money"] == "19.90"


def test_create_subscription_zpay_order_route_activates_free_plan_without_payment(
    monkeypatch,
):
    test_client, session = make_client(monkeypatch)
    plan = make_plan(
        session,
        code="free",
        name="Free Plan",
        price_cents=0,
    )
    try:
        response = test_client.post(
            "/api/payments/zpay/subscription-orders",
            json={"planId": str(plan.id), "payType": "alipay"},
        )
    finally:
        cleanup_overrides()

    payload = response.json()
    stored = session.query(PaymentOrderRow).one()
    subscription = session.query(UserSubscriptionRow).one()

    assert response.status_code == 200
    assert payload["order"]["paymentUrl"] is None
    assert payload["order"]["status"] == "paid"
    assert payload["order"]["subject"] == "Free Plan"
    assert payload["order"]["amount"] == "0.00"
    assert stored.plan_id == plan.id
    assert stored.order_kind == "subscription"
    assert stored.status == "paid"
    assert subscription.plan_id == plan.id
    assert subscription.status == "active"


def test_create_subscription_zpay_order_route_reuses_active_free_subscription(
    monkeypatch,
):
    test_client, session = make_client(monkeypatch)
    plan = make_plan(
        session,
        code="free",
        name="Free Plan",
        price_cents=0,
    )
    try:
        first_response = test_client.post(
            "/api/payments/zpay/subscription-orders",
            json={"planId": str(plan.id), "payType": "alipay"},
        )
        second_response = test_client.post(
            "/api/payments/zpay/subscription-orders",
            json={"planId": str(plan.id), "payType": "alipay"},
        )
    finally:
        cleanup_overrides()

    orders = session.query(PaymentOrderRow).all()
    subscriptions = session.query(UserSubscriptionRow).all()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(orders) == 1
    assert first_response.json()["order"]["orderNo"] == orders[0].order_no
    assert second_response.json()["order"]["orderNo"] == orders[0].order_no
    assert len(subscriptions) == 1
    assert subscriptions[0].plan_id == plan.id
    assert subscriptions[0].status == "active"


def test_zpay_notify_route_activates_subscription_order_once_and_is_idempotent(
    monkeypatch,
):
    test_client, session = make_client(monkeypatch)
    plan = make_plan(session, price_cents=1990)
    try:
        create_response = test_client.post(
            "/api/payments/zpay/subscription-orders",
            json={"planId": str(plan.id), "payType": "alipay"},
        )
        order_no = create_response.json()["order"]["orderNo"]
        callback = signed_params(
            {
                "pid": "merchant-1",
                "trade_no": "202605102200002",
                "out_trade_no": order_no,
                "type": "alipay",
                "name": "Pro Plan",
                "money": "19.90",
                "trade_status": "TRADE_SUCCESS",
                "param": f"user_id=U00000001;plan_id={plan.id}",
            },
            "secret",
        )

        notify_response = test_client.get(
            "/api/payments/zpay/notify",
            params=callback,
        )
        repeat_response = test_client.get(
            "/api/payments/zpay/notify",
            params=callback,
        )
    finally:
        cleanup_overrides()

    stored = session.query(PaymentOrderRow).one()
    subscriptions = session.query(UserSubscriptionRow).all()

    assert notify_response.status_code == 200
    assert notify_response.text == "success"
    assert repeat_response.status_code == 200
    assert repeat_response.text == "success"
    assert stored.status == "paid"
    assert stored.provider_trade_no == "202605102200002"
    assert stored.subscription_id == subscriptions[0].id
    assert len(subscriptions) == 1
    assert subscriptions[0].plan_id == plan.id
    assert subscriptions[0].status == "active"


def test_zpay_notify_route_marks_order_paid_and_returns_success(monkeypatch):
    test_client, session = make_client(monkeypatch)
    try:
        create_response = test_client.post(
            "/api/payments/zpay/orders",
            json={"subject": "Image credits", "amount": "9.90", "payType": "alipay"},
        )
        order_no = create_response.json()["order"]["orderNo"]
        callback = signed_params(
            {
                "pid": "merchant-1",
                "trade_no": "202605102200001",
                "out_trade_no": order_no,
                "type": "alipay",
                "name": "Image credits",
                "money": "9.90",
                "trade_status": "TRADE_SUCCESS",
                "param": "user_id=U00000001",
            },
            "secret",
        )

        notify_response = test_client.get(
            "/api/payments/zpay/notify",
            params=callback,
        )
    finally:
        cleanup_overrides()

    stored = session.query(PaymentOrderRow).one()
    assert notify_response.status_code == 200
    assert notify_response.text == "success"
    assert stored.status == "paid"
    assert stored.provider_trade_no == "202605102200001"
