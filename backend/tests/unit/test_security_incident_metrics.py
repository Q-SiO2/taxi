import asyncio
from datetime import UTC, datetime

import pytest

from taximobile_api.domains.security_incidents.metrics import (
    SecurityIncidentMetricsUnavailable,
    collect_security_incident_metrics,
)
from taximobile_api.domains.security_incidents.models import SecurityIncidentSeverity


class _Result:
    def __init__(self, rows: list[tuple]) -> None:
        self._rows = rows

    def all(self) -> list[tuple]:
        return self._rows


class _Session:
    def __init__(
        self,
        rows: list[tuple] | None = None,
        failure: Exception | None = None,
    ) -> None:
        self._rows = rows or []
        self._failure = failure

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None

    async def execute(self, _statement):
        if self._failure is not None:
            raise self._failure
        return _Result(self._rows)


def test_security_incident_metrics_fill_all_fixed_severity_buckets() -> None:
    session = _Session(
        [
            (SecurityIncidentSeverity.SEV1, 2, 1, 0, 0),
            ("SEV3", 0, 0, 4, 2),
        ]
    )

    result = asyncio.run(
        collect_security_incident_metrics(
            lambda: session,
            observed_at=datetime(2026, 9, 8, 12, 0, tzinfo=UTC),
        )
    )

    assert result.available is True
    assert [bucket.incident_severity for bucket in result.severities] == [
        "SEV1",
        "SEV2",
        "SEV3",
        "SEV4",
    ]
    assert result.severities[0].open_incidents == 2
    assert result.severities[0].containment_overdue == 1
    assert result.severities[1].open_incidents == 0
    assert result.severities[2].postmortem_pending == 4
    assert result.severities[2].postmortem_overdue == 2


def test_security_incident_metrics_reject_unknown_or_inconsistent_rows() -> None:
    for rows in (
        [("private-dynamic-value", 1, 0, 0, 0)],
        [("SEV2", 1, 2, 0, 0)],
        [("SEV4", 0, 0, 1, 2)],
    ):
        with pytest.raises(
            SecurityIncidentMetricsUnavailable,
            match="Aggregate security incident metrics are unavailable",
        ):
            asyncio.run(collect_security_incident_metrics(lambda: _Session(rows)))


def test_security_incident_metrics_hide_database_failure_details() -> None:
    session = _Session(failure=RuntimeError("password=private connection detail"))

    with pytest.raises(
        SecurityIncidentMetricsUnavailable,
        match="Aggregate security incident metrics are unavailable",
    ) as caught:
        asyncio.run(collect_security_incident_metrics(lambda: session))

    assert "private" not in str(caught.value)


def test_security_incident_metrics_timeout_is_bounded() -> None:
    class _SlowSession(_Session):
        async def execute(self, statement):
            await asyncio.sleep(0.05)
            return await super().execute(statement)

    with pytest.raises(SecurityIncidentMetricsUnavailable):
        asyncio.run(
            collect_security_incident_metrics(
                lambda: _SlowSession(),
                timeout_seconds=0.001,
            )
        )
