# Subscription Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add administrator-managed monthly subscription plans with daily/monthly image quotas, default Free entitlement, ZPAY subscription payments, and quota prompts during image generation.

**Architecture:** Add subscription plan, user subscription, and image usage persistence in FastAPI/SQLAlchemy. Extend the existing ZPAY payment order flow so paid subscription orders activate plans on callback. Enforce quota inside `/api/images/generate` after request validation and before OpenAI calls, then record usage only after successful generation. The Next.js frontend gets admin plan management, dynamic billing plans, and a quota modal in the product workbench.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, Next.js App Router, React, TypeScript, Tailwind CSS, Node test runner.

---

## File Structure

Backend files:

- Create `backend/app/subscription_models.py`: `SubscriptionPlanRow`, `UserSubscriptionRow`, `ImageUsageEventRow`.
- Create `backend/app/subscription_repository.py`: persistence helpers for plans, subscriptions, and usage.
- Create `backend/app/subscription_schemas.py`: request/response DTOs for plans, entitlement, quota errors.
- Create `backend/app/subscription_service.py`: plan validation, default Free fallback, entitlement lookup, quota checks, usage recording, subscription activation.
- Create `backend/alembic/versions/20260510_0007_subscriptions.py`: subscription tables and `payment_orders` plan/order-kind columns.
- Create `backend/tests/test_subscription_models.py`.
- Create `backend/tests/test_subscription_service.py`.
- Create `backend/tests/test_subscription_routes.py`.
- Modify `backend/app/payment_models.py`: add `plan_id` and `order_kind`.
- Modify `backend/app/payment_service.py`: add subscription order creation and activation hook.
- Modify `backend/app/payment_schemas.py`: add `CreateSubscriptionZpayOrderRequest`.
- Modify `backend/app/main.py`: add admin/user subscription routes, subscription order route, quota enforcement in image generation.
- Modify `backend/alembic/env.py`: import `subscription_models`.
- Modify `backend/tests/test_payment_models.py`, `backend/tests/test_payment_service.py`, `backend/tests/test_payment_routes.py`, `backend/tests/test_main.py`, `backend/tests/test_user_models.py`.

Frontend files:

- Create `frontend/src/lib/subscription-api.ts`: user/admin subscription API client.
- Create `frontend/src/app/admin/subscriptions/page.tsx`: admin plan management UI.
- Modify `frontend/src/app/billing/page.tsx`: load active plans from backend and create subscription ZPAY orders.
- Modify `frontend/src/lib/payment-api.ts`: add subscription order request.
- Modify `frontend/src/lib/image-api.ts`: preserve subscription limit payload.
- Modify `frontend/src/components/product-workbench.tsx`: show subscription modal when quota is insufficient.
- Modify `frontend/src/components/app-nav.tsx`: add admin subscription management entry.
- Create `frontend/tests/subscription-flow.test.mjs`.
- Modify `frontend/tests/payment-flow.test.mjs` and `frontend/tests/auth-flow.test.mjs`.

---

### Task 1: Subscription Models And Migration

**Files:**
- Create: `backend/tests/test_subscription_models.py`
- Create: `backend/app/subscription_models.py`
- Create: `backend/alembic/versions/20260510_0007_subscriptions.py`
- Modify: `backend/alembic/env.py`
- Modify: `backend/app/payment_models.py`
- Modify: `backend/tests/test_payment_models.py`
- Modify: `backend/tests/test_user_models.py`

- [ ] **Step 1: Write failing subscription model tests**

Create `backend/tests/test_subscription_models.py`:

```python
from pathlib import Path

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


def test_subscriptions_migration_exists_and_seeds_free_plan():
    migration = Path(
        "backend/alembic/versions/20260510_0007_subscriptions.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260510_0007"' in migration
    assert 'down_revision = "20260510_0006"' in migration
    assert 'op.create_table("subscription_plans"' in migration
    assert 'op.create_table("user_subscriptions"' in migration
    assert 'op.create_table("image_usage_events"' in migration
    assert 'op.add_column("payment_orders", sa.Column("plan_id"' in migration
    assert 'op.add_column("payment_orders", sa.Column("order_kind"' in migration
    assert '"free"' in migration
    assert "Free" in migration
    assert "daily_image_limit" in migration
    assert "monthly_image_limit" in migration
    assert 'op.drop_table("image_usage_events")' in migration
    assert 'op.drop_table("user_subscriptions")' in migration
    assert 'op.drop_table("subscription_plans")' in migration
```

- [ ] **Step 2: Update payment model test for subscription linkage**

Append to `backend/tests/test_payment_models.py`:

```python
def test_payment_order_can_reference_subscription_plan():
    assert {"plan_id", "order_kind"} <= set(PaymentOrderRow.__table__.columns.keys())
```

- [ ] **Step 3: Run model tests red**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_subscription_models.py backend\tests\test_payment_models.py -q"
```

Expected: FAIL because `app.subscription_models` does not exist and `PaymentOrderRow` lacks `plan_id`/`order_kind`.

- [ ] **Step 4: Implement subscription models**

Create `backend/app/subscription_models.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SubscriptionPlanRow(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    daily_image_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_image_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class UserSubscriptionRow(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subscription_plans.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class ImageUsageEventRow(Base):
    __tablename__ = "image_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user_subscriptions.id"), nullable=True, index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("subscription_plans.id"), nullable=False, index=True
    )
    image_count: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="image_generate")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, index=True
    )
```

- [ ] **Step 5: Extend `PaymentOrderRow`**

In `backend/app/payment_models.py`, add imports:

```python
from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid
```

Add columns to `PaymentOrderRow` after `provider_trade_no`:

```python
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("subscription_plans.id"), nullable=True, index=True
    )
    order_kind: Mapped[str] = mapped_column(Text, nullable=False, default="payment")
