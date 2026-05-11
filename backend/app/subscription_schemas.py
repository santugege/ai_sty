from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


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

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Plan code cannot be blank.")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Plan name cannot be blank.")
        return normalized

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: str) -> str:
        try:
            amount = Decimal(str(value))
        except InvalidOperation as error:
            raise ValueError("Plan price is invalid.") from error
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
            raise ValueError("Plan price is invalid.")
        return f"{amount:.2f}"

    @model_validator(mode="after")
    def validate_limits(self) -> SubscriptionPlanInput:
        if self.dailyImageLimit <= 0:
            raise ValueError("Daily image limit must be positive.")
        if self.monthlyImageLimit <= 0:
            raise ValueError("Monthly image limit must be positive.")
        if self.dailyImageLimit > self.monthlyImageLimit:
            raise ValueError("Daily image limit cannot exceed monthly image limit.")
        return self


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
