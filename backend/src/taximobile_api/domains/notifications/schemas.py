from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from taximobile_api.domains.notifications.models import DevicePlatform, DeviceRegistrationKind


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    data: dict[str, str]
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    page: int
    limit: int
    total: int


class DeviceRegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: DevicePlatform
    registration_kind: DeviceRegistrationKind
    registration_id: str = Field(min_length=1, max_length=512)

    @field_validator("registration_id")
    @classmethod
    def registration_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Token must not be blank.")
        return value


class DeviceRevocationRequest(DeviceRegistrationRequest):
    pass


class DeviceRegistrationResponse(BaseModel):
    id: UUID
    platform: DevicePlatform
    registration_kind: DeviceRegistrationKind
