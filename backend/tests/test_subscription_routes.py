import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.auth_dependencies import get_current_user
from app.db import Base, get_db_session
from app.main import app
from app.subscription_models import SubscriptionPlanRow
from app.user_models import UserRow


client = TestClient(app)


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def make_user(db: Session, *, is_admin: bool = False) -> UserRow:
    user = UserRow(
        user_id="U00000001" if not is_admin else "U00000002",
        email="admin@example.com" if is_admin else "user@example.com",
        username="admin" if is_admin else "user",
        password_hash="hash",
        is_admin=is_admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def add_plan(
    db: Session,
    *,
    code: str,
    name: str,
    price_cents: int,
    daily: int,
    monthly: int,
    is_active: bool = True,
    is_default: bool = False,
    sort_order: int = 0,
) -> SubscriptionPlanRow:
    plan = SubscriptionPlanRow(
        id=uuid.uuid4(),
        code=code,
        name=name,
        description=f"{name} plan",
        price_cents=price_cents,
        daily_image_limit=daily,
        monthly_image_limit=monthly,
        is_active=is_active,
        is_default=is_default,
        sort_order=sort_order,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def make_client_with_user(user: UserRow, db: Session) -> TestClient:
    def override_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user] = override_user
    return client


def cleanup_overrides() -> None:
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_authenticated_user_can_list_active_subscription_plans():
    db = make_session()
    user = make_user(db)
    add_plan(
        db,
        code="free",
        name="Free",
        price_cents=0,
        daily=1,
        monthly=5,
        is_default=True,
    )
    add_plan(
        db,
        code="archived",
        name="Archived",
        price_cents=990,
        daily=5,
        monthly=50,
        is_active=False,
    )
    test_client = make_client_with_user(user, db)
    try:
        response = test_client.get("/api/subscription/plans")
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert [plan["code"] for plan in response.json()["plans"]] == ["free"]


def test_subscription_me_returns_current_user_entitlement():
    db = make_session()
    user = make_user(db)
    add_plan(
        db,
        code="free",
        name="Free",
        price_cents=0,
        daily=3,
        monthly=30,
        is_default=True,
    )
    test_client = make_client_with_user(user, db)
    try:
        response = test_client.get("/api/subscription/me")
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    entitlement = response.json()["entitlement"]
    assert entitlement["plan"]["code"] == "free"
    assert entitlement["dailyLimit"] == 3
    assert entitlement["dailyRemaining"] == 3


def test_admin_can_create_subscription_plan_and_regular_user_gets_403():
    db = make_session()
    regular_user = make_user(db)
    admin_user = make_user(db, is_admin=True)
    payload = {
        "code": "pro",
        "name": "Pro",
        "description": "For teams",
        "price": "19.90",
        "dailyImageLimit": 20,
        "monthlyImageLimit": 500,
        "isActive": True,
        "isDefault": True,
        "sortOrder": 10,
    }

    regular_client = make_client_with_user(regular_user, db)
    try:
        forbidden = regular_client.post("/api/admin/subscription/plans", json=payload)
    finally:
        cleanup_overrides()

    admin_client = make_client_with_user(admin_user, db)
    try:
        created = admin_client.post("/api/admin/subscription/plans", json=payload)
    finally:
        cleanup_overrides()

    assert forbidden.status_code == 403
    assert created.status_code == 200
    plan = created.json()["plan"]
    assert plan["code"] == "pro"
    assert plan["price"] == "19.90"
    assert plan["isDefault"] is True


def test_admin_create_subscription_plan_returns_json_error_for_invalid_payload():
    db = make_session()
    admin_user = make_user(db, is_admin=True)
    test_client = make_client_with_user(admin_user, db)
    try:
        response = test_client.post(
            "/api/admin/subscription/plans",
            json={
                "name": "Pro",
                "price": "19.90",
                "dailyImageLimit": 6,
                "monthlyImageLimit": 5,
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 400
    assert "error" in response.json()


def test_admin_create_subscription_plan_rejects_duplicate_code_with_json_error():
    db = make_session()
    admin_user = make_user(db, is_admin=True)
    payload = {
        "code": "pro",
        "name": "Pro",
        "description": "For teams",
        "price": "19.90",
        "dailyImageLimit": 20,
        "monthlyImageLimit": 500,
    }
    test_client = make_client_with_user(admin_user, db)
    try:
        first_response = test_client.post(
            "/api/admin/subscription/plans",
            json=payload,
        )
        duplicate_response = test_client.post(
            "/api/admin/subscription/plans",
            json={**payload, "name": "Pro Duplicate"},
        )
    finally:
        cleanup_overrides()

    assert first_response.status_code == 200
    assert duplicate_response.status_code == 400
    assert duplicate_response.json() == {"error": "套餐代码已存在。"}


def test_admin_can_list_all_subscription_plans_including_inactive():
    db = make_session()
    admin_user = make_user(db, is_admin=True)
    add_plan(
        db,
        code="free",
        name="Free",
        price_cents=0,
        daily=1,
        monthly=5,
        is_default=True,
    )
    add_plan(
        db,
        code="archived",
        name="Archived",
        price_cents=990,
        daily=5,
        monthly=50,
        is_active=False,
    )
    test_client = make_client_with_user(admin_user, db)
    try:
        response = test_client.get("/api/admin/subscription/plans")
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert [plan["code"] for plan in response.json()["plans"]] == [
        "free",
        "archived",
    ]
