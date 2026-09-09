from decimal import Decimal
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from taximobile_api.domains.markets.models import ServiceType
from taximobile_api.domains.payments.models import (
    PaymentCapabilityStatus,
    PaymentRecipientStatus,
    RefundReason,
    RefundSettlementMethod,
)


class StrictPaymentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentRecipientCreateRequest(StrictPaymentModel):
    operator_id: UUID
    label: str = Field(min_length=2, max_length=80)
    recipient_name: str = Field(min_length=2, max_length=120)
    bank_account: str | None = Field(default=None, min_length=3, max_length=120)
    wallet_id: str | None = Field(default=None, min_length=3, max_length=120)

    @field_validator("label", "recipient_name", "bank_account", "wallet_id", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def destination_required(self):
        if not self.bank_account and not self.wallet_id:
            raise ValueError("At least one bank account or wallet destination is required.")
        return self


class PaymentRecipientUpdateRequest(PaymentRecipientCreateRequest):
    operator_id: UUID | None = None
    expected_version: int = Field(ge=1)


class PaymentRecipientCommandRequest(StrictPaymentModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PaymentRecipientResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    label: str
    recipient_name: str
    bank_account: str | None
    wallet_id: str | None
    status: PaymentRecipientStatus
    optimistic_version: int
    verified_at: datetime | None
    retired_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentRecipientListResponse(BaseModel):
    items: list[PaymentRecipientResponse]
    page: int
    limit: int
    total: int


class PaymentCapabilityCreateRequest(StrictPaymentModel):
    operator_id: UUID
    service_type: ServiceType
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
    cash_enabled: bool = True
    manual_transfer_enabled: bool = False
    recipient_account_id: UUID | None = None
    effective_from: datetime
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def coherent_methods(self):
        if not self.cash_enabled:
            raise ValueError("Cash must remain enabled.")
        if self.manual_transfer_enabled != (self.recipient_account_id is not None):
            raise ValueError("Manual transfer and recipient account must be configured together.")
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from.")
        return self


class PaymentCapabilityUpdateRequest(StrictPaymentModel):
    expected_version: int = Field(ge=1)
    manual_transfer_enabled: bool
    recipient_account_id: UUID | None = None
    effective_from: datetime
    effective_until: datetime | None = None

    @model_validator(mode="after")
    def coherent_methods(self):
        if self.manual_transfer_enabled != (self.recipient_account_id is not None):
            raise ValueError("Manual transfer and recipient account must be configured together.")
        if self.effective_until is not None and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from.")
        return self


class PaymentCapabilityCommandRequest(StrictPaymentModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=240)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PaymentCapabilityResponse(BaseModel):
    id: UUID
    city_id: UUID
    operator_id: UUID
    service_type: ServiceType
    version: str
    status: PaymentCapabilityStatus
    cash_enabled: bool
    manual_transfer_enabled: bool
    recipient_account_id: UUID | None
    effective_from: datetime
    effective_until: datetime | None
    optimistic_version: int
    submitted_at: datetime | None
    approved_at: datetime | None
    activated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentCapabilityListResponse(BaseModel):
    items: list[PaymentCapabilityResponse]
    page: int
    limit: int
    total: int


class OperationsManualTransferResponse(BaseModel):
    claim_id: UUID
    payment_id: UUID
    ride_id: UUID
    city_id: UUID
    operator_id: UUID
    recipient_account_id: UUID | None
    recipient_label: str | None
    payment_reference: str
    payer_reference: str | None
    amount: Decimal
    currency: str
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None = None


class OperationsManualTransferListResponse(BaseModel):
    items: list[OperationsManualTransferResponse]
    page: int
    limit: int
    total: int


class PaymentResponse(BaseModel):
    id: UUID
    ride_id: UUID
    amount: Decimal
    currency: str
    method: str
    status: str


class ManualTransferClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payer_reference: str | None = Field(
        default=None,
        min_length=3,
        max_length=80,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )

    @field_validator("payer_reference", mode="before")
    @classmethod
    def normalize_reference(cls, value: object) -> object:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None


class ManualTransferClaimResponse(BaseModel):
    id: UUID
    payment_id: UUID
    ride_id: UUID
    status: str
    submitted_at: datetime


class ManualTransferReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settlement_reference: str = Field(
        min_length=3,
        max_length=120,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )

    @field_validator("settlement_reference", mode="before")
    @classmethod
    def normalize_settlement_reference(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ManualTransferRejectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=3, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ManualTransferAdminResponse(BaseModel):
    claim_id: UUID
    payment_id: UUID
    ride_id: UUID
    payment_reference: str
    payer_reference: str | None
    amount: Decimal
    currency: str
    status: str
    submitted_at: datetime
    reviewed_at: datetime | None = None


class ManualTransferAdminListResponse(BaseModel):
    items: list[ManualTransferAdminResponse]
    page: int
    limit: int
    total: int


class PaymentRefundCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    reason: RefundReason
    settlement_method: RefundSettlementMethod
    settlement_reference: str = Field(
        min_length=3,
        max_length=120,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$",
    )
    operator_note: str = Field(min_length=3, max_length=500)

    @field_validator("settlement_reference", "operator_note", mode="before")
    @classmethod
    def normalize_refund_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PaymentRefundAdminResponse(BaseModel):
    id: UUID
    payment_id: UUID
    ride_id: UUID
    city_id: UUID
    operator_id: UUID
    amount: Decimal
    currency: str
    reason: RefundReason
    settlement_method: RefundSettlementMethod
    settlement_reference: str
    operator_note: str
    driver_recovery_amount: Decimal
    operator_funded_amount: Decimal
    authorized_by_user_id: UUID
    refunded_at: datetime
    payment_status: str
    remaining_refundable_amount: Decimal


class PaymentRefundAdminListResponse(BaseModel):
    items: list[PaymentRefundAdminResponse]
    page: int
    limit: int
    total: int


class PassengerRefundResponse(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    reason: RefundReason
    refunded_at: datetime


class PassengerRefundSummaryResponse(BaseModel):
    refunded_amount: Decimal
    net_paid_amount: Decimal
    currency: str
    items: list[PassengerRefundResponse]


class DriverEarningResponse(BaseModel):
    id: UUID
    ride_id: UUID
    gross: Decimal
    fees: Decimal
    adjustments: Decimal
    net: Decimal
    transport_fare: Decimal
    scheduling_surcharge: Decimal
    operator_service_fee: Decimal
    operator_fee_funding_mode: str | None
    operator_allocation: Decimal
    currency: str
    settled_at: datetime


class EarningsResponse(BaseModel):
    currency: str
    gross: Decimal
    fees: Decimal
    adjustments: Decimal
    net: Decimal
    transport_fare: Decimal
    scheduling_surcharge: Decimal
    operator_service_fee: Decimal
    operator_allocation: Decimal
    settled_through: datetime | None
    count: int
    page: int
    limit: int
    items: list[DriverEarningResponse]
