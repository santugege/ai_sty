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
        plan = self.repository.get_plan(subscription.plan_id) if subscription else None
        if plan is None:
            plan = self.repository.get_default_plan() or fallback_free_plan()

        day_start, day_end = utc_day_bounds(now)
        month_start, month_end = utc_month_bounds(now)
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
        if requested_images <= 0:
            raise SubscriptionServiceError("Requested image count must be positive.")
        entitlement = self.get_entitlement(user)
        if (
            requested_images > entitlement.dailyRemaining
            or requested_images > entitlement.monthlyRemaining
        ):
            payload = SubscriptionLimitPayload(
                error="Image generation quota reached.",
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
        if image_count <= 0:
            raise SubscriptionServiceError("Image count must be positive.")
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
        self, user: UserRow, plan: SubscriptionPlanRow, *, commit: bool = True
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
        if not commit:
            return self.repository.flush_subscription(subscription)
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


def utc_day_bounds(now: datetime) -> tuple[datetime, datetime]:
    day_start = now.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return day_start, day_start + timedelta(days=1)


def utc_month_bounds(now: datetime) -> tuple[datetime, datetime]:
    month_start = now.astimezone(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    return month_start, month_end


def yuan_to_cents(value: str) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Invalid price.") from error

    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
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