```

- [ ] **Step 6: Import subscription models in Alembic env**

Change `backend/alembic/env.py`:

```python
from app import agent_models, payment_models, subscription_models, user_models  # noqa: F401
```

- [ ] **Step 7: Add migration**

Create `backend/alembic/versions/20260510_0007_subscriptions.py`:

```python
"""create subscription tables

Revision ID: 20260510_0007
Revises: 20260510_0006
Create Date: 2026-05-10 00:07:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260510_0007"
down_revision = "20260510_0006"
branch_labels = None
depends_on = None


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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_plans_code", "subscription_plans", ["code"], unique=True)
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
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"], unique=False)
    op.create_index("ix_user_subscriptions_plan_id", "user_subscriptions", ["plan_id"], unique=False)
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_usage_events_user_id", "image_usage_events", ["user_id"], unique=False)
    op.create_index("ix_image_usage_events_plan_id", "image_usage_events", ["plan_id"], unique=False)
    op.create_index("ix_image_usage_events_subscription_id", "image_usage_events", ["subscription_id"], unique=False)
    op.create_index("ix_image_usage_events_created_at", "image_usage_events", ["created_at"], unique=False)
    op.add_column("payment_orders", sa.Column("plan_id", sa.Uuid(), nullable=True))
    op.add_column("payment_orders", sa.Column("order_kind", sa.Text(), nullable=False, server_default="payment"))
    op.create_index("ix_payment_orders_plan_id", "payment_orders", ["plan_id"], unique=False)
    op.create_foreign_key(
        "fk_payment_orders_plan_id_subscription_plans",
        "payment_orders",
        "subscription_plans",
        ["plan_id"],
        ["id"],
    )
    op.execute(
        sa.text(
            """
            insert into subscription_plans (
                id, code, name, description, price_cents,
                daily_image_limit, monthly_image_limit, is_active, is_default,
                sort_order, created_at, updated_at
            ) values (
                gen_random_uuid(), 'free', 'Free', 'Default free image quota.',
                0, 5, 50, true, true, 0, now(), now()
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_payment_orders_plan_id_subscription_plans", "payment_orders", type_="foreignkey")
    op.drop_index("ix_payment_orders_plan_id", table_name="payment_orders")
    op.drop_column("payment_orders", "order_kind")
    op.drop_column("payment_orders", "plan_id")
    op.drop_index("ix_image_usage_events_created_at", table_name="image_usage_events")
    op.drop_index("ix_image_usage_events_subscription_id", table_name="image_usage_events")
    op.drop_index("ix_image_usage_events_plan_id", table_name="image_usage_events")
    op.drop_index("ix_image_usage_events_user_id", table_name="image_usage_events")
    op.drop_table("image_usage_events")
    op.drop_index("ix_user_subscriptions_plan_id", table_name="user_subscriptions")
    op.drop_index("ix_user_subscriptions_user_id", table_name="user_subscriptions")
    op.drop_table("user_subscriptions")
    op.drop_index("ix_subscription_plans_code", table_name="subscription_plans")
    op.drop_table("subscription_plans")
```

Note: if PostgreSQL lacks `gen_random_uuid()`, replace the seed with a static UUID string in implementation. Tests only require the migration shape.

- [ ] **Step 8: Update Alembic head test**

In `backend/tests/test_user_models.py`, change:

```python
assert "20260510_0006" in result.stdout
```

to:

```python
assert "20260510_0007" in result.stdout
```

- [ ] **Step 9: Run model tests green**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_subscription_models.py backend\tests\test_payment_models.py backend\tests\test_user_models.py -q"
```

Expected: PASS.

---

### Task 2: Subscription Service And Entitlement Logic

**Files:**
- Create: `backend/tests/test_subscription_service.py`
- Create: `backend/app/subscription_repository.py`
- Create: `backend/app/subscription_schemas.py`
- Create: `backend/app/subscription_service.py`

- [ ] **Step 1: Write failing service tests**

Create `backend/tests/test_subscription_service.py`:

```python
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.subscription_models import SubscriptionPlanRow
from app.subscription_repository import SubscriptionRepository
from app.subscription_service import (
    SubscriptionLimitError,
    SubscriptionService,
    cents_to_yuan,
    yuan_to_cents,
)
from app.user_models import UserRow


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
    code="free",
    name="Free",
    price_cents=0,
    daily=5,
    monthly=50,
    is_default=True,
    is_active=True,
):
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


def test_yuan_to_cents_and_cents_to_yuan():
    assert yuan_to_cents("19.90") == 1990
    assert cents_to_yuan(1990) == "19.90"


def test_yuan_to_cents_rejects_invalid_values():
    with pytest.raises(ValueError):
        yuan_to_cents("-1")
    with pytest.raises(ValueError):
        yuan_to_cents("1.001")


def test_default_entitlement_uses_active_default_free_plan():
    db = make_session()
    user = make_user(db)
    add_plan(db, daily=3, monthly=30)

    entitlement = SubscriptionService(SubscriptionRepository(db)).get_entitlement(user)

    assert entitlement.plan.code == "free"
    assert entitlement.dailyLimit == 3
    assert entitlement.monthlyLimit == 30
    assert entitlement.todayUsed == 0
    assert entitlement.monthUsed == 0


def test_fallback_free_entitlement_when_no_plan_exists():
    db = make_session()
    user = make_user(db)

    entitlement = SubscriptionService(SubscriptionRepository(db)).get_entitlement(user)

    assert entitlement.plan.code == "free"
    assert entitlement.dailyLimit == 1
    assert entitlement.monthlyLimit == 5


def test_quota_check_rejects_when_daily_limit_is_insufficient():
    db = make_session()
    user = make_user(db)
    plan = add_plan(db, daily=3, monthly=50)
    service = SubscriptionService(SubscriptionRepository(db))
    service.record_usage(user=user, plan=plan, subscription=None, image_count=2)

    with pytest.raises(SubscriptionLimitError) as error:
        service.ensure_can_generate(user=user, requested_images=2)

    assert error.value.payload["errorCode"] == "SUBSCRIPTION_LIMIT_REACHED"
    assert error.value.payload["usage"]["dailyRemaining"] == 1


def test_quota_check_rejects_when_monthly_limit_is_insufficient():
    db = make_session()
    user = make_user(db)
    plan = add_plan(db, daily=10, monthly=3)
    service = SubscriptionService(SubscriptionRepository(db))
    service.record_usage(user=user, plan=plan, subscription=None, image_count=2)

    with pytest.raises(SubscriptionLimitError) as error:
        service.ensure_can_generate(user=user, requested_images=2)

    assert error.value.payload["usage"]["monthlyRemaining"] == 1


def test_quota_check_allows_and_records_successful_usage():
    db = make_session()
    user = make_user(db)
    add_plan(db, daily=5, monthly=50)
    service = SubscriptionService(SubscriptionRepository(db))

    entitlement = service.ensure_can_generate(user=user, requested_images=4)
    service.record_generation(user=user, entitlement=entitlement, image_count=4)
    refreshed = service.get_entitlement(user)

    assert refreshed.todayUsed == 4
    assert refreshed.monthUsed == 4


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
    service = SubscriptionService(SubscriptionRepository(db))
    old = service.activate_subscription(user=user, plan=free)

    activated = service.activate_subscription(user=user, plan=pro)

    db.refresh(old)
    assert old.status == "ended"
    assert activated.status == "active"
    assert activated.ends_at > datetime.now(timezone.utc) + timedelta(days=27)
```

- [ ] **Step 2: Run service tests red**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_subscription_service.py -q"
```

Expected: FAIL because repository/service/schemas do not exist.

- [ ] **Step 3: Implement subscription schemas**

Create `backend/app/subscription_schemas.py`:

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SubscriptionPlanDto(BaseModel):
    id: str
    code: str
    name: str
    description: str
    price: str
    dailyImageLimit: int
    monthlyImageLimit: int
    isActive: bool
    isDefault: bool
    sortOrder: int


class SubscriptionPlanListEnvelope(BaseModel):
    plans: list[SubscriptionPlanDto]


class SubscriptionPlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = None
    name: str
    description: str = ""
    price: str
    dailyImageLimit: int
    monthlyImageLimit: int
    isActive: bool = True
    isDefault: bool = False
    sortOrder: int = 0


class EntitlementDto(BaseModel):
    plan: SubscriptionPlanDto
    dailyLimit: int
    monthlyLimit: int
    todayUsed: int
    monthUsed: int
    dailyRemaining: int
    monthlyRemaining: int


class EntitlementEnvelope(BaseModel):
    entitlement: EntitlementDto


class SubscriptionLimitPayload(BaseModel):
    error: str
    errorCode: str
    usage: EntitlementDto
    plans: list[SubscriptionPlanDto]
```

- [ ] **Step 4: Implement repository**

Create `backend/app/subscription_repository.py`:

```python
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.subscription_models import (
    ImageUsageEventRow,
    SubscriptionPlanRow,
    UserSubscriptionRow,
)


class SubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_plans(self, include_inactive: bool = False) -> list[SubscriptionPlanRow]:
        statement = select(SubscriptionPlanRow).order_by(
            SubscriptionPlanRow.sort_order.asc(),
            SubscriptionPlanRow.price_cents.asc(),
            SubscriptionPlanRow.created_at.asc(),
        )
        if not include_inactive:
            statement = statement.where(SubscriptionPlanRow.is_active.is_(True))
        return list(self.db.scalars(statement))

    def get_plan(self, plan_id: uuid.UUID | str) -> SubscriptionPlanRow | None:
        try:
            parsed = plan_id if isinstance(plan_id, uuid.UUID) else uuid.UUID(str(plan_id))
        except ValueError:
            return None
        return self.db.get(SubscriptionPlanRow, parsed)

    def get_default_plan(self) -> SubscriptionPlanRow | None:
        return self.db.scalar(
            select(SubscriptionPlanRow).where(
                SubscriptionPlanRow.is_default.is_(True),
                SubscriptionPlanRow.is_active.is_(True),
            )
        )

    def save_plan(self, plan: SubscriptionPlanRow) -> SubscriptionPlanRow:
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def clear_default_plans(self) -> None:
        for plan in self.db.scalars(select(SubscriptionPlanRow)):
            plan.is_default = False
        self.db.flush()

    def get_active_subscription(
        self, user_id: uuid.UUID, now: datetime
    ) -> UserSubscriptionRow | None:
        return self.db.scalar(
            select(UserSubscriptionRow)
            .where(
                UserSubscriptionRow.user_id == user_id,
                UserSubscriptionRow.status == "active",
                UserSubscriptionRow.starts_at <= now,
                UserSubscriptionRow.ends_at > now,
            )
            .order_by(UserSubscriptionRow.starts_at.desc())
        )

    def list_active_subscriptions(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[UserSubscriptionRow]:
        return list(
            self.db.scalars(
                select(UserSubscriptionRow).where(
                    UserSubscriptionRow.user_id == user_id,
                    UserSubscriptionRow.status == "active",
                    UserSubscriptionRow.ends_at > now,
                )
            )
        )

    def save_subscription(self, subscription: UserSubscriptionRow) -> UserSubscriptionRow:
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def add_usage(self, event: ImageUsageEventRow) -> ImageUsageEventRow:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def usage_sum(self, user_id: uuid.UUID, start: datetime, end: datetime) -> int:
        return int(
            self.db.scalar(
                select(func.coalesce(func.sum(ImageUsageEventRow.image_count), 0)).where(
                    ImageUsageEventRow.user_id == user_id,
                    ImageUsageEventRow.created_at >= start,
                    ImageUsageEventRow.created_at < end,
                )
            )
            or 0
        )
```

- [ ] **Step 5: Implement service**

Create `backend/app/subscription_service.py` with the service API expected by the tests:

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from app.subscription_models import (
    ImageUsageEventRow,
    SubscriptionPlanRow,
    UserSubscriptionRow,
)
from app.subscription_repository import SubscriptionRepository
from app.subscription_schemas import (
    EntitlementDto,
    SubscriptionLimitPayload,
    SubscriptionPlanDto,
)
from app.user_models import UserRow


class SubscriptionServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class SubscriptionLimitError(SubscriptionServiceError):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__("Subscription quota reached.", status_code=402)
        self.payload = payload


@dataclass(frozen=True)
class Entitlement:
    plan: SubscriptionPlanDto
    subscription: UserSubscriptionRow | None
    plan_row: SubscriptionPlanRow
    dailyLimit: int
    monthlyLimit: int
    todayUsed: int
    monthUsed: int
    dailyRemaining: int
    monthlyRemaining: int

    def to_dto(self) -> EntitlementDto:
        return EntitlementDto(
            plan=self.plan,
            dailyLimit=self.dailyLimit,
            monthlyLimit=self.monthlyLimit,
            todayUsed=self.todayUsed,
            monthUsed=self.monthUsed,
            dailyRemaining=self.dailyRemaining,
            monthlyRemaining=self.monthlyRemaining,
        )


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository) -> None:
        self.repository = repository

    def list_plans(self, include_inactive: bool = False) -> list[SubscriptionPlanRow]:
        return self.repository.list_plans(include_inactive=include_inactive)

    def get_entitlement(self, user: UserRow) -> Entitlement:
        now = datetime.now(timezone.utc)
        subscription = self.repository.get_active_subscription(user.id, now)
        plan = None
        if subscription is not None:
            plan = self.repository.get_plan(subscription.plan_id)
        if plan is None:
            plan = self.repository.get_default_plan() or fallback_free_plan()

        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1)

        today_used = self.repository.usage_sum(user.id, day_start, day_end)
        month_used = self.repository.usage_sum(user.id, month_start, month_end)
        daily_remaining = max(plan.daily_image_limit - today_used, 0)
        monthly_remaining = max(plan.monthly_image_limit - month_used, 0)
        return Entitlement(
            plan=subscription_plan_to_dto(plan),
            subscription=subscription,
            plan_row=plan,
            dailyLimit=plan.daily_image_limit,
            monthlyLimit=plan.monthly_image_limit,
            todayUsed=today_used,
            monthUsed=month_used,
            dailyRemaining=daily_remaining,
            monthlyRemaining=monthly_remaining,
        )

    def ensure_can_generate(self, user: UserRow, requested_images: int) -> Entitlement:
        entitlement = self.get_entitlement(user)
        if (
            requested_images > entitlement.dailyRemaining
            or requested_images > entitlement.monthlyRemaining
        ):
            payload = SubscriptionLimitPayload(
                error="图片生成额度不足，请订阅更高套餐。",
                errorCode="SUBSCRIPTION_LIMIT_REACHED",
                usage=entitlement.to_dto(),
                plans=[
                    subscription_plan_to_dto(plan)
                    for plan in self.repository.list_plans(include_inactive=False)
                    if plan.price_cents > 0
                ],
            ).model_dump(mode="json")
            raise SubscriptionLimitError(payload)
        return entitlement

    def record_generation(
        self, user: UserRow, entitlement: Entitlement, image_count: int
    ) -> None:
        self.record_usage(
            user=user,
            plan=entitlement.plan_row,
            subscription=entitlement.subscription,
            image_count=image_count,
        )

    def record_usage(
        self,
        *,
        user: UserRow,
        plan: SubscriptionPlanRow,
        subscription: UserSubscriptionRow | None,
        image_count: int,
    ) -> None:
        self.repository.add_usage(
            ImageUsageEventRow(
                user_id=user.id,
                subscription_id=subscription.id if subscription else None,
                plan_id=plan.id,
                image_count=image_count,
                source="image_generate",
            )
        )

    def activate_subscription(
        self, user: UserRow, plan: SubscriptionPlanRow
    ) -> UserSubscriptionRow:
        now = datetime.now(timezone.utc)
        for active in self.repository.list_active_subscriptions(user.id, now):
            active.status = "ended"
            active.ends_at = now
        subscription = UserSubscriptionRow(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
            starts_at=now,
            ends_at=now + timedelta(days=30),
        )
        return self.repository.save_subscription(subscription)


