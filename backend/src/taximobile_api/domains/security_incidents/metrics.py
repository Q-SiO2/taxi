"""Privacy-bounded deadline measurements for the security incident register."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import (
    KNOWN_SECURITY_INCIDENT_SEVERITIES,
    SecurityIncidentMetrics,
    SecurityIncidentSeverityMetrics,
)
from taximobile_api.domains.security_incidents.models import (
    SecurityIncident,
    SecurityIncidentStatus,
)


class SecurityIncidentMetricsUnavailable(RuntimeError):
    """The aggregate incident-deadline snapshot could not be read safely."""


async def collect_security_incident_metrics(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    observed_at: datetime | None = None,
    timeout_seconds: float = 5.0,
) -> SecurityIncidentMetrics:
    """Read fixed severity counts without loading incident content or identities."""

    now = observed_at or datetime.now(UTC)
    open_incident = SecurityIncident.status != SecurityIncidentStatus.CLOSED
    containment_overdue = and_(
        SecurityIncident.contained_at.is_(None),
        SecurityIncident.containment_due_at < now,
    )
    postmortem_pending = and_(
        SecurityIncident.status == SecurityIncidentStatus.CLOSED,
        SecurityIncident.postmortem_completed_at.is_(None),
    )
    postmortem_overdue = and_(
        postmortem_pending,
        SecurityIncident.postmortem_due_at < now,
    )
    statement = (
        select(
            SecurityIncident.severity,
            func.count().filter(open_incident),
            func.count().filter(containment_overdue),
            func.count().filter(postmortem_pending),
            func.count().filter(postmortem_overdue),
        )
        .group_by(SecurityIncident.severity)
        .order_by(SecurityIncident.severity)
    )
    try:
        async with asyncio.timeout(timeout_seconds):
            async with session_factory() as session:
                rows = (await session.execute(statement)).all()
        totals = {
            severity: SecurityIncidentSeverityMetrics(incident_severity=severity)
            for severity in KNOWN_SECURITY_INCIDENT_SEVERITIES
        }
        for raw_severity, opened, containment, pending, overdue in rows:
            severity = getattr(raw_severity, "value", raw_severity)
            totals[severity] = SecurityIncidentSeverityMetrics(
                incident_severity=severity,
                open_incidents=int(opened),
                containment_overdue=int(containment),
                postmortem_pending=int(pending),
                postmortem_overdue=int(overdue),
            )
        return SecurityIncidentMetrics(
            available=True,
            severities=tuple(
                totals[severity] for severity in KNOWN_SECURITY_INCIDENT_SEVERITIES
            ),
        )
    except Exception as error:
        # Database, timeout and malformed-result details can contain connection
        # or schema information. Collapse them into one stable operational fact.
        raise SecurityIncidentMetricsUnavailable(
            "Aggregate security incident metrics are unavailable."
        ) from error
