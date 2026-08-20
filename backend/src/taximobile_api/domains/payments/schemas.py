from decimal import Decimal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PaymentResponse(BaseModel):
    id: UUID
    ride_id: UUID
    amount: Decimal
    currency: str
    method: str
    status: str


class DriverEarningResponse(BaseModel):
    id: UUID
    ride_id: UUID
    gross: Decimal
    fees: Decimal
    adjustments: Decimal
    net: Decimal
    currency: str
    settled_at: datetime


class EarningsResponse(BaseModel):
    currency: str
    gross: Decimal
    fees: Decimal
    adjustments: Decimal
    net: Decimal
    settled_through: datetime | None
    count: int
    page: int
    limit: int
    items: list[DriverEarningResponse]