def fallback_free_plan() -> SubscriptionPlanRow:
    return SubscriptionPlanRow(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        code="free",
        name="Free",
        description="Fallback free image quota.",
        price_cents=0,
        daily_image_limit=1,
        monthly_image_limit=5,
        is_active=True,
        is_default=True,
        sort_order=0,
    )


def yuan_to_cents(value: str) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Invalid price.") from error
    if amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Invalid price.")
    return int(amount * 100)


def cents_to_yuan(cents: int) -> str:
    return f"{Decimal(cents) / Decimal(100):.2f}"


def subscription_plan_to_dto(plan: SubscriptionPlanRow) -> SubscriptionPlanDto:
    return SubscriptionPlanDto(
        id=str(plan.id),
        code=plan.code,
        name=plan.name,
        description=plan.description,
        price=cents_to_yuan(plan.price_cents),
        dailyImageLimit=plan.daily_image_limit,
        monthlyImageLimit=plan.monthly_image_limit,
        isActive=plan.is_active,
        isDefault=plan.is_default,
        sortOrder=plan.sort_order,
    )
```

- [ ] **Step 6: Run service tests green**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_subscription_service.py -q"
```

Expected: PASS.

---

### Task 3: Subscription Payment Integration

**Files:**
- Modify: `backend/app/payment_schemas.py`
- Modify: `backend/app/payment_service.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_payment_service.py`
- Modify: `backend/tests/test_payment_routes.py`

