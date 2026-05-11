from __future__ import annotations

import uuid
from datetime import datetime, timezone

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
        subscription = self.db.scalar(
            select(UserSubscriptionRow)
            .where(
                UserSubscriptionRow.user_id == user_id,
                UserSubscriptionRow.status == "active",
                UserSubscriptionRow.starts_at <= now,
                UserSubscriptionRow.ends_at > now,
            )
            .order_by(UserSubscriptionRow.starts_at.desc())
        )
        return ensure_utc_subscription(subscription)

    def list_active_subscriptions(
        self, user_id: uuid.UUID, now: datetime
    ) -> list[UserSubscriptionRow]:
        subscriptions = list(
            self.db.scalars(
                select(UserSubscriptionRow).where(
                    UserSubscriptionRow.user_id == user_id,
                    UserSubscriptionRow.status == "active",
                    UserSubscriptionRow.starts_at <= now,
                    UserSubscriptionRow.ends_at > now,
                )
            )
        )
        return [ensure_utc_subscription(subscription) for subscription in subscriptions]

    def save_subscription(self, subscription: UserSubscriptionRow) -> UserSubscriptionRow:
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return ensure_utc_subscription(subscription)

    def flush_subscription(self, subscription: UserSubscriptionRow) -> UserSubscriptionRow:
        self.db.add(subscription)
        self.db.flush()
        return ensure_utc_subscription(subscription)

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
                    ImageUsageEventRow.image_count > 0,
                    ImageUsageEventRow.created_at >= start,
                    ImageUsageEventRow.created_at < end,
                )
            )
            or 0
        )


def ensure_utc_subscription(
    subscription: UserSubscriptionRow | None,
) -> UserSubscriptionRow | None:
    if subscription is None:
        return None
    if subscription.starts_at.tzinfo is None:
        subscription.starts_at = subscription.starts_at.replace(tzinfo=timezone.utc)
    if subscription.ends_at.tzinfo is None:
        subscription.ends_at = subscription.ends_at.replace(tzinfo=timezone.utc)
    return subscription
