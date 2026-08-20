from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CooperativeMembershipResponse(BaseModel):
    cooperative_id: UUID
    cooperative_name: str
    status: str
    joined_at: datetime | None
    membership_number: str | None
