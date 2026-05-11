import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.subscription_models import SubscriptionPlanRow, UserSubscriptionRow
from app.subscription_repository import SubscriptionRepository
from app.subscription_schemas import SubscriptionPlanInput
from app.subscription_service import (
    SubscriptionLimitError,
    SubscriptionService,
    SubscriptionServiceError,
    cents_to_yuan,
    yuan_to_cents,
)
from app.user_models import UserRow


def make_session() -> Session:
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
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_plan(
    db: Session,
    *,
    code: str = "free",
    name: str = "Free",
    price_cents: int = 0,
    daily: int = 5,
    monthly: int = 50,
    is_default: bool = True,
    is_active: bool = True,
) -> SubscriptionPlanRow:
    plan = SubscriptionPlanRow(
        id=uuid.uuid4(),
        code=code,
        name=name,
        description="plan",
        price_cents=price_cents,
        daily_image_limit=daily,
        monthly_image_limit=monthly,
        is_default=is_default,
        is_active=is_active,
        sort_order=0,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def subscription_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def make_service(db: Session) -> SubscriptionService:
    return SubscriptionService(SubscriptionRepository(db))


def test_yuan_to_cents_and_cents_to_yuan():
    assert yuan_to_cents("19.90") == 1990
    assert cents_to_yuan(1990) == "19.90"


def test_yuan_to_cents_rejects_invalid_values():
    with pytest.raises(ValueError):
        yuan_to_cents("-1")
    with pytest.raises(ValueError):
        yuan_to_cents("1.001")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_yuan_to_cents_rejects_non_finite_values(value):
    with pytest.raises(ValueError):
        yuan_to_cents(value)


def test_default_entitlement_uses_active_default_free_plan():
    db = make_session()
    user = make_user(db)
    add_plan(db, daily=3, monthly=30)

    entitlement = make_service(db).get_entitlement(user)

    assert entitlement.plan.code == "free"
    assert entitlement.dailyLimit == 3
    assert entitlement.monthlyLimit == 30
    assert entitlement.todayUsed == 0
    assert entitlement.monthUsed == 0


def test_fallback_free_entitlement_when_no_plan_exists():
    db = make_session()
    user = make_user(db)

    entitlement = make_service(db).get_entitlement(user)

    assert entitlement.plan.code == "free"
    assert entitlement.dailyLimit == 1
    assert entitlement.monthlyLimit == 5


def test_quota_check_rejects_when_daily_limit_is_insufficient():
    db = make_session()
    user = make_user(db)
    plan = add_plan(db, daily=3, monthly=50)
    service = make_service(db)
    service.record_usage(user=user, plan=plan, subscription=None, image_count=2)

    with pytest.raises(SubscriptionLimitError) as error:
        service.ensure_can_generate(user=user, requested_images=2)

    assert error.value.status_code == 402
    assert error.value.payload["errorCode"] == "SUBSCRIPTION_LIMIT_REACHED"
    assert error.value.payload["usage"]["dailyRemaining"] == 1


def test_quota_check_rejects_when_monthly_limit_is_insufficient():
    db = make_session()
    user = make_user(db)
    plan = add_plan(db, daily=3, monthly=3)
    service = make_service(db)
    service.record_usage(user=user, plan=plan, subscription=None, image_count=3)

    with pytest.raises(SubscriptionLimitError) as error:
        service.ensure_can_generate(user=user, requested_images=1)

    assert error.value.status_code == 402
    assert error.value.payload["errorCode"] == "SUBSCRIPTION_LIMIT_REACHED"
    assert error.value.payload["usage"]["monthlyRemaining"] == 0


def test_quota_check_allows_and_records_successful_usage():
    db = make_session()
    user = make_user(db)
    add_plan(db, daily=5, monthly=50)
    service = make_service(db)

    entitlement = service.ensure_can_generate(user=user, requested_images=4)
    service.record_generation(user=user, entitlement=entitlement, image_count=4)
    refreshed = service.get_entitlement(user)

    assert refreshed.todayUsed == 4
    assert refreshed.monthUsed == 4


def test_quota_check_rejects_non_positive_requested_images():
    db = make_session()
    user = make_user(db)
    add_plan(db)
    service = make_service(db)

    with pytest.raises(SubscriptionServiceError):
        service.ensure_can_generate(user=user, requested_images=0)

    with pytest.raises(SubscriptionServiceError):
        service.ensure_can_generate(user=user, requested_images=-1)


def test_record_usage_rejects_non_positive_image_count():
    db = make_session()
    user = make_user(db)
    plan = add_plan(db)
    service = make_service(db)

    with pytest.raises(SubscriptionServiceError):
        service.record_usage(user=user, plan=plan, subscription=None, image_count=0)

    with pytest.raises(SubscriptionServiceError):
        service.record_usage(user=user, plan=plan, subscription=None, image_count=-2)

    entitlement = service.get_entitlement(user)
    assert entitlement.todayUsed == 0
    assert entitlement.dailyRemaining == 5


def test_activate_subscription_ends_existing_active_subscription():
    db = make_session()
    user = make_user(db)
    free = add_plan(db)
    pro = add_plan(
        db,
        code="pro",
        name="Pro",
        price_cents=1990,
        daily=20,
        monthly=500,
        is_default=False,
    )
    service = make_service(db)
    old = service.activate_subscription(user=user, plan=free)

    activated = service.activate_subscription(user=user, plan=pro)

    db.refresh(old)
    assert old.status == "ended"
    assert activated.status == "active"
    assert activated.ends_at > datetime.now(timezone.utc) + timedelta(days=27)


def test_activate_subscription_does_not_end_future_subscription():
    db = make_session()
    user = make_user(db)
    free = add_plan(db)
    pro = add_plan(
        db,
        code="pro",
        name="Pro",
        price_cents=1990,
        daily=20,
        monthly=500,
        is_default=False,
    )
    now = datetime.now(timezone.utc)
    future = UserSubscriptionRow(
        id=uuid.uuid4(),
        user_id=user.id,
        plan_id=free.id,
        status="active",
        starts_at=now + timedelta(days=3),
        ends_at=now + timedelta(days=33),
    )
    db.add(future)
    db.commit()
    service = make_service(db)

    service.activate_subscription(user=user, plan=pro)

    db.refresh(future)
    assert future.status == "active"
    assert subscription_time(future.starts_at) > datetime.now(timezone.utc)


def test_subscription_plan_input_accepts_valid_admin_plan():
    plan = SubscriptionPlanInput(
        code="pro",
        name="Pro",
        price="19.90",
        dailyImageLimit=20,
        monthlyImageLimit=500,
    )

    assert plan.code == "pro"
    assert plan.name == "Pro"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "name": " ",
            "price": "19.90",
            "dailyImageLimit": 1,
            "monthlyImageLimit": 5,
        },
        {
            "code": " ",
            "name": "Pro",
            "price": "19.90",
            "dailyImageLimit": 1,
            "monthlyImageLimit": 5,
        },
        {
            "name": "Pro",
            "price": "-1",
            "dailyImageLimit": 1,
            "monthlyImageLimit": 5,
        },
        {
            "name": "Pro",
            "price": "1.001",
            "dailyImageLimit": 1,
            "monthlyImageLimit": 5,
        },
        {
            "name": "Pro",
            "price": "NaN",
            "dailyImageLimit": 1,
            "monthlyImageLimit": 5,
        },
        {
            "name": "Pro",
            "price": "Infinity",
            "dailyImageLimit": 1,
            "monthlyImageLimit": 5,
        },
        {
            "name": "Pro",
            "price": "-Infinity",
            "dailyImageLimit": 1,
            "monthlyImageLimit": 5,
        },
        {
            "name": "Pro",
            "price": "19.90",
            "dailyImageLimit": 0,
            "monthlyImageLimit": 5,
        },
        {
            "name": "Pro",
            "price": "19.90",
            "dailyImageLimit": 6,
            "monthlyImageLimit": 5,
        },
    ],
)
def test_subscription_plan_input_rejects_invalid_admin_plan(payload):
    with pytest.raises(ValidationError):
        SubscriptionPlanInput(**payload)
