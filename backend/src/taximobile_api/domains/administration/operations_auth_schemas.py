"""Request/response contracts for isolated browser operations sessions."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationsLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    device_label: str | None = Field(default=None, max_length=120)


class OperationsRefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=32, max_length=512)


class OperationsTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    csrf_token: str | None = None
    token_type: str = "bearer"
    expires_in: int
    authentication_strength: str = "PASSWORD_ONLY_LOCAL"


class OperationsLogoutResponse(BaseModel):
    success: bool = True


class OperationsGrantSessionResponse(BaseModel):
    id: UUID
    role_template: str
    market_id: UUID | None
    operator_id: UUID | None
    city_id: UUID | None
    permissions: list[str]


class OperationsSessionResponse(BaseModel):
    user_id: UUID
    session_id: UUID
    grants: list[OperationsGrantSessionResponse]
    expires_at: datetime | None = None
    mfa_verified_at: datetime | None = None
    authentication_strength: str


class MfaChallengeResponse(BaseModel):
    challenge_id: UUID
    expires_in: int
    authentication_methods: list[str] = Field(
        default_factory=lambda: ["TOTP", "RECOVERY_CODE"]
    )


class MfaVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: UUID
    code: str = Field(min_length=6, max_length=32, pattern=r"^[A-Za-z0-9-]+$")


class MfaStepUpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=32, pattern=r"^[A-Za-z0-9-]+$")


class MfaStepUpResponse(BaseModel):
    verified_at: datetime
    authentication_strength: str
