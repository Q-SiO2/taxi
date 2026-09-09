"""Legal-hold-aware erasure of expired support and safety personal data."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, exists, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.case_retention.models import (
    CaseLegalHold,
    CaseRetentionAction,
    CaseRetentionActionCode,
    LegalHoldStatus,
)
from taximobile_api.domains.safety.models import SafetyReport, SafetyReportNote, SafetyReportStatus
from taximobile_api.domains.support.models import SupportTicket, SupportTicketNote, SupportTicketStatus
from taximobile_api.workers.runtime import run_polling_processor


class CaseRetentionProcessor:
    """Erase personal fields only after closure, due time, and hold recheck.

    The selected case row and active-hold predicate live in the same transaction.
    `SKIP LOCKED` permits multiple workers without duplicate evidence; the unique
    action row remains the final database guard.
    """

    def __init__(self, sessions: async_sessionmaker[AsyncSession], *, batch_size: int = 100) -> None:
        self._sessions = sessions
        self._batch_size = batch_size

    async def process_once(self) -> int:
        now = datetime.now(UTC)
        processed = 0
        async with self._sessions() as session:
            async with session.begin():
                support_cases = list(
                    await session.scalars(
                        select(SupportTicket)
                        .where(
                            SupportTicket.status == SupportTicketStatus.CLOSED,
                            SupportTicket.retention_until.is_not(None),
                            SupportTicket.retention_until <= now,
                            SupportTicket.retention_processed_at.is_(None),
                            ~exists().where(
                                CaseLegalHold.support_ticket_id == SupportTicket.id,
                                CaseLegalHold.status == LegalHoldStatus.ACTIVE.value,
                            ),
                        )
                        .order_by(SupportTicket.retention_until.asc(), SupportTicket.id.asc())
                        .limit(self._batch_size)
                        .with_for_update(skip_locked=True)
                    )
                )
                for ticket in support_cases:
                    await self._erase_support(session, ticket, now)
                    processed += 1

                safety_cases = list(
                    await session.scalars(
                        select(SafetyReport)
                        .where(
                            SafetyReport.status == SafetyReportStatus.CLOSED,
                            SafetyReport.retention_until.is_not(None),
                            SafetyReport.retention_until <= now,
                            SafetyReport.retention_processed_at.is_(None),
                            ~exists().where(
                                CaseLegalHold.safety_report_id == SafetyReport.id,
                                CaseLegalHold.status == LegalHoldStatus.ACTIVE.value,
                            ),
                        )
                        .order_by(SafetyReport.retention_until.asc(), SafetyReport.id.asc())
                        .limit(self._batch_size)
                        .with_for_update(skip_locked=True)
                    )
                )
                for report in safety_cases:
                    await self._erase_safety(session, report, now)
                    processed += 1
        return processed

    async def _erase_support(self, session: AsyncSession, ticket: SupportTicket, now: datetime) -> None:
        result = await session.execute(delete(SupportTicketNote).where(SupportTicketNote.ticket_id == ticket.id))
        note_count = max(result.rowcount or 0, 0)
        ticket.user_id = None
        ticket.ride_id = None
        ticket.assigned_to_user_id = None
        ticket.subject = ""
        ticket.description = ""
        ticket.latest_public_message = None
        ticket.latest_public_message_at = None
        ticket.retention_action = CaseRetentionActionCode.PERSONAL_DATA_ERASED.value
        ticket.retention_processed_at = now
        ticket.updated_at = now
        session.add(
            CaseRetentionAction(
                city_id=ticket.city_id,
                support_ticket_id=ticket.id,
                action=CaseRetentionActionCode.PERSONAL_DATA_ERASED.value,
                retention_policy_version=ticket.retention_policy_version,
                retention_due_at=ticket.retention_until,
                executed_at=now,
                erased_note_count=note_count,
                created_at=now,
            )
        )

    async def _erase_safety(self, session: AsyncSession, report: SafetyReport, now: datetime) -> None:
        result = await session.execute(delete(SafetyReportNote).where(SafetyReportNote.report_id == report.id))
        note_count = max(result.rowcount or 0, 0)
        report.ride_id = None
        report.reporter_user_id = None
        report.reported_user_id = None
        report.assigned_to_user_id = None
        report.description = ""
        report.latest_public_message = None
        report.latest_public_message_at = None
        report.retention_action = CaseRetentionActionCode.PERSONAL_DATA_ERASED.value
        report.retention_processed_at = now
        report.updated_at = now
        session.add(
            CaseRetentionAction(
                city_id=report.city_id,
                safety_report_id=report.id,
                action=CaseRetentionActionCode.PERSONAL_DATA_ERASED.value,
                retention_policy_version=report.retention_policy_version,
                retention_due_at=report.retention_until,
                executed_at=now,
                erased_note_count=note_count,
                created_at=now,
            )
        )


async def run_case_retention_processor(
    processor: CaseRetentionProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    await run_polling_processor(
        worker="case_retention",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
