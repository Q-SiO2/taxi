"""Pure lifecycle rules for security incidents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from taximobile_api.domains.security_incidents.models import SecurityIncidentStatus


class SecurityIncidentTransition(StrEnum):
    START_CONTAINMENT = "START_CONTAINMENT"
    MARK_CONTAINED = "MARK_CONTAINED"
    START_RECOVERY = "START_RECOVERY"
    MARK_RECOVERED = "MARK_RECOVERED"
    CLOSE = "CLOSE"


class InvalidSecurityIncidentTransition(ValueError):
    """The requested transition does not follow the reviewed lifecycle."""


@dataclass(frozen=True, slots=True)
class TransitionResult:
    status: SecurityIncidentStatus
    contained_at: datetime | None
    recovered_at: datetime | None
    closed_at: datetime | None


_NEXT_STATUS = {
    (SecurityIncidentStatus.OPEN, SecurityIncidentTransition.START_CONTAINMENT): (
        SecurityIncidentStatus.CONTAINING
    ),
    (SecurityIncidentStatus.CONTAINING, SecurityIncidentTransition.MARK_CONTAINED): (
        SecurityIncidentStatus.CONTAINED
    ),
    (SecurityIncidentStatus.CONTAINED, SecurityIncidentTransition.START_RECOVERY): (
        SecurityIncidentStatus.RECOVERING
    ),
    (SecurityIncidentStatus.RECOVERING, SecurityIncidentTransition.MARK_RECOVERED): (
        SecurityIncidentStatus.RECOVERED
    ),
    (SecurityIncidentStatus.RECOVERED, SecurityIncidentTransition.CLOSE): (
        SecurityIncidentStatus.CLOSED
    ),
}


def apply_transition(
    *,
    current_status: SecurityIncidentStatus,
    transition: SecurityIncidentTransition,
    changed_at: datetime,
    contained_at: datetime | None,
    recovered_at: datetime | None,
    closed_at: datetime | None,
) -> TransitionResult:
    """Return lifecycle timestamps for one valid, forward-only transition."""

    next_status = _NEXT_STATUS.get((current_status, transition))
    if next_status is None:
        raise InvalidSecurityIncidentTransition(
            f"{transition.value} is not valid while the incident is {current_status.value}."
        )
    if next_status == SecurityIncidentStatus.CONTAINED:
        contained_at = changed_at
    elif next_status == SecurityIncidentStatus.RECOVERED:
        recovered_at = changed_at
    elif next_status == SecurityIncidentStatus.CLOSED:
        closed_at = changed_at
    return TransitionResult(
        status=next_status,
        contained_at=contained_at,
        recovered_at=recovered_at,
        closed_at=closed_at,
    )