- [ ] **Step 1: Write failing payment service tests**

Append to `backend/tests/test_payment_service.py`:

```python
from app.subscription_models import SubscriptionPlanRow, UserSubscriptionRow
from app.subscription_repository import SubscriptionRepository
from app.subscription_service import SubscriptionService


def add_subscription_plan(db, *, price_cents=1990):
    plan = SubscriptionPlanRow(
        id=uuid.uuid4(),
        code="pro",
        name="Pro",
        description="Pro plan",
        price_cents=price_cents,
        daily_image_limit=20,
        monthly_image_limit=500,
        is_active=True,
        is_default=False,
        sort_order=1,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_create_subscription_zpay_order_uses_plan_price_and_plan_id(monkeypatch):
    db = make_session()
    user = make_user(db)
    plan = add_subscription_plan(db)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    monkeypatch.setenv("BACKEND_PUBLIC_ORIGIN", "https://api.example.com")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://app.example.com")

    order = PaymentService(PaymentRepository(db)).create_subscription_zpay_order(
        user=user,
        plan=plan,
        pay_type="alipay",
    )

    assert order.plan_id == plan.id
    assert order.order_kind == "subscription"
    assert order.amount_cents == 1990
    assert "money=19.90" in order.payment_url


def test_paid_subscription_order_activates_user_plan(monkeypatch):
    db = make_session()
    user = make_user(db)
    plan = add_subscription_plan(db)
    monkeypatch.setenv("ZPAY_PID", "merchant-1")
    monkeypatch.setenv("ZPAY_KEY", "secret")
    service = PaymentService(PaymentRepository(db))
    order = service.create_subscription_zpay_order(user=user, plan=plan, pay_type="alipay")
    callback = signed_params(
        {
            "pid": "merchant-1",
            "trade_no": "202605102200002",
            "out_trade_no": order.order_no,
            "type": "alipay",
            "name": "Pro",
            "money": "19.90",
            "trade_status": "TRADE_SUCCESS",
            "param": "user_id=U00000001",
        },
        "secret",
    )

    service.handle_zpay_notify(
        callback,
        subscription_service=SubscriptionService(SubscriptionRepository(db)),
        user=user,
    )

    subscription = db.query(UserSubscriptionRow).one()
    assert subscription.user_id == user.id
    assert subscription.plan_id == plan.id
    assert subscription.status == "active"
```

- [ ] **Step 2: Run payment service tests red**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_payment_service.py -q"
```

Expected: FAIL because `create_subscription_zpay_order` and activation hook do not exist.

- [ ] **Step 3: Add subscription payment schema**

In `backend/app/payment_schemas.py`, add:

```python
class CreateSubscriptionZpayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planId: str
    payType: str = "alipay"
```

- [ ] **Step 4: Extend payment service**

In `backend/app/payment_service.py`, import:

```python
from app.subscription_models import SubscriptionPlanRow
from app.subscription_service import SubscriptionService
```

Add method to `PaymentService`:

```python
    def create_subscription_zpay_order(
        self,
        *,
        user: UserRow,
        plan: SubscriptionPlanRow,
        pay_type: str,
    ) -> PaymentOrderRow:
        if plan.price_cents <= 0:
            raise PaymentServiceError("Free plans do not require payment.")
        settings = load_zpay_settings()
        normalized_pay_type = normalize_pay_type(pay_type)
        order_no = next_order_no()
        payment_url = build_submit_payment_url(
            config=settings.config,
            name=plan.name,
            money=cents_to_money(plan.price_cents),
            out_trade_no=order_no,
            notify_url=f"{settings.backend_origin}/api/payments/zpay/notify",
            return_url=f"{settings.frontend_origin}/payments/return",
            pay_type=normalized_pay_type,
            param=f"user_id={user.user_id};plan_id={plan.id}",
        )
        return self.repository.create_order(
            PaymentOrderRow(
                order_no=order_no,
                user_id=user.id,
                user_public_id=user.user_id,
                provider="zpay",
                plan_id=plan.id,
                order_kind="subscription",
                subject=plan.name,
                amount_cents=plan.price_cents,
                pay_type=normalized_pay_type,
                status="pending",
                payment_url=payment_url,
            )
        )
```

Change `handle_zpay_notify` signature:

```python
    def handle_zpay_notify(
        self,
        params: dict[str, object],
        subscription_service: SubscriptionService | None = None,
        user: UserRow | None = None,
    ) -> PaymentOrderRow:
```

After setting `order.status = "paid"` and before save return, add:

```python
        saved = self.repository.save(order)
        if (
            saved.order_kind == "subscription"
            and saved.plan_id is not None
            and subscription_service is not None
            and user is not None
        ):
            plan = subscription_service.repository.get_plan(saved.plan_id)
            if plan is not None:
                subscription_service.activate_subscription(user=user, plan=plan)
        return saved
```

Remove the old `return self.repository.save(order)` to avoid double returns.

- [ ] **Step 5: Run payment service tests green**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_payment_service.py -q"
```

