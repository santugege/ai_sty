from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaymentOrderRow(Base):
    __tablename__ = "payment_orders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_no: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    user_public_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="zpay")
    provider_trade_no: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("subscription_plans.id"), nullable=True, index=True
    )
    order_kind: Mapped[str] = mapped_column(Text, nullable=False, default="payment")
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("user_subscriptions.id"), nullable=True, index=True
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    pay_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    payment_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_callback: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
