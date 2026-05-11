from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CreateZpayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    amount: str
    payType: str = "alipay"


class CreateSubscriptionZpayOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planId: str
    payType: str = "alipay"


class PaymentOrderDto(BaseModel):
    id: str
    orderNo: str
    subject: str
    amount: str
    payType: str
    provider: str
    status: str
    paymentUrl: str | None
    createdAt: str
    paidAt: str | None = None


class PaymentOrderEnvelope(BaseModel):
    order: PaymentOrderDto
