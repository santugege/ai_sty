from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.payment_models import PaymentOrderRow


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_order(self, row: PaymentOrderRow) -> PaymentOrderRow:
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_order_no(self, order_no: str) -> PaymentOrderRow | None:
        return self.db.scalar(
            select(PaymentOrderRow).where(PaymentOrderRow.order_no == order_no)
        )

    def get_paid_subscription_order_by_subscription_id(
        self,
        subscription_id,
    ) -> PaymentOrderRow | None:
        return self.db.scalar(
            select(PaymentOrderRow)
            .where(
                PaymentOrderRow.order_kind == "subscription",
                PaymentOrderRow.status == "paid",
                PaymentOrderRow.subscription_id == subscription_id,
            )
            .order_by(PaymentOrderRow.created_at.desc())
        )

    def save(self, order: PaymentOrderRow) -> PaymentOrderRow:
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def flush(self, order: PaymentOrderRow) -> PaymentOrderRow:
        self.db.add(order)
        self.db.flush()
        return order

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    def refresh(self, order: PaymentOrderRow) -> PaymentOrderRow:
        self.db.refresh(order)
        return order
