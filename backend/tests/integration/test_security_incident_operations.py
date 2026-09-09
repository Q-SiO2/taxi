"""PostGIS proof for the scoped append-only security-incident workflow."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from os import getenv
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.core.config import Settings
from taximobile_api.domains.administration.bootstrap import (
    bootstrap_initial_platform_grant,
)
from taximobile_api.domains.administration.models import (
    AdministrativeGrant,
    AdministrativeRoleTemplate,
    AuditLog,
)
from taximobile_api.domains.auth.bootstrap import bootstrap_initial_administrator
from taximobile_api.domains.auth.models import User
from taximobile_api.domains.markets.models import Market, MarketStatus
from taximobile_api.domains.security_incidents.models import (
    SecurityIncident,
    SecurityIncidentCategory,
    SecurityIncidentResponsibility,
    SecurityIncidentResponsibilityAssignment,
    SecurityIncidentSeverity,
    SecurityIncidentStatus,
    SecurityIncidentTimelineEntry,
)
from taximobile_api.domains.security_incidents.metrics import (
    collect_security_incident_metrics,
)
from taximobile_api.main import create_app


pytestmark = pytest.mark.integration

ADMIN_EMAIL = "security-incident-admin@example.test"
ADMIN_PASSWORD = "Security-incident-integration-password-2026"


def integration_settings() -> Settings:
    if getenv("TAXIMOBILE_RUN_INTEGRATION") != "1":
        pytest.skip(
            "Set TAXIMOBILE_RUN_INTEGRATION=1 with an isolated migrated PostGIS database."
        )
    settings = Settings.from_environment()
    if settings.environment != "test" or "taximobile_ci" not in settings.database_url:
        pytest.fail(
            "Integration tests require TAXIMOBILE_ENV=test and an isolated taximobile_ci database."
        )
    assert settings.operations_password_login_enabled
    return settings


async def seed_administrator(settings: Settings) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_administrator(
                    session,
                    email=ADMIN_EMAIL,
                    password=ADMIN_PASSWORD,
                )
        async with sessions() as session:
            async with session.begin():
                await bootstrap_initial_platform_grant(
                    session,
                    admin_email=ADMIN_EMAIL,
                    market_code="MA",
                )
    finally:
        await engine.dispose()


async def first_incident_audit_id(settings: Settings, incident_id: UUID) -> UUID:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            audit_id = await session.scalar(
                select(AuditLog.id).where(
                    AuditLog.resource_id == incident_id,
                    AuditLog.action == "SECURITY_INCIDENT_CREATED",
                )
            )
            assert audit_id is not None
            return audit_id
    finally:
        await engine.dispose()


async def incident_metrics(settings: Settings, observed_at: datetime):
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        return await collect_security_incident_metrics(
            sessions,
            observed_at=observed_at,
        )
    finally:
        await engine.dispose()


async def seed_out_of_scope_incident(settings: Settings, now: datetime) -> UUID:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                actor_id = await session.scalar(
                    select(User.id).where(User.email == ADMIN_EMAIL)
                )
                assert actor_id is not None
                market = Market(
                    code="ZZ",
                    name="Out-of-scope synthetic market",
                    default_currency="MAD",
                    status=MarketStatus.ACTIVE,
                    created_at=now,
                    updated_at=now,
                )
                session.add(market)
                await session.flush()
                incident_id = uuid4()
                session.add(
                    SecurityIncident(
                        id=incident_id,
                        reference=f"SEC-{incident_id.hex.upper()}",
                        market_id=market.id,
                        severity=SecurityIncidentSeverity.SEV4,
                        category=SecurityIncidentCategory.OTHER,
                        status=SecurityIncidentStatus.OPEN,
                        summary="Synthetic incident outside the administrator market scope.",
                        reported_by_user_id=actor_id,
                        lead_user_id=actor_id,
                        detected_at=now - timedelta(minutes=1),
                        opened_at=now,
                        containment_due_at=now + timedelta(days=1),
                        optimistic_version=1,
                        created_at=now,
                        updated_at=now,
                    )
                )
            return incident_id
    finally:
        await engine.dispose()


async def seed_eligible_responder(settings: Settings, market_id: UUID) -> UUID:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                actor_id = await session.scalar(
                    select(User.id).where(User.email == ADMIN_EMAIL)
                )
                assert actor_id is not None
                responder = User(
                    email=f"security-responder-{uuid4().hex}@example.test",
                    password_hash="!inert-security-responder",
                )
                session.add(responder)
                await session.flush()
                session.add(
                    AdministrativeGrant(
                        user_id=responder.id,
                        role_template=AdministrativeRoleTemplate.PLATFORM_ADMIN,
                        market_id=market_id,
                        granted_by_user_id=actor_id,
                        grant_reason="Synthetic incident responsibility test grant.",
                    )
                )
            return responder.id
    finally:
        await engine.dispose()


async def assert_audit_redaction_and_append_only(
    settings: Settings,
    incident_id: UUID,
    private_summary: str,
) -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            audits = list(
                await session.scalars(
                    select(AuditLog).where(AuditLog.resource_id == incident_id)
                )
            )
            assert len(audits) == 10
            assert private_summary not in repr([entry.changes for entry in audits])

        async with sessions() as session:
            assignment_id = await session.scalar(
                select(SecurityIncidentResponsibilityAssignment.id)
                .where(
                    SecurityIncidentResponsibilityAssignment.incident_id
                    == incident_id,
                    SecurityIncidentResponsibilityAssignment.released_at.is_(None),
                )
                .limit(1)
            )
            assert assignment_id is not None
            with pytest.raises(DBAPIError) as captured:
                await session.execute(
                    update(SecurityIncidentResponsibilityAssignment)
                    .where(
                        SecurityIncidentResponsibilityAssignment.id == assignment_id
                    )
                    .values(assignment_reference="MUTATION-ATTEMPT")
                )
                await session.commit()
            assert getattr(captured.value.orig, "sqlstate", None) == "55000"
            await session.rollback()

        async with sessions() as session:
            entry_id = await session.scalar(
                select(SecurityIncidentTimelineEntry.id)
                .where(SecurityIncidentTimelineEntry.incident_id == incident_id)
                .order_by(SecurityIncidentTimelineEntry.sequence.asc())
                .limit(1)
            )
            assert entry_id is not None
            with pytest.raises(DBAPIError) as captured:
                await session.execute(
                    update(SecurityIncidentTimelineEntry)
                    .where(SecurityIncidentTimelineEntry.id == entry_id)
                    .values(summary="Attempted mutation")
                )
                await session.commit()
            assert getattr(captured.value.orig, "sqlstate", None) == "55000"
            await session.rollback()
    finally:
        await engine.dispose()


def expect(response, status_code: int):
    assert response.status_code == status_code, response.text
    return response.json()


def test_concurrent_responsibility_assignments_have_one_authoritative_winner() -> None:
    async def prove() -> None:
        settings = integration_settings()
        await seed_administrator(settings)
        app = create_app(settings=settings)
        transport = httpx.ASGITransport(app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
            trust_env=False,
        ) as client:
            login = expect(
                await client.post(
                    "/api/v1/operations/auth/login",
                    json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                ),
                200,
            )
            headers = {"Authorization": f"Bearer {login['access_token']}"}
            market_id = UUID(
                expect(
                    await client.get("/api/v1/operations/markets", headers=headers),
                    200,
                )["items"][0]["id"]
            )
            now = datetime.now(UTC)
            incident = expect(
                await client.post(
                    "/api/v1/operations/security-incidents",
                    headers={**headers, "Idempotency-Key": "incident-race-create"},
                    json={
                        "market_id": str(market_id),
                        "severity": "SEV2",
                        "category": "ACCOUNT_COMPROMISE",
                        "summary": "Synthetic responsibility race with no customer data.",
                        "detected_at": (now - timedelta(minutes=1)).isoformat(),
                        "containment_due_at": (now + timedelta(hours=2)).isoformat(),
                    },
                ),
                201,
            )
            responders = [
                await seed_eligible_responder(settings, market_id),
                await seed_eligible_responder(settings, market_id),
            ]
            assignment_time = datetime.now(UTC).isoformat()

            async def assign(index: int):
                return await client.post(
                    f"/api/v1/operations/security-incidents/{incident['id']}"
                    "/responsibilities/OPERATIONS_LIAISON/assign",
                    headers={
                        **headers,
                        "Idempotency-Key": f"incident-role-race-{index}",
                    },
                    json={
                        "expected_version": 1,
                        "assigned_user_id": str(responders[index]),
                        "occurred_at": assignment_time,
                        "external_reference": "ROSTER-SEC-RACE-001",
                    },
                )

            first, second = await asyncio.wait_for(
                asyncio.gather(assign(0), assign(1)),
                timeout=10,
            )
            assert sorted([first.status_code, second.status_code]) == [201, 409]
            winner = first if first.status_code == 201 else second
            assert winner.json()["incident_version"] == 2
            assert winner.json()["assigned_user_id"] in {
                str(responders[0]),
                str(responders[1]),
            }

            detail = expect(
                await client.get(
                    f"/api/v1/operations/security-incidents/{incident['id']}",
                    headers=headers,
                ),
                200,
            )
            assignments = expect(
                await client.get(
                    f"/api/v1/operations/security-incidents/{incident['id']}"
                    "/responsibilities",
                    headers=headers,
                ),
                200,
            )
            timeline = expect(
                await client.get(
                    f"/api/v1/operations/security-incidents/{incident['id']}/timeline",
                    headers=headers,
                ),
                200,
            )
            assert detail["optimistic_version"] == 2
            assert assignments["total"] == 2
            assert sum(
                item["responsibility"] == "OPERATIONS_LIAISON"
                and item["released_at"] is None
                for item in assignments["items"]
            ) == 1
            assert timeline["total"] == 2
            assert timeline["items"][-1]["kind"] == "RESPONSIBILITY_CHANGED"

    asyncio.run(prove())


def test_security_incident_scope_timeline_idempotency_and_lifecycle() -> None:
    settings = integration_settings()
    asyncio.run(seed_administrator(settings))
    now = datetime.now(UTC)
    out_of_scope_incident_id = asyncio.run(seed_out_of_scope_incident(settings, now))
    private_summary = "Synthetic provider credential exposure without customer data."

    with TestClient(create_app(settings=settings)) as client:
        login = expect(
            client.post(
                "/api/v1/operations/auth/login",
                json={"identifier": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            ),
            200,
        )
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        market_id = expect(
            client.get("/api/v1/operations/markets", headers=headers),
            200,
        )["items"][0]["id"]

        creation_payload = {
            "market_id": market_id,
            "severity": "SEV2",
            "category": "PROVIDER_CREDENTIAL_EXPOSURE",
            "summary": private_summary,
            "detected_at": (now - timedelta(minutes=1)).isoformat(),
            "containment_due_at": (now + timedelta(hours=2)).isoformat(),
        }
        create_headers = {**headers, "Idempotency-Key": "incident-create-001"}
        created = expect(
            client.post(
                "/api/v1/operations/security-incidents",
                headers=create_headers,
                json=creation_payload,
            ),
            201,
        )
        replayed = expect(
            client.post(
                "/api/v1/operations/security-incidents",
                headers=create_headers,
                json=creation_payload,
            ),
            201,
        )
        assert replayed == created
        assert created["reference"].startswith("SEC-")
        assert created["status"] == "OPEN"
        incident_id = UUID(created["id"])

        initial_responsibilities = expect(
            client.get(
                f"/api/v1/operations/security-incidents/{incident_id}/responsibilities",
                headers=headers,
            ),
            200,
        )
        assert initial_responsibilities["total"] == 1
        assert (
            initial_responsibilities["items"][0]["responsibility"]
            == "SECURITY_RESPONSE_LEAD"
        )
        assert initial_responsibilities["items"][0]["assigned_user_id"] == created[
            "lead_user_id"
        ]
        responder_id = asyncio.run(
            seed_eligible_responder(settings, UUID(market_id))
        )
        assignment_time = datetime.now(UTC).isoformat()
        ineligible_assignment = client.post(
            f"/api/v1/operations/security-incidents/{incident_id}/responsibilities/OPERATIONS_LIAISON/assign",
            headers={**headers, "Idempotency-Key": "incident-role-ineligible"},
            json={
                "expected_version": 1,
                "assigned_user_id": str(uuid4()),
                "occurred_at": assignment_time,
                "external_reference": "ROSTER-SEC-001",
            },
        )
        assert ineligible_assignment.status_code == 409
        communications_payload = {
            "expected_version": 1,
            "assigned_user_id": str(responder_id),
            "occurred_at": assignment_time,
            "external_reference": "ROSTER-SEC-001",
        }
        communications_headers = {
            **headers,
            "Idempotency-Key": "incident-role-communications",
        }
        communications = expect(
            client.post(
                f"/api/v1/operations/security-incidents/{incident_id}/responsibilities/COMMUNICATIONS_LEAD/assign",
                headers=communications_headers,
                json=communications_payload,
            ),
            201,
        )
        assert communications["incident_version"] == 2
        assert communications["assigned_user_id"] == str(responder_id)
        assert expect(
            client.post(
                f"/api/v1/operations/security-incidents/{incident_id}/responsibilities/COMMUNICATIONS_LEAD/assign",
                headers=communications_headers,
                json=communications_payload,
            ),
            201,
        ) == communications
        response_lead = expect(
            client.post(
                f"/api/v1/operations/security-incidents/{incident_id}/responsibilities/SECURITY_RESPONSE_LEAD/assign",
                headers={**headers, "Idempotency-Key": "incident-role-response-lead"},
                json={
                    **communications_payload,
                    "expected_version": 2,
                    "external_reference": "ROSTER-SEC-002",
                },
            ),
            201,
        )
        assert response_lead["incident_version"] == 3
        responsibilities = expect(
            client.get(
                f"/api/v1/operations/security-incidents/{incident_id}/responsibilities",
                headers=headers,
            ),
            200,
        )
        assert responsibilities["total"] == 3
        assert sum(item["released_at"] is None for item in responsibilities["items"]) == 2
        refreshed_incident = expect(
            client.get(
                f"/api/v1/operations/security-incidents/{incident_id}",
                headers=headers,
            ),
            200,
        )
        assert refreshed_incident["lead_user_id"] == str(responder_id)
        assert refreshed_incident["optimistic_version"] == 3

        assert expect(
            client.get("/api/v1/operations/security-incidents", headers=headers),
            200,
        )["total"] == 1
        assert client.get(
            f"/api/v1/operations/security-incidents/{out_of_scope_incident_id}",
            headers=headers,
        ).status_code == 404
        audit_log_id = asyncio.run(first_incident_audit_id(settings, incident_id))
        timeline_payload = {
            "kind": "EVIDENCE_LINKED",
            "summary": "Linked the immutable creation audit for the synthetic exercise.",
            "occurred_at": now.isoformat(),
            "audit_log_id": str(audit_log_id),
            "external_reference": "DRILL-SEC-001",
        }
        timeline_headers = {**headers, "Idempotency-Key": "incident-event-001"}
        timeline_entry = expect(
            client.post(
                f"/api/v1/operations/security-incidents/{incident_id}/timeline",
                headers=timeline_headers,
                json=timeline_payload,
            ),
            201,
        )
        assert timeline_entry["sequence"] == 4
        assert expect(
            client.post(
                f"/api/v1/operations/security-incidents/{incident_id}/timeline",
                headers=timeline_headers,
                json=timeline_payload,
            ),
            201,
        ) == timeline_entry

        version = 3
        transitions = [
            ("START_CONTAINMENT", "CONTAINING"),
            ("MARK_CONTAINED", "CONTAINED"),
            ("START_RECOVERY", "RECOVERING"),
            ("MARK_RECOVERED", "RECOVERED"),
            ("CLOSE", "CLOSED"),
        ]
        for index, (transition, expected_status) in enumerate(transitions, start=1):
            if transition == "START_RECOVERY":
                chronological_refusal = client.post(
                    f"/api/v1/operations/security-incidents/{incident_id}/transitions",
                    headers={
                        **headers,
                        "Idempotency-Key": "incident-transition-backdated",
                    },
                    json={
                        "transition": transition,
                        "expected_version": version,
                        "summary": "A backdated recovery milestone must be rejected safely.",
                        "occurred_at": created["detected_at"],
                    },
                )
                assert chronological_refusal.status_code == 422
            payload = {
                "transition": transition,
                "expected_version": version,
                "summary": f"Synthetic drill recorded lifecycle action {transition} safely.",
                "occurred_at": datetime.now(UTC).isoformat(),
            }
            if transition == "CLOSE":
                payload["postmortem_due_at"] = (now + timedelta(days=7)).isoformat()
            updated = expect(
                client.post(
                    f"/api/v1/operations/security-incidents/{incident_id}/transitions",
                    headers={
                        **headers,
                        "Idempotency-Key": f"incident-transition-{index:03d}",
                    },
                    json=payload,
                ),
                200,
            )
            version += 1
            assert updated["status"] == expected_status
            assert updated["optimistic_version"] == version

        stale = client.post(
            f"/api/v1/operations/security-incidents/{incident_id}/transitions",
            headers={**headers, "Idempotency-Key": "incident-transition-stale"},
            json={
                "transition": "START_CONTAINMENT",
                "expected_version": 1,
                "summary": "This stale command must be refused by version authority.",
                "occurred_at": datetime.now(UTC).isoformat(),
            },
        )
        assert stale.status_code == 409

        deadline_snapshot = asyncio.run(
            incident_metrics(settings, now + timedelta(days=8))
        )
        by_severity = {
            item.incident_severity: item for item in deadline_snapshot.severities
        }
        assert by_severity["SEV2"].open_incidents == 0
        assert by_severity["SEV2"].postmortem_pending == 1
        assert by_severity["SEV2"].postmortem_overdue == 1
        assert by_severity["SEV4"].open_incidents == 1
        assert by_severity["SEV4"].containment_overdue == 1

        postmortem_payload = {
            "expected_version": version,
            "outcome": "FOLLOW_UP_REQUIRED",
            "summary": "The controlled exercise produced tracked follow-up remediation work.",
            "occurred_at": datetime.now(UTC).isoformat(),
            "audit_log_id": str(audit_log_id),
            "external_reference": "POSTMORTEM-SEC-001",
        }
        postmortem_headers = {
            **headers,
            "Idempotency-Key": "incident-postmortem-complete-001",
        }
        completed = expect(
            client.post(
                f"/api/v1/operations/security-incidents/{incident_id}/postmortem/complete",
                headers=postmortem_headers,
                json=postmortem_payload,
            ),
            200,
        )
        assert completed["postmortem_outcome"] == "FOLLOW_UP_REQUIRED"
        assert completed["postmortem_completed_at"] is not None
        assert completed["postmortem_completed_by_user_id"] == created["lead_user_id"]
        assert completed["optimistic_version"] == version + 1
        assert expect(
            client.post(
                f"/api/v1/operations/security-incidents/{incident_id}/postmortem/complete",
                headers=postmortem_headers,
                json=postmortem_payload,
            ),
            200,
        ) == completed
        duplicate_completion = client.post(
            f"/api/v1/operations/security-incidents/{incident_id}/postmortem/complete",
            headers={**headers, "Idempotency-Key": "incident-postmortem-duplicate"},
            json={**postmortem_payload, "expected_version": version + 1},
        )
        assert duplicate_completion.status_code == 409

        completed_snapshot = asyncio.run(
            incident_metrics(settings, now + timedelta(days=8))
        )
        completed_by_severity = {
            item.incident_severity: item for item in completed_snapshot.severities
        }
        assert completed_by_severity["SEV2"].postmortem_pending == 0
        assert completed_by_severity["SEV2"].postmortem_overdue == 0

        timeline = expect(
            client.get(
                f"/api/v1/operations/security-incidents/{incident_id}/timeline",
                headers=headers,
            ),
            200,
        )
        assert timeline["total"] == 10
        assert [item["sequence"] for item in timeline["items"]] == list(range(1, 11))
        assert sum(
            item["kind"] == "RESPONSIBILITY_CHANGED"
            for item in timeline["items"]
        ) == 2
        assert timeline["items"][-1]["kind"] == "POSTMORTEM_ACTION"

    asyncio.run(
        assert_audit_redaction_and_append_only(
            settings,
            incident_id,
            private_summary,
        )
    )
