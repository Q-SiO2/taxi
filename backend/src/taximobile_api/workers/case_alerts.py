"""Durable overdue-case discovery, resolution, and protected paging."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taximobile_api.core.metrics import MetricsRegistry
from taximobile_api.domains.case_alerts.models import (
    CaseAlertSeverity,
    CaseAlertStatus,
    CaseOverdueAlert,
)
from taximobile_api.domains.safety.models import SafetyReport, SafetyReportStatus
from taximobile_api.domains.support.models import (
    SupportPriority,
    SupportTicket,
    SupportTicketStatus,
)
from taximobile_api.integrations.case_pager import (
    CasePager,
    CasePagerDeliveryError,
    CasePagerMessage,
)
from taximobile_api.workers.runtime import run_polling_processor


_REPAGING_INTERVAL = timedelta(minutes=15)
_ADVISORY_LOCK_ID = 8_731_440_041


def support_is_overdue(ticket: SupportTicket, now: datetime) -> bool:
    return (
        ticket.first_responded_at is None
        and ticket.response_due_at < now
        and ticket.status not in {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}
    )


def safety_is_overdue(report: SafetyReport, now: datetime) -> bool:
    return (
        report.first_acknowledged_at is None
        and report.response_due_at < now
        and report.status not in {SafetyReportStatus.RESOLVED, SafetyReportStatus.CLOSED}
    )


class CaseAlertProcessor:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        pager: CasePager,
        *,
        batch_size: int = 100,
        max_delivery_attempts: int = 8,
    ) -> None:
        self._sessions = sessions
        self._pager = pager
        self._batch_size = batch_size
        self._max_delivery_attempts = max_delivery_attempts

    async def process_once(self) -> int:
        now = datetime.now(UTC)
        changed = 0
        delivery_failed = False
        async with self._sessions() as session:
            async with session.begin():
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": _ADVISORY_LOCK_ID},
                )
                changed += await self._discover(session, now)
                changed += await self._resolve(session, now)
                await session.flush()
                alerts = list(
                    await session.scalars(
                        select(CaseOverdueAlert)
                        .where(
                            CaseOverdueAlert.status == CaseAlertStatus.OPEN.value,
                            CaseOverdueAlert.delivery_attempts < self._max_delivery_attempts,
                            or_(
                                CaseOverdueAlert.next_delivery_at.is_(None),
                                CaseOverdueAlert.next_delivery_at <= now,
                            ),
                        )
                        .order_by(
                            CaseOverdueAlert.severity.desc(),
                            CaseOverdueAlert.first_detected_at.asc(),
                            CaseOverdueAlert.id.asc(),
                        )
                        .limit(self._batch_size)
                        .with_for_update(skip_locked=True)
                    )
                )
                for alert in alerts:
                    try:
                        delivered = await self._pager.send(_pager_message(alert))
                    except CasePagerDeliveryError:
                        alert.delivery_attempts += 1
                        alert.next_delivery_at = now + _retry_delay(alert.delivery_attempts)
                        alert.updated_at = now
                        delivery_failed = True
                    else:
                        if delivered:
                            alert.delivery_attempts += 1
                            alert.last_delivered_at = now
                            alert.next_delivery_at = now + _REPAGING_INTERVAL
                            alert.updated_at = now
                            changed += 1
        if delivery_failed:
            raise CasePagerDeliveryError("One or more protected case alerts were not delivered.")
        return changed

    async def _discover(self, session: AsyncSession, now: datetime) -> int:
        changed = 0
        support_tickets = list(
            await session.scalars(
                select(SupportTicket)
                .where(
                    SupportTicket.first_responded_at.is_(None),
                    SupportTicket.response_due_at < now,
                    SupportTicket.status.not_in(
                        (SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED)
                    ),
                )
                .order_by(SupportTicket.response_due_at.asc(), SupportTicket.id.asc())
                .limit(self._batch_size)
            )
        )
        safety_reports = list(
            await session.scalars(
                select(SafetyReport)
                .where(
                    SafetyReport.first_acknowledged_at.is_(None),
                    SafetyReport.response_due_at < now,
                    SafetyReport.status.not_in(
                        (SafetyReportStatus.RESOLVED, SafetyReportStatus.CLOSED)
                    ),
                )
                .order_by(SafetyReport.response_due_at.asc(), SafetyReport.id.asc())
                .limit(self._batch_size)
            )
        )
        for ticket in support_tickets:
            existing = await session.scalar(
                select(CaseOverdueAlert).where(
                    CaseOverdueAlert.support_ticket_id == ticket.id
                )
            )
            if existing is None:
                session.add(
                    CaseOverdueAlert(
                        city_id=ticket.city_id,
                        support_ticket_id=ticket.id,
                        severity=(
                            CaseAlertSeverity.URGENT.value
                            if ticket.priority == SupportPriority.URGENT
                            else CaseAlertSeverity.HIGH.value
                        ),
                        status=CaseAlertStatus.OPEN.value,
                        response_due_at=ticket.response_due_at,
                        first_detected_at=now,
                        last_evaluated_at=now,
                        next_delivery_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )
                changed += 1
            else:
                existing.last_evaluated_at = now
        for report in safety_reports:
            existing = await session.scalar(
                select(CaseOverdueAlert).where(
                    CaseOverdueAlert.safety_report_id == report.id
                )
            )
            if existing is None:
                session.add(
                    CaseOverdueAlert(
                        city_id=report.city_id,
                        safety_report_id=report.id,
                        severity=(
                            CaseAlertSeverity.URGENT.value
                            if report.priority == SupportPriority.URGENT
                            else CaseAlertSeverity.HIGH.value
                        ),
                        status=CaseAlertStatus.OPEN.value,
                        response_due_at=report.response_due_at,
                        first_detected_at=now,
                        last_evaluated_at=now,
                        next_delivery_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )
                changed += 1
            else:
                existing.last_evaluated_at = now
        await session.flush()
        return changed

    async def _resolve(self, session: AsyncSession, now: datetime) -> int:
        alerts = list(
            await session.scalars(
                select(CaseOverdueAlert)
                .where(CaseOverdueAlert.status != CaseAlertStatus.RESOLVED.value)
                .order_by(CaseOverdueAlert.first_detected_at.asc())
                .limit(self._batch_size * 2)
                .with_for_update(skip_locked=True)
            )
        )
        changed = 0
        for alert in alerts:
            still_overdue = False
            if alert.support_ticket_id is not None:
                ticket = await session.get(SupportTicket, alert.support_ticket_id)
                still_overdue = ticket is not None and support_is_overdue(ticket, now)
            elif alert.safety_report_id is not None:
                report = await session.get(SafetyReport, alert.safety_report_id)
                still_overdue = report is not None and safety_is_overdue(report, now)
            if not still_overdue:
                alert.status = CaseAlertStatus.RESOLVED.value
                alert.resolved_at = now
                alert.next_delivery_at = None
                alert.last_evaluated_at = now
                alert.updated_at = now
                changed += 1
        return changed


def _pager_message(alert: CaseOverdueAlert) -> CasePagerMessage:
    if alert.support_ticket_id is not None:
        case_type = "SUPPORT"
        case_id = alert.support_ticket_id
    else:
        case_type = "SAFETY"
        assert alert.safety_report_id is not None
        case_id = alert.safety_report_id
    return CasePagerMessage(
        alert_id=alert.id,
        city_id=alert.city_id,
        case_type=case_type,
        case_id=case_id,
        severity=alert.severity,
        response_due_at=alert.response_due_at,
        first_detected_at=alert.first_detected_at,
    )


def _retry_delay(attempt: int) -> timedelta:
    return timedelta(seconds=min(900, 30 * (2 ** min(attempt - 1, 5))))


async def run_case_alert_processor(
    processor: CaseAlertProcessor,
    poll_seconds: float,
    metrics: MetricsRegistry,
) -> None:
    await run_polling_processor(
        worker="case_alerts",
        processor=processor,
        poll_seconds=poll_seconds,
        metrics=metrics,
    )
