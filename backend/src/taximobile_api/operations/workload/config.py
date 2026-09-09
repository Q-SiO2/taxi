"""Fail-closed input boundary for a workload that creates durable test records."""

from dataclasses import dataclass
from math import isfinite
from urllib.parse import urlsplit
from uuid import UUID

from taximobile_api.operations.performance_smoke import is_local_target


@dataclass(frozen=True)
class PassengerWorkloadConfig:
    base_url: str
    city_id: UUID
    pickup: tuple[float, float]
    destination: tuple[float, float]
    confirm_synthetic_target: bool = False
    confirm_nonlocal_target: bool = False
    users: int = 2
    journeys_per_user: int = 2
    interval_seconds: float = 1.0
    request_timeout_seconds: float = 5.0
    duration_seconds: float = 120.0
    p95_budget_ms: float = 1000.0

    def __post_init__(self) -> None:
        if self.confirm_synthetic_target is not True:
            raise ValueError("Confirm an isolated synthetic-only target before creating records.")
        try:
            url = urlsplit(self.base_url)
            port = url.port
            valid = (
                url.scheme in {"http", "https"} and bool(url.hostname)
                and url.username is None and url.password is None
                and url.path in {"", "/"} and not url.query and not url.fragment
                and (port is None or 1 <= port <= 65535)
                and self.base_url.isascii()
                and not any(character.isspace() for character in self.base_url)
                and "\\" not in self.base_url
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Target must be an HTTP origin without credentials, path or query.")
        if not is_local_target(self.base_url):
            if url.scheme != "https" or self.confirm_nonlocal_target is not True:
                raise ValueError("Nonlocal targets require HTTPS and explicit staging confirmation.")
        if not isinstance(self.city_id, UUID):
            raise ValueError("Supply the synthetic city's UUID.")
        for coordinate in (self.pickup, self.destination):
            if len(coordinate) != 2 or any(
                type(value) not in {int, float} or not isfinite(value) or abs(value) > bound
                for value, bound in zip(coordinate, (90, 180))
            ):
                raise ValueError("Coordinates must be finite latitude/longitude pairs.")
        for value, maximum in ((self.users, 50), (self.journeys_per_user, 100)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("Users must be 1..50 and journeys per user 1..100.")
        for value, minimum, maximum in (
            (self.interval_seconds, 0, 60),
            (self.request_timeout_seconds, 0.1, 30),
            (self.duration_seconds, 1, 600),
            (self.p95_budget_ms, 1, 60000),
        ):
            if type(value) not in {int, float} or not isfinite(value) or not minimum <= value <= maximum:
                raise ValueError("Workload timings must be finite and within documented bounds.")

    def ride_payload(self) -> dict:
        return {
            "city_id": str(self.city_id),
            "pickup": {"latitude": self.pickup[0], "longitude": self.pickup[1]},
            "destination": {"latitude": self.destination[0], "longitude": self.destination[1]},
        }


@dataclass(frozen=True)
class OpenLoopPassengerWorkloadConfig(PassengerWorkloadConfig):
    """Constant-arrival extension; ``users`` is the hard in-flight actor cap."""

    arrival_rate_per_second: float = 1.0
    arrival_lag_budget_ms: float = 250.0

    def __post_init__(self) -> None:
        super().__post_init__()
        for value, minimum, maximum in (
            (self.arrival_rate_per_second, 0.01, 100),
            (self.arrival_lag_budget_ms, 1, 60000),
        ):
            if type(value) not in {int, float} or not isfinite(value) or not minimum <= value <= maximum:
                raise ValueError("Open-loop arrival controls must be finite and within documented bounds.")
        planned = self.users * self.journeys_per_user
        if planned > 1000:
            raise ValueError("Open-loop workload may schedule at most 1000 bounded arrivals.")
