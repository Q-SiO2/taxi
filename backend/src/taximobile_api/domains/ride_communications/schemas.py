from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from taximobile_api.domains.ride_communications.models import RideCoordinationCode


class RideCoordinationSenderRole(StrEnum):
    PASSENGER = "PASSENGER"
    DRIVER = "DRIVER"


class RideCoordinationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: RideCoordinationCode


class RideCoordinationMessageResponse(BaseModel):
    id: UUID
    ride_id: UUID
    sender_role: RideCoordinationSenderRole
    code: RideCoordinationCode
    created_at: datetime
