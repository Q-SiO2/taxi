"""Guarded selective replay for reviewed transactional-outbox dead letters."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from os import getenv
import re
import sys
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from taximobile_api.domains.outbox.models import OutboxEvent


MAX_REPLAY_EVENTS = 100
INCIDENT_REFERENCE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{2,79}")


class ReplayRefused(ValueError):
    """Raised when a requested replay does not satisfy the incident guardrails."""


@dataclass(frozen=True, slots=True)
class ReplayRequest:
    event_ids: tuple[UUID, ...]
    expected_database_host: str
    expected_database_name: str
    incident_reference: str


def validate_request(
    *,
    database_url: str,
    event_ids: tuple[UUID, ...],
    expected_database_host: str,
    expected_database_name: str,
    incident_reference: str,
) -> ReplayRequest:
    if not event_ids or len(event_ids) > MAX_REPLAY_EVENTS:
        raise ReplayRefused(f"Replay requires 1-{MAX_REPLAY_EVENTS} explicit event IDs.")
    if len(set(event_ids)) != len(event_ids):
        raise ReplayRefused("Replay event IDs must be unique.")
    if not INCIDENT_REFERENCE.fullmatch(incident_reference):
        raise ReplayRefused("Incident reference must use 3-80 safe identifier characters.")
    try:
        url = make_url(database_url)
    except ArgumentError as error:
        raise ReplayRefused("The configured database URL is invalid.") from error
    if url.drivername != "postgresql+asyncpg" or not url.host or not url.database:
        raise ReplayRefused("Replay requires an explicit postgresql+asyncpg database target.")
    actual_host = url.host.strip().rstrip(".").lower()
    expected_host = expected_database_host.strip().rstrip(".").lower()
    if not expected_host or actual_host != expected_host:
        raise ReplayRefused("The configured database host does not match the confirmed target.")
    if url.database != expected_database_name.strip():
        raise ReplayRefused("The configured database name does not match the confirmed target.")
    return ReplayRequest(
        event_ids=event_ids,
        expected_database_host=expected_host,
        expected_database_name=expected_database_name.strip(),
        incident_reference=incident_reference,
    )


async def replay_dead_letters(database_url: str, request: ReplayRequest) -> int:
    """Atomically requeue exactly the locked, undelivered dead letters requested."""
    engine = create_async_engine(database_url, pool_pre_ping=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as session:
            async with session.begin():
                rows = list(
                    (
                        await session.execute(
                            select(
                                OutboxEvent.id,
                                OutboxEvent.delivered_at,
                                OutboxEvent.dead_lettered_at,
                            )
                            .where(OutboxEvent.id.in_(request.event_ids))
                            .with_for_update()
                        )
                    ).all()
                )
                if {row.id for row in rows} != set(request.event_ids):
                    raise ReplayRefused("Every requested event must exist before replay.")
                if any(row.delivered_at is not None or row.dead_lettered_at is None for row in rows):
                    raise ReplayRefused("Every requested event must be an undelivered dead letter.")
                result = await session.execute(
                    update(OutboxEvent)
                    .where(
                        OutboxEvent.id.in_(request.event_ids),
                        OutboxEvent.delivered_at.is_(None),
                        OutboxEvent.dead_lettered_at.is_not(None),
                    )
                    .values(
                        available_at=func.now(),
                        dead_lettered_at=None,
                        attempts=0,
                        locked_at=None,
                        locked_by=None,
                        last_error=None,
                    )
                )
                if result.rowcount != len(request.event_ids):
                    raise ReplayRefused("The dead-letter set changed while replay was being authorized.")
        return len(request.event_ids)
    finally:
        await engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Requeue only explicitly reviewed TaxiMobile outbox dead letters.",
    )
    parser.add_argument("--event-id", action="append", required=True, type=UUID)
    parser.add_argument("--expected-database-host", required=True)
    parser.add_argument("--expected-database-name", required=True)
    parser.add_argument("--incident-reference", required=True)
    parser.add_argument(
        "--execute-reviewed-replay",
        action="store_true",
        help="Required confirmation that the dependency is fixed and every ID was reviewed.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    arguments = parser.parse_args()
    if not arguments.execute_reviewed_replay:
        parser.error("Refusing replay without --execute-reviewed-replay.")
    database_url = getenv("TAXIMOBILE_DATABASE_URL", "").strip()
    if not database_url:
        parser.error("TAXIMOBILE_DATABASE_URL must be supplied through the secret boundary.")
    try:
        request = validate_request(
            database_url=database_url,
            event_ids=tuple(arguments.event_id),
            expected_database_host=arguments.expected_database_host,
            expected_database_name=arguments.expected_database_name,
            incident_reference=arguments.incident_reference,
        )
        count = asyncio.run(replay_dead_letters(database_url, request))
    except ReplayRefused as error:
        parser.error(str(error))
    except Exception as error:
        print(f"Replay failed safely ({type(error).__name__}).", file=sys.stderr)
        raise SystemExit(1) from None
    print(
        f"Requeued {count} reviewed dead-letter event(s) for incident "
        f"{request.incident_reference}."
    )


if __name__ == "__main__":
    main()
