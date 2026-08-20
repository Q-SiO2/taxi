"""The user-facing support contract. Extra fields are rejected deliberately."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taximobile_api.domains.support.models import SupportCategory


class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: SupportCategory
    subject: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    ride_id: UUID | None = None


class SupportTicketResponse(BaseModel):
    id: UUID
    category: SupportCategory
    subject: str
    description: str
    ride_id: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class SupportTicketListResponse(BaseModel):
    items: list[SupportTicketResponse]
    page: int
    limit: int
    total: int