Expected: PASS.

---

### Task 4: Subscription Routes And Image Quota Enforcement

**Files:**
- Create: `backend/tests/test_subscription_routes.py`
- Modify: `backend/tests/test_main.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write failing route tests**

Create `backend/tests/test_subscription_routes.py`:

```python
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


def make_client(is_admin=False):
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
        is_admin=is_admin,
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
    return client, session, user


def cleanup_overrides():
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_current_user, None)


def add_plan(session, code="pro", price_cents=1990, active=True):
    plan = SubscriptionPlanRow(
        id=uuid.uuid4(),
        code=code,
        name="Pro",
        description="Pro plan",
        price_cents=price_cents,
        daily_image_limit=20,
        monthly_image_limit=500,
        is_active=active,
        is_default=False,
        sort_order=1,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def test_user_can_list_active_subscription_plans():
    test_client, session, _ = make_client()
    try:
        add_plan(session)
        add_plan(session, code="hidden", active=False)
        response = test_client.get("/api/subscription/plans")
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert [plan["code"] for plan in response.json()["plans"]] == ["pro"]


def test_admin_can_create_subscription_plan():
    test_client, session, _ = make_client(is_admin=True)
    try:
        response = test_client.post(
            "/api/admin/subscription/plans",
            json={
                "code": "starter",
                "name": "Starter",
                "description": "Starter plan",
                "price": "9.90",
                "dailyImageLimit": 10,
                "monthlyImageLimit": 100,
                "isActive": True,
                "isDefault": False,
                "sortOrder": 1,
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert response.json()["plan"]["code"] == "starter"
    assert session.query(SubscriptionPlanRow).one().price_cents == 990


def test_regular_user_cannot_create_subscription_plan():
    test_client, _, _ = make_client(is_admin=False)
    try:
        response = test_client.post(
            "/api/admin/subscription/plans",
            json={
                "name": "Starter",
                "price": "9.90",
                "dailyImageLimit": 10,
                "monthlyImageLimit": 100,
            },
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 403
```

Append to `backend/tests/test_main.py`:

```python
def test_image_route_returns_subscription_limit_when_quota_is_insufficient(monkeypatch):
    allow_authenticated_user()

    class LimitError(Exception):
        status_code = 402
        payload = {
            "error": "图片生成额度不足，请订阅更高套餐。",
            "errorCode": "SUBSCRIPTION_LIMIT_REACHED",
            "usage": {"dailyRemaining": 0, "monthlyRemaining": 0},
            "plans": [],
        }

    class FakeSubscriptionService:
        def ensure_can_generate(self, user, requested_images):
            raise LimitError()

    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setattr(
        "app.main.build_subscription_service",
        lambda db: FakeSubscriptionService(),
        raising=False,
    )
    try:
        response = client.post(
            "/api/images/generate",
            data={"toolId": "product", "imageCount": "4"},
            files={"image": ("product.png", TINY_PNG, "image/png")},
        )
    finally:
        cleanup_auth_override()

    assert response.status_code == 402
    assert response.json()["errorCode"] == "SUBSCRIPTION_LIMIT_REACHED"
```

- [ ] **Step 2: Run route tests red**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_subscription_routes.py backend\tests\test_main.py -q"
```

Expected: FAIL because routes and quota wiring do not exist.

- [ ] **Step 3: Add subscription service factory and routes**

In `backend/app/main.py`, import:

```python
from app.subscription_repository import SubscriptionRepository
from app.subscription_schemas import (
    EntitlementEnvelope,
    SubscriptionPlanInput,
    SubscriptionPlanListEnvelope,
)
from app.subscription_service import (
    SubscriptionLimitError,
    SubscriptionService,
    SubscriptionServiceError,
    subscription_plan_to_dto,
    yuan_to_cents,
)
from app.subscription_models import SubscriptionPlanRow
```

Add factory:

```python
def build_subscription_service(db: Session) -> SubscriptionService:
    return SubscriptionService(SubscriptionRepository(db))
```

Add helpers:

```python
def subscription_error_response(error: SubscriptionServiceError) -> JSONResponse:
    if isinstance(error, SubscriptionLimitError):
        return JSONResponse(error.payload, status_code=error.status_code)
    return JSONResponse({"error": str(error)}, status_code=error.status_code)


def plan_from_input(payload: SubscriptionPlanInput, existing: SubscriptionPlanRow | None = None) -> SubscriptionPlanRow:
    if payload.dailyImageLimit <= 0 or payload.monthlyImageLimit <= 0:
        raise SubscriptionServiceError("套餐额度必须大于 0。")
    if payload.dailyImageLimit > payload.monthlyImageLimit:
        raise SubscriptionServiceError("每日额度不能超过每月额度。")
    plan = existing or SubscriptionPlanRow(code=(payload.code or "").strip())
    if payload.code is not None:
        plan.code = payload.code.strip()
    if not plan.code:
        raise SubscriptionServiceError("套餐代码不能为空。")
    plan.name = payload.name.strip()
    if not plan.name:
        raise SubscriptionServiceError("套餐名称不能为空。")
    plan.description = payload.description.strip()
    plan.price_cents = yuan_to_cents(payload.price)
    plan.daily_image_limit = payload.dailyImageLimit
    plan.monthly_image_limit = payload.monthlyImageLimit
    plan.is_active = payload.isActive
    plan.is_default = payload.isDefault
    plan.sort_order = payload.sortOrder
    return plan
```

Add routes before image route:

```python
@app.get("/api/subscription/plans")
async def list_subscription_plans(
    _current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    plans = build_subscription_service(db).list_plans(include_inactive=False)
    return SubscriptionPlanListEnvelope(
        plans=[subscription_plan_to_dto(plan) for plan in plans]
    ).model_dump(mode="json")


@app.get("/api/subscription/me")
async def get_subscription_entitlement(
    current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    entitlement = build_subscription_service(db).get_entitlement(current_user)
    return EntitlementEnvelope(entitlement=entitlement.to_dto()).model_dump(mode="json")


@app.get("/api/admin/subscription/plans")
async def list_admin_subscription_plans(
    _admin_user: UserRow = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
):
    plans = build_subscription_service(db).list_plans(include_inactive=True)
    return SubscriptionPlanListEnvelope(
        plans=[subscription_plan_to_dto(plan) for plan in plans]
    ).model_dump(mode="json")


@app.post("/api/admin/subscription/plans")
async def create_admin_subscription_plan(
    payload: SubscriptionPlanInput,
    _admin_user: UserRow = Depends(require_admin_user),
    db: Session = Depends(get_db_session),
):
    try:
        service = build_subscription_service(db)
        plan = plan_from_input(payload)
        if plan.is_default:
            service.repository.clear_default_plans()
        saved = service.repository.save_plan(plan)
        return {"plan": subscription_plan_to_dto(saved).model_dump(mode="json")}
    except (SubscriptionServiceError, ValueError) as error:
        status_code = error.status_code if isinstance(error, SubscriptionServiceError) else 400
        return JSONResponse({"error": str(error)}, status_code=status_code)
```

- [ ] **Step 4: Wire subscription quota into image route**

Change image route dependency:

```python
    current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
```

Replace `_current_user`.

After `valid_request = await validate_image_form(...)`, add:

```python
        subscription_service = build_subscription_service(db)
        entitlement = subscription_service.ensure_can_generate(
            user=current_user,
            requested_images=valid_request.generation_settings.image_count,
        )
```

After OpenAI generation succeeds and before return:

```python
        subscription_service.record_generation(
            user=current_user,
            entitlement=entitlement,
            image_count=len(generated.images),
        )
```

Add `SubscriptionLimitError` to the except handling:

```python
    except SubscriptionLimitError as error:
        return subscription_error_response(error)
```

- [ ] **Step 5: Run route tests green**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_subscription_routes.py backend\tests\test_main.py -q"
```

Expected: PASS.

---

### Task 5: Subscription Order Route

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_payment_routes.py`

- [ ] **Step 1: Write failing subscription order route test**

Append to `backend/tests/test_payment_routes.py`:

```python
from app.subscription_models import SubscriptionPlanRow, UserSubscriptionRow


def add_paid_plan(session):
    plan = SubscriptionPlanRow(
        id=uuid.uuid4(),
        code="pro",
        name="Pro",
        description="Pro plan",
        price_cents=1990,
        daily_image_limit=20,
        monthly_image_limit=500,
        is_active=True,
        is_default=False,
        sort_order=1,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan


def test_create_subscription_zpay_order_route_returns_payment_url(monkeypatch):
    test_client, session = make_client(monkeypatch)
    plan = add_paid_plan(session)
    try:
        response = test_client.post(
            "/api/payments/zpay/subscription-orders",
            json={"planId": str(plan.id), "payType": "alipay"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert response.json()["order"]["paymentUrl"]
    assert response.json()["order"]["subject"] == "Pro"


def test_create_free_subscription_order_activates_without_payment(monkeypatch):
    test_client, session = make_client(monkeypatch)
    plan = SubscriptionPlanRow(
        id=uuid.uuid4(),
        code="free",
        name="Free",
        description="Free plan",
        price_cents=0,
        daily_image_limit=5,
        monthly_image_limit=50,
        is_active=True,
        is_default=True,
        sort_order=0,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)
    try:
        response = test_client.post(
            "/api/payments/zpay/subscription-orders",
            json={"planId": str(plan.id), "payType": "alipay"},
        )
    finally:
        cleanup_overrides()

    assert response.status_code == 200
    assert response.json()["order"]["paymentUrl"] is None
    assert session.query(UserSubscriptionRow).one().plan_id == plan.id
```

- [ ] **Step 2: Run route test red**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_payment_routes.py -q"
```

Expected: FAIL because `/api/payments/zpay/subscription-orders` does not exist.

- [ ] **Step 3: Add subscription order route**

In `backend/app/main.py`, import:

```python
from app.payment_schemas import (
    CreateSubscriptionZpayOrderRequest,
    CreateZpayOrderRequest,
    PaymentOrderEnvelope,
)
```

Add route:

```python
@app.post("/api/payments/zpay/subscription-orders")
async def create_zpay_subscription_order(
    payload: CreateSubscriptionZpayOrderRequest,
    current_user: UserRow = Depends(get_current_user),
    db: Session = Depends(get_db_session),
):
    try:
        subscription_service = build_subscription_service(db)
        plan = subscription_service.repository.get_plan(payload.planId)
        if plan is None or not plan.is_active:
            return JSONResponse({"error": "套餐不存在或已停用。"}, status_code=404)
        if plan.price_cents <= 0:
            subscription_service.activate_subscription(user=current_user, plan=plan)
            free_order = PaymentOrderRow(
                order_no=next_order_no(),
                user_id=current_user.id,
                user_public_id=current_user.user_id,
                provider="zpay",
                plan_id=plan.id,
                order_kind="subscription",
                subject=plan.name,
                amount_cents=0,
                pay_type=payload.payType,
                status="paid",
                payment_url=None,
            )
            order = PaymentRepository(db).create_order(free_order)
        else:
            order = build_payment_service(db).create_subscription_zpay_order(
                user=current_user,
                plan=plan,
                pay_type=payload.payType,
            )
        return PaymentOrderEnvelope(order=payment_order_to_dto(order)).model_dump(mode="json")
    except PaymentServiceError as error:
        return payment_error_response(error)
```

Also import `PaymentOrderRow` and `next_order_no` if not already available:

```python
from app.payment_models import PaymentOrderRow
from app.payment_service import next_order_no
```

- [ ] **Step 4: Update ZPAY notify route to activate subscription**

In `handle_zpay_notify`, after params are read, lookup the order before handling if needed or update service call:

```python
        order = build_payment_service(db).handle_zpay_notify(params)
        if order.order_kind == "subscription":
            user = AccountRepository(db).get_by_id(order.user_id)
            if user is not None:
                build_payment_service(db).handle_zpay_notify(
                    params,
                    subscription_service=build_subscription_service(db),
                    user=user,
                )
```

Then simplify to avoid double handling:

```python
        preliminary_order_no = str(params.get("out_trade_no") or "")
        existing_order = PaymentRepository(db).get_by_order_no(preliminary_order_no)
        notify_user = (
            AccountRepository(db).get_by_id(existing_order.user_id)
            if existing_order is not None and existing_order.order_kind == "subscription"
            else None
        )
        build_payment_service(db).handle_zpay_notify(
            params,
            subscription_service=build_subscription_service(db),
            user=notify_user,
        )
```

- [ ] **Step 5: Run payment route tests green**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests\test_payment_routes.py -q"
```

Expected: PASS.

---

### Task 6: Frontend Subscription APIs And Billing Page

**Files:**
- Create: `frontend/tests/subscription-flow.test.mjs`
- Create: `frontend/src/lib/subscription-api.ts`
- Modify: `frontend/src/lib/payment-api.ts`
- Modify: `frontend/src/app/billing/page.tsx`

- [ ] **Step 1: Write failing frontend tests**

Create `frontend/tests/subscription-flow.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { test } from "node:test";

test("subscription api exposes plan and entitlement helpers", () => {
  const source = readFileSync("src/lib/subscription-api.ts", "utf8");

  assert.match(source, /listSubscriptionPlans/);
  assert.match(source, /getMyEntitlement/);
  assert.match(source, /listAdminSubscriptionPlans/);
  assert.match(source, /createAdminSubscriptionPlan/);
  assert.match(source, /credentials: "include"/);
  assert.match(source, /\/api\/subscription\/plans/);
  assert.match(source, /\/api\/admin\/subscription\/plans/);
});

test("payment api creates subscription zpay orders", () => {
  const source = readFileSync("src/lib/payment-api.ts", "utf8");

  assert.match(source, /createSubscriptionZpayOrder/);
  assert.match(source, /\/api\/payments\/zpay\/subscription-orders/);
  assert.match(source, /planId/);
});

test("billing page loads backend subscription plans", () => {
  const source = readFileSync("src/app/billing/page.tsx", "utf8");

  assert.match(source, /listSubscriptionPlans/);
  assert.match(source, /createSubscriptionZpayOrder/);
  assert.doesNotMatch(source, /const plans = \[/);
  assert.match(source, /每日/);
  assert.match(source, /每月/);
});

test("admin subscriptions page exists", () => {
  assert.equal(existsSync("src/app/admin/subscriptions/page.tsx"), true);
});
```

- [ ] **Step 2: Run frontend tests red**

Run:

```bash
rtk powershell -NoProfile -Command "npm test -- tests/subscription-flow.test.mjs"
```

from `frontend`.

Expected: FAIL because API/page files are missing or still hardcoded.

- [ ] **Step 3: Add subscription API client**

Create `frontend/src/lib/subscription-api.ts`:

```typescript
const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export type SubscriptionPlan = {
  id: string;
  code: string;
  name: string;
  description: string;
  price: string;
  dailyImageLimit: number;
  monthlyImageLimit: number;
  isActive: boolean;
  isDefault: boolean;
  sortOrder: number;
};

export type Entitlement = {
  plan: SubscriptionPlan;
  dailyLimit: number;
  monthlyLimit: number;
  todayUsed: number;
  monthUsed: number;
  dailyRemaining: number;
  monthlyRemaining: number;
};

export type PlanInput = {
  code?: string;
  name: string;
  description: string;
  price: string;
  dailyImageLimit: number;
  monthlyImageLimit: number;
  isActive: boolean;
  isDefault: boolean;
  sortOrder: number;
};

export async function listSubscriptionPlans() {
  return readJsonResponse<{ plans: SubscriptionPlan[] }>(
    await fetch(`${apiBaseUrl}/api/subscription/plans`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function getMyEntitlement() {
  return readJsonResponse<{ entitlement: Entitlement }>(
    await fetch(`${apiBaseUrl}/api/subscription/me`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function listAdminSubscriptionPlans() {
  return readJsonResponse<{ plans: SubscriptionPlan[] }>(
    await fetch(`${apiBaseUrl}/api/admin/subscription/plans`, {
      method: "GET",
      credentials: "include",
    }),
  );
}

export async function createAdminSubscriptionPlan(input: PlanInput) {
  return readJsonResponse<{ plan: SubscriptionPlan }>(
    await fetch(`${apiBaseUrl}/api/admin/subscription/plans`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}

async function readJsonResponse<T>(response: Response): Promise<T> {
  const payload = await readJsonPayload<T>(response);
  if (!response.ok || payload.error || payload.detail) {
    throw new Error(payload.error || payload.detail || "Subscription request failed.");
  }
  return payload;
}

async function readJsonPayload<T>(
  response: Response,
): Promise<T & { error?: string | null; detail?: string | null }> {
  const contentType = response.headers.get("content-type")?.toLowerCase();
  if (!contentType?.includes("json")) {
    return {} as T & { error?: string | null; detail?: string | null };
  }
  try {
    return (await response.json()) as T & { error?: string | null; detail?: string | null };
  } catch {
    return {} as T & { error?: string | null; detail?: string | null };
  }
}
```

- [ ] **Step 4: Extend payment API**

In `frontend/src/lib/payment-api.ts`, add:

```typescript
export type CreateSubscriptionZpayOrderInput = {
  planId: string;
  payType: "alipay" | "wxpay";
};

export async function createSubscriptionZpayOrder(
  input: CreateSubscriptionZpayOrderInput,
): Promise<PaymentOrderEnvelope> {
  return readJsonResponse<PaymentOrderEnvelope>(
    await fetch(`${apiBaseUrl}/api/payments/zpay/subscription-orders`, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
}
```

- [ ] **Step 5: Replace hardcoded billing plans**

Modify `frontend/src/app/billing/page.tsx`:

- Import `useEffect`.
- Import `listSubscriptionPlans`, `SubscriptionPlan`.
- Import `createSubscriptionZpayOrder`.
- Replace the hardcoded `plans` array with state loaded from `listSubscriptionPlans()`.
- Submit selected plan id to `createSubscriptionZpayOrder`.
- Render daily/monthly quota labels.
- If returned `paymentUrl` is null, show a success message instead of redirecting.

Use this submit core:

```typescript
const envelope = await createSubscriptionZpayOrder({
  planId: selectedPlan.id,
  payType,
});
if (envelope.order.paymentUrl) {
  window.location.assign(envelope.order.paymentUrl);
  return;
}
setStatus("套餐已更新。");
```

- [ ] **Step 6: Run frontend subscription tests green**

Run:

```bash
rtk powershell -NoProfile -Command "npm test -- tests/subscription-flow.test.mjs"
```

from `frontend`.

Expected: PASS.

---

### Task 7: Admin Subscription UI And Navigation

**Files:**
- Create: `frontend/src/app/admin/subscriptions/page.tsx`
- Modify: `frontend/src/components/app-nav.tsx`
- Modify: `frontend/tests/auth-flow.test.mjs`
- Modify: `frontend/tests/subscription-flow.test.mjs`

- [ ] **Step 1: Add failing admin UI source assertions**

Append to `frontend/tests/subscription-flow.test.mjs`:

```javascript
test("admin subscription page manages plan fields", () => {
  const source = readFileSync("src/app/admin/subscriptions/page.tsx", "utf8");

  assert.match(source, /listAdminSubscriptionPlans/);
  assert.match(source, /createAdminSubscriptionPlan/);
  assert.match(source, /dailyImageLimit/);
  assert.match(source, /monthlyImageLimit/);
  assert.match(source, /每日额度/);
  assert.match(source, /每月额度/);
});

test("navigation links admin subscription management for admins", () => {
  const source = readFileSync("src/components/app-nav.tsx", "utf8");

  assert.match(source, /href: "\/admin\/subscriptions"/);
  assert.match(source, /订阅管理/);
});
```

- [ ] **Step 2: Run tests red**

Run:

```bash
rtk powershell -NoProfile -Command "npm test -- tests/subscription-flow.test.mjs"
```

Expected: FAIL because admin page/nav link is missing.

- [ ] **Step 3: Create admin subscriptions page**

Create `frontend/src/app/admin/subscriptions/page.tsx` as a client component modeled after `frontend/src/app/admin/accounts/page.tsx`.

Required behavior:

- Uses `AppNav`.
- Uses `useAuth` to block non-admins.
- Calls `listAdminSubscriptionPlans()` on load.
- Form fields:
  - `code`
  - `name`
  - `description`
  - `price`
  - `dailyImageLimit`
  - `monthlyImageLimit`
  - `isActive`
  - `isDefault`
  - `sortOrder`
- Submit calls `createAdminSubscriptionPlan()`.
- Table lists plan name, price, daily/monthly quota, active/default state.

Keep UI compact and utilitarian, matching existing admin page classes.

- [ ] **Step 4: Add nav item**

In `frontend/src/components/app-nav.tsx`, import a suitable lucide icon:

```typescript
  ListChecks,
```

Change admin items:

```typescript
const adminItems = [
  { label: "订阅管理", href: "/admin/subscriptions", icon: ListChecks },
  { label: "账号管理", href: "/admin/accounts", icon: ShieldCheck },
];
```

Then:

```typescript
const items = user?.isAdmin ? [...baseItems, ...adminItems] : baseItems;
```

- [ ] **Step 5: Run frontend admin tests green**

Run:

```bash
rtk powershell -NoProfile -Command "npm test -- tests/subscription-flow.test.mjs tests/auth-flow.test.mjs"
```

from `frontend`.

Expected: PASS.

---

### Task 8: Quota Modal In Product Workbench

**Files:**
- Modify: `frontend/src/lib/image-api.ts`
- Modify: `frontend/src/components/product-workbench.tsx`
- Modify: `frontend/tests/subscription-flow.test.mjs`

- [ ] **Step 1: Add failing frontend quota prompt assertions**

Append to `frontend/tests/subscription-flow.test.mjs`:

```javascript
test("image api preserves subscription limit payload", () => {
  const source = readFileSync("src/lib/image-api.ts", "utf8");

  assert.match(source, /SUBSCRIPTION_LIMIT_REACHED/);
  assert.match(source, /SubscriptionLimitError/);
  assert.match(source, /usage/);
  assert.match(source, /plans/);
});

test("product workbench opens subscription modal on quota limit", () => {
  const source = readFileSync("src/components/product-workbench.tsx", "utf8");

  assert.match(source, /subscriptionLimit/);
  assert.match(source, /SUBSCRIPTION_LIMIT_REACHED/);
  assert.match(source, /套餐额度不足/);
  assert.match(source, /\/billing/);
});
```

- [ ] **Step 2: Run frontend quota tests red**

Run:

```bash
rtk powershell -NoProfile -Command "npm test -- tests/subscription-flow.test.mjs"
```

Expected: FAIL because image API and workbench do not handle the structured limit payload.

- [ ] **Step 3: Extend image API error type**

In `frontend/src/lib/image-api.ts`, add exported types:

```typescript
export type SubscriptionLimitPayload = {
  error: string;
  errorCode: "SUBSCRIPTION_LIMIT_REACHED";
  usage: {
    dailyRemaining: number;
    monthlyRemaining: number;
    plan?: { name: string };
  };
  plans: Array<{
    id: string;
    name: string;
    price: string;
    dailyImageLimit: number;
    monthlyImageLimit: number;
  }>;
};

export class SubscriptionLimitError extends Error {
  payload: SubscriptionLimitPayload;

  constructor(payload: SubscriptionLimitPayload) {
    super(payload.error);
    this.name = "SubscriptionLimitError";
    this.payload = payload;
  }
}
```

In the response handling where `payload.error` is checked, before generic `throw new Error(...)`, add:

```typescript
if (payload.errorCode === "SUBSCRIPTION_LIMIT_REACHED") {
  throw new SubscriptionLimitError(payload as SubscriptionLimitPayload);
}
```

- [ ] **Step 4: Update product workbench**

In `frontend/src/components/product-workbench.tsx`:

- Import `SubscriptionLimitError`.
- Add state:

```typescript
const [subscriptionLimit, setSubscriptionLimit] = useState<SubscriptionLimitPayload | null>(null);
```

- In image generation catch block:

```typescript
if (caught instanceof SubscriptionLimitError) {
  setSubscriptionLimit(caught.payload);
  setError("");
  return;
}
```

- Render modal near the end of JSX:

```tsx
{subscriptionLimit ? (
  <div className="fixed inset-0 z-50 grid place-items-center bg-ink/30 px-4">
    <section className="w-full max-w-md rounded-lg border border-border bg-surface p-5 shadow-refined">
      <p className="text-xs font-bold uppercase text-accent">Subscription</p>
      <h2 className="mt-1 text-xl font-black">套餐额度不足</h2>
      <p className="mt-2 text-sm leading-6 text-ink-light">
        当前套餐今日剩余 {subscriptionLimit.usage.dailyRemaining} 张，本月剩余 {subscriptionLimit.usage.monthlyRemaining} 张。
      </p>
      <div className="mt-4 grid gap-2">
        {subscriptionLimit.plans.slice(0, 3).map((plan) => (
          <div key={plan.id} className="rounded-md border border-border bg-surface-soft p-3 text-sm">
            <p className="font-bold">{plan.name} · ¥{plan.price}/月</p>
            <p className="mt-1 text-ink-light">
              每日 {plan.dailyImageLimit} 张，每月 {plan.monthlyImageLimit} 张
            </p>
          </div>
        ))}
      </div>
      <div className="mt-5 flex flex-wrap gap-2">
        <Link href="/billing" className="inline-flex h-10 items-center rounded-md bg-ink px-4 text-sm font-black text-white">
          查看套餐
        </Link>
        <button
          type="button"
          onClick={() => setSubscriptionLimit(null)}
          className="h-10 rounded-md border border-border px-4 text-sm font-bold text-ink-light"
        >
          稍后再说
        </button>
      </div>
    </section>
  </div>
) : null}
```

- [ ] **Step 5: Run frontend quota tests green**

Run:

```bash
rtk powershell -NoProfile -Command "npm test -- tests/subscription-flow.test.mjs"
```

Expected: PASS.

---

### Task 9: Full Verification

**Files:**
- Modify: `docs/plans/2026-05-10-subscription-management-design.md` if implementation decisions changed.

- [ ] **Step 1: Run backend tests**

Run:

```bash
rtk powershell -NoProfile -Command "backend\.venv\Scripts\python -m pytest backend\tests -q"
```

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run from `frontend`:

```bash
rtk powershell -NoProfile -Command "npm test"
```

Expected: PASS.

- [ ] **Step 3: Run frontend lint**

Run from `frontend`:

```bash
rtk powershell -NoProfile -Command "npm run lint"
```

Expected: PASS with no errors.

- [ ] **Step 4: Run frontend build**

Run from `frontend`:

```bash
rtk powershell -NoProfile -Command "npm run build"
```

Expected: PASS.

- [ ] **Step 5: Review changed files**

Run:

```bash
rtk powershell -NoProfile -Command "git status --short"
rtk powershell -NoProfile -Command "git diff --stat"
```

Expected: only subscription-related files plus existing ZPAY files if they are still uncommitted.

---

## Self-Review

- Spec coverage:
  - Admin-created plans: Tasks 1, 2, 4, 7.
  - Default Free plan: Tasks 1 and 2.
  - Daily/monthly quotas: Tasks 1, 2, 4, 8.
  - Deduct by image count: Tasks 2 and 4.
  - Payment subscription activation: Tasks 3 and 5.
  - Quota prompt on insufficient images: Tasks 4 and 8.
- Placeholder scan: no `TBD`, `TODO`, or unspecified implementation steps remain.
- Type consistency:
  - Backend uses `dailyImageLimit/monthlyImageLimit` in API schemas and `daily_image_limit/monthly_image_limit` in DB.
  - Frontend uses `SubscriptionLimitError` and `SUBSCRIPTION_LIMIT_REACHED` consistently.
  - Payment route uses `planId` and `payType`.

