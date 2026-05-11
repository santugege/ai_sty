from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from app.payment_models import PaymentOrderRow
from app.payment_repository import PaymentRepository
from app.payment_schemas import PaymentOrderDto
from app.subscription_models import SubscriptionPlanRow
from app.subscription_service import SubscriptionService
from app.user_models import UserRow
from app.zpay_client import (
    ZpayConfig,
    build_submit_payment_url,
    verify_signature,
)

SUPPORTED_PAY_TYPES = {"alipay", "wxpay", "qqpay"}


class PaymentServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ZpaySettings:
    config: ZpayConfig
    backend_origin: str
    frontend_origin: str


class PaymentService:
    def __init__(self, repository: PaymentRepository) -> None:
        self.repository = repository

    def create_zpay_order(
        self,
        *,
        user: UserRow,
        subject: str,
        amount: str,
        pay_type: str,
    ) -> PaymentOrderRow:
        settings = load_zpay_settings()
        normalized_pay_type = normalize_pay_type(pay_type)
        normalized_subject = normalize_subject(subject)
        amount_in_cents = amount_cents(amount)
        order_no = next_order_no()
        payment_url = build_submit_payment_url(
            config=settings.config,
            name=normalized_subject,
            money=cents_to_money(amount_in_cents),
            out_trade_no=order_no,
            notify_url=f"{settings.backend_origin}/api/payments/zpay/notify",
            return_url=f"{settings.frontend_origin}/payments/return",
            pay_type=normalized_pay_type,
            param=f"user_id={user.user_id}",
        )
        return self.repository.create_order(
            PaymentOrderRow(
                order_no=order_no,
                user_id=user.id,
                user_public_id=user.user_id,
                provider="zpay",
                subject=normalized_subject,
                amount_cents=amount_in_cents,
                pay_type=normalized_pay_type,
                status="pending",
                payment_url=payment_url,
            )
        )

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
        normalized_subject = normalize_subject(plan.name)
        order_no = next_order_no()
        payment_url = build_submit_payment_url(
            config=settings.config,
            name=normalized_subject,
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
                subject=normalized_subject,
                amount_cents=plan.price_cents,
                pay_type=normalized_pay_type,
                status="pending",
                payment_url=payment_url,
            )
        )

    def handle_zpay_notify(
        self,
        params: dict[str, object],
        *,
        subscription_service: SubscriptionService | None = None,
        user: UserRow | None = None,
    ) -> PaymentOrderRow:
        settings = load_zpay_settings()
        if not verify_signature(params, settings.config.key):
            raise PaymentServiceError("Invalid ZPAY signature.", status_code=400)
        if str(params.get("pid") or "") != settings.config.pid:
            raise PaymentServiceError("Invalid ZPAY merchant.", status_code=400)

        order_no = str(params.get("out_trade_no") or "").strip()
        order = self.repository.get_by_order_no(order_no)
        if order is None:
            raise PaymentServiceError("Payment order not found.", status_code=404)

        if amount_cents(str(params.get("money") or "")) != order.amount_cents:
            raise PaymentServiceError("Payment amount mismatch.", status_code=400)
        if str(params.get("trade_status") or "") != "TRADE_SUCCESS":
            raise PaymentServiceError("Payment is not successful.", status_code=400)

        order.raw_callback = json.dumps(params, ensure_ascii=False, sort_keys=True)
        order.provider_trade_no = str(params.get("trade_no") or "")
        if order.status != "paid":
            order.status = "paid"
            order.paid_at = datetime.now(timezone.utc)

        if should_activate_subscription(order, subscription_service, user):
            plan = subscription_service.repository.get_plan(order.plan_id)
            if plan is not None:
                try:
                    subscription = subscription_service.activate_subscription(
                        user,
                        plan,
                        commit=False,
                    )
                    order.subscription_id = subscription.id
                    self.repository.flush(order)
                    self.repository.commit()
                    return self.repository.refresh(order)
                except Exception:
                    self.repository.rollback()
                    raise

        return self.repository.save(order)


def load_zpay_settings() -> ZpaySettings:
    pid = (os.getenv("ZPAY_PID") or "").strip()
    key = (os.getenv("ZPAY_KEY") or "").strip()
    if not pid or not key:
        raise PaymentServiceError("ZPAY is not configured.", status_code=500)

    return ZpaySettings(
        config=ZpayConfig(
            pid=pid,
            key=key,
            submit_url=(os.getenv("ZPAY_SUBMIT_URL") or "https://zpayz.cn/submit.php").strip(),
        ),
        backend_origin=origin_env("BACKEND_PUBLIC_ORIGIN", "http://localhost:8000"),
        frontend_origin=origin_env("FRONTEND_ORIGIN", "http://localhost:3000"),
    )


def amount_cents(value: str) -> int:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise PaymentServiceError("Invalid payment amount.") from error

    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise PaymentServiceError("Invalid payment amount.")
    return int(amount * 100)


def cents_to_money(cents: int) -> str:
    return f"{Decimal(cents) / Decimal(100):.2f}"


def normalize_pay_type(pay_type: str) -> str:
    normalized = pay_type.strip().lower()
    if normalized not in SUPPORTED_PAY_TYPES:
        raise PaymentServiceError("Unsupported payment method.")
    return normalized


def normalize_subject(subject: str) -> str:
    normalized = subject.strip()
    if not normalized:
        raise PaymentServiceError("Payment subject is required.")
    return normalized[:120]


def next_order_no() -> str:
    return f"P{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:10].upper()}"


def origin_env(name: str, fallback: str) -> str:
    first_value = (os.getenv(name) or fallback).split(",")[0].strip()
    return first_value.rstrip("/")


def should_activate_subscription(
    order: PaymentOrderRow,
    subscription_service: SubscriptionService | None,
    user: UserRow | None,
) -> bool:
    if (
        order.status != "paid"
        or order.order_kind != "subscription"
        or order.plan_id is None
        or order.subscription_id is not None
        or subscription_service is None
        or user is None
    ):
        return False

    return True


def payment_order_to_dto(order: PaymentOrderRow) -> PaymentOrderDto:
    return PaymentOrderDto(
        id=str(order.id),
        orderNo=order.order_no,
        subject=order.subject,
        amount=cents_to_money(order.amount_cents),
        payType=order.pay_type,
        provider=order.provider,
        status=order.status,
        paymentUrl=order.payment_url,
        createdAt=order.created_at.isoformat(),
        paidAt=order.paid_at.isoformat() if order.paid_at else None,
    )
