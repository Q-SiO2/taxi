"""Resolve a civil clock selection without choosing an overlap or shifting a gap."""

from datetime import UTC, datetime
from functools import lru_cache
from importlib import resources
from zoneinfo import ZoneInfo


class TimeZoneRulesUnavailable(Exception):
    """Configured, packaged rules cannot be used; never fall back to OS rules."""


@lru_cache(maxsize=128)
def _packaged_zone(name: str) -> ZoneInfo:
    try:
        package = resources.files("tzdata")
        names = package.joinpath("zones").read_text(encoding="utf-8").splitlines()
        if name not in names:
            raise TimeZoneRulesUnavailable()
        with package.joinpath("zoneinfo", *name.split("/")).open("rb") as data:
            return ZoneInfo.from_file(data, key=name)
    except (ModuleNotFoundError, OSError, ValueError) as error:
        raise TimeZoneRulesUnavailable() from error


def local_pickup_time_options(local: datetime, zone_name: str) -> list[tuple[datetime, int]]:
    if local.tzinfo is not None or local.second != 0 or local.microsecond != 0:
        raise ValueError("Supply a local date and minute without an offset.")
    zone = _packaged_zone(zone_name)
    options: dict[datetime, int] = {}
    try:
        for fold in (0, 1):
            instant = local.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            returned = instant.astimezone(zone)
            if returned.replace(tzinfo=None) == local:
                offset = returned.utcoffset()
                assert offset is not None
                options[instant] = int(offset.total_seconds())
    except (OverflowError, ValueError) as error:
        raise ValueError("The clock selection is outside the supported date range.") from error
    return sorted(options.items())


def packaged_rules_version() -> str:
    try:
        from tzdata import IANA_VERSION
        return IANA_VERSION
    except ImportError as error:
        raise TimeZoneRulesUnavailable() from error
