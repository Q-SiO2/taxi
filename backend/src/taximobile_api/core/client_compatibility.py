"""Closed client-build compatibility policy and production request boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
from collections.abc import Awaitable, Callable, Mapping

from starlette.responses import JSONResponse
from starlette.types import Message, Receive, Scope, Send


CLIENT_SURFACE_HEADER = "X-TaxiMobile-Client"
CLIENT_VERSION_HEADER = "X-TaxiMobile-Version"
CLIENT_BUILD_HEADER = "X-TaxiMobile-Build"
CLIENT_POLICY_HEADER = "X-TaxiMobile-Client-Policy"
CLIENT_MINIMUM_VERSION_HEADER = "X-TaxiMobile-Minimum-Version"
CLIENT_RECOMMENDED_VERSION_HEADER = "X-TaxiMobile-Recommended-Version"

_VERSION_PATTERN = re.compile(
    r"(?P<major>0|[1-9][0-9]*)\."
    r"(?P<minor>0|[1-9][0-9]*)\."
    r"(?P<patch>0|[1-9][0-9]*)"
    r"(?:\.(?P<revision>0|[1-9][0-9]*))?"
)
_POLICY_REVISION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_MAX_VERSION_COMPONENT = 2_147_483_647
_MAX_BUILD = 2_147_483_647


class ClientSurface(StrEnum):
    ANDROID_PASSENGER = "ANDROID_PASSENGER"
    ANDROID_DRIVER = "ANDROID_DRIVER"
    IOS_PASSENGER = "IOS_PASSENGER"
    IOS_DRIVER = "IOS_DRIVER"
    WEB_APPLICANT = "WEB_APPLICANT"
    WEB_OPERATIONS = "WEB_OPERATIONS"


class ClientCompatibilityStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    UPGRADE_REQUIRED = "UPGRADE_REQUIRED"


class ClientIdentityError(ValueError):
    """Raised for a missing or malformed closed client-build identity."""


@dataclass(frozen=True, order=True, slots=True)
class ClientVersion:
    major: int
    minor: int
    patch: int
    revision: int = 0

    @classmethod
    def parse(cls, value: str) -> "ClientVersion":
        if not isinstance(value, str) or len(value) > 64:
            raise ClientIdentityError("Client version is invalid.")
        match = _VERSION_PATTERN.fullmatch(value)
        if match is None:
            raise ClientIdentityError("Client version is invalid.")
        components = tuple(int(match.group(name) or 0) for name in ("major", "minor", "patch", "revision"))
        if any(component > _MAX_VERSION_COMPONENT for component in components):
            raise ClientIdentityError("Client version is invalid.")
        return cls(*components)

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}.{self.revision}" if self.revision else base


@dataclass(frozen=True, slots=True)
class ClientBuildIdentity:
    surface: ClientSurface
    version: ClientVersion
    build: int


@dataclass(frozen=True, slots=True)
class ClientCompatibilityResult:
    status: ClientCompatibilityStatus
    surface: ClientSurface
    minimum_version: str
    recommended_version: str
    policy_revision: str
    api_version: str = "v1"


@dataclass(frozen=True, slots=True)
class ClientCompatibilityPolicy:
    revision: str
    minimum_versions: tuple[tuple[str, str], ...]
    recommended_versions: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if _POLICY_REVISION_PATTERN.fullmatch(self.revision) is None:
            raise ValueError("Client policy revision must be a controlled identifier.")
        minimum = self._validated_versions(self.minimum_versions, "minimum")
        recommended = self._validated_versions(self.recommended_versions, "recommended")
        expected = set(ClientSurface)
        if set(minimum) != expected or set(recommended) != expected:
            raise ValueError("Client policy must define every closed client surface exactly once.")
        for surface in expected:
            if recommended[surface] < minimum[surface]:
                raise ValueError(f"Recommended version cannot be below minimum for {surface.value}.")

    @staticmethod
    def _validated_versions(
        values: tuple[tuple[str, str], ...],
        label: str,
    ) -> dict[ClientSurface, ClientVersion]:
        parsed: dict[ClientSurface, ClientVersion] = {}
        for raw_surface, raw_version in values:
            try:
                surface = ClientSurface(raw_surface)
            except ValueError as error:
                raise ValueError(f"Unknown {label} client surface.") from error
            if surface in parsed:
                raise ValueError(f"Duplicate {label} client surface {surface.value}.")
            parsed[surface] = ClientVersion.parse(raw_version)
        return parsed

    def assess(self, identity: ClientBuildIdentity) -> ClientCompatibilityResult:
        minimum = self._validated_versions(self.minimum_versions, "minimum")[identity.surface]
        recommended = self._validated_versions(self.recommended_versions, "recommended")[identity.surface]
        status = (
            ClientCompatibilityStatus.UPGRADE_REQUIRED
            if identity.version < minimum
            else ClientCompatibilityStatus.UPDATE_AVAILABLE
            if identity.version < recommended
            else ClientCompatibilityStatus.SUPPORTED
        )
        return ClientCompatibilityResult(
            status=status,
            surface=identity.surface,
            minimum_version=str(minimum),
            recommended_version=str(recommended),
            policy_revision=self.revision,
        )


def parse_client_identity(headers: Mapping[str, str]) -> ClientBuildIdentity:
    try:
        surface = ClientSurface(headers[CLIENT_SURFACE_HEADER.lower()])
    except (KeyError, ValueError) as error:
        raise ClientIdentityError("Client identity is required.") from error
    try:
        version = ClientVersion.parse(headers[CLIENT_VERSION_HEADER.lower()])
        raw_build = headers[CLIENT_BUILD_HEADER.lower()]
        if not re.fullmatch(r"[1-9][0-9]{0,9}", raw_build):
            raise ValueError
        build = int(raw_build)
        if build > _MAX_BUILD:
            raise ValueError
    except (KeyError, ValueError) as error:
        raise ClientIdentityError("Client identity is required.") from error
    return ClientBuildIdentity(surface=surface, version=version, build=build)


def compatibility_headers(result: ClientCompatibilityResult) -> list[tuple[bytes, bytes]]:
    return [
        (CLIENT_POLICY_HEADER.lower().encode(), result.policy_revision.encode()),
        (CLIENT_MINIMUM_VERSION_HEADER.lower().encode(), result.minimum_version.encode()),
        (CLIENT_RECOMMENDED_VERSION_HEADER.lower().encode(), result.recommended_version.encode()),
    ]


class ClientCompatibilityMiddleware:
    """Require a closed, supported build identity on production-like v1 HTTP calls."""

    def __init__(
        self,
        app: Callable[[Scope, Receive, Send], Awaitable[None]],
        *,
        policy: ClientCompatibilityPolicy,
        api_prefix: str,
        enforced: bool,
    ) -> None:
        self.app = app
        self.policy = policy
        self.api_prefix = api_prefix.rstrip("/")
        self.enforced = enforced
        self.excluded_paths = {
            f"{self.api_prefix}/openapi.json",
            f"{self.api_prefix}/client-compatibility",
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._applies(scope):
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        try:
            identity = parse_client_identity(headers)
            result = self.policy.assess(identity)
        except ClientIdentityError:
            await self._reject(scope, receive, send, None)
            return
        if result.status == ClientCompatibilityStatus.UPGRADE_REQUIRED:
            await self._reject(scope, receive, send, result)
            return

        async def send_with_policy(message: Message) -> None:
            if message["type"] == "http.response.start":
                message["headers"] = list(message.get("headers", [])) + compatibility_headers(result)
            await send(message)

        await self.app(scope, receive, send_with_policy)

    def _applies(self, scope: Scope) -> bool:
        path = str(scope.get("path", ""))
        return (
            self.enforced
            and scope.get("type") == "http"
            and scope.get("method") != "OPTIONS"
            and path.startswith(f"{self.api_prefix}/")
            and path not in self.excluded_paths
        )

    async def _reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        result: ClientCompatibilityResult | None,
    ) -> None:
        details: dict[str, str] = {
            "api_version": "v1",
            "policy_revision": self.policy.revision,
        }
        code = "CLIENT_IDENTITY_REQUIRED"
        message = "A supported TaxiMobile client is required."
        headers: dict[str, str] = {CLIENT_POLICY_HEADER: self.policy.revision}
        if result is not None:
            code = "CLIENT_UPGRADE_REQUIRED"
            message = "This TaxiMobile client must be upgraded before it can continue."
            details.update(
                minimum_version=result.minimum_version,
                recommended_version=result.recommended_version,
            )
            headers.update(
                {
                    CLIENT_MINIMUM_VERSION_HEADER: result.minimum_version,
                    CLIENT_RECOMMENDED_VERSION_HEADER: result.recommended_version,
                }
            )
        response = JSONResponse(
            status_code=426,
            content={"error": {"code": code, "message": message, "details": details}},
            headers=headers,
        )
        await response(scope, receive, send)

