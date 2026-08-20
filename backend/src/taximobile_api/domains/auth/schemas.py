"""Public auth request/response schemas. Client input never carries roles or status."""

from uuid import UUID
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_moroccan_phone_number(value: str) -> str:
    """Canonicalize common Moroccan mobile/landline input to E.164-like +212."""
    compact = re.sub(r"[\s().-]", "", value)
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    if compact.startswith("0"):
        compact = "+212" + compact[1:]
    if not (compact.startswith("+212") and len(compact) == 13 and compact[4:].isdigit()):
        raise ValueError("Use a Moroccan phone number such as +212600000000.")
    return compact


def normalized_login_identifier(value: str) -> str:
    """Normalize an email or accepted phone spelling without rejecting email login."""
    candidate = value.strip()
    if "@" in candidate:
        return candidate.lower()
    try:
        return normalize_moroccan_phone_number(candidate)
    except ValueError:
        return candidate.lower()


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_number: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=320)
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def has_identifier(self) -> "RegisterRequest":
        if not self.phone_number and not self.email:
            raise ValueError("Provide a phone number or email address.")
        return self

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Provide a valid email address.")
        return normalized

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_moroccan_phone_number(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)
    device_label: str | None = Field(default=None, max_length=120)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str = Field(min_length=20, max_length=512)


class UserSummary(BaseModel):
    id: UUID
    phone_number: str | None
    email: str | None


class RegisterResponse(BaseModel):
    user: UserSummary


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900


class CurrentUserResponse(BaseModel):
    id: UUID
    roles: list[str]
    profile: dict[str, str]


class PassengerProfileResponse(BaseModel):
    id: UUID
    display_name: str


class PassengerProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("display_name", mode="before")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display name must not be blank.")
        return value


class LogoutResponse(BaseModel):
    success: bool = True
