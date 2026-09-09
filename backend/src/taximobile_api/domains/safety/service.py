from datetime import timedelta

from taximobile_api.domains.safety.models import (
    SafetyReport,
    SafetyReportCategory,
    SafetyReportNote,
    SafetyReportStatus,
    SafetyResolutionCode,
)
from taximobile_api.domains.support.models import CaseNoteVisibility, SupportPriority


class InvalidSafetyTransition(ValueError):
    pass


_SAFETY_RETENTION = timedelta(days=1825)


def safety_priority(category: SafetyReportCategory) -> SupportPriority:
    return (
        SupportPriority.URGENT
        if category == SafetyReportCategory.IMMEDIATE_DANGER
        else SupportPriority.HIGH
    )


def safety_response_deadline(created_at, category: SafetyReportCategory):
    target = timedelta(minutes=5 if category == SafetyReportCategory.IMMEDIATE_DANGER else 30)
    return created_at + target


def create_safety_report_record(
    *,
    city_id,
    ride_id,
    reporter_user_id,
    reported_user_id,
    category: SafetyReportCategory,
    description: str,
    created_at,
    source_support_ticket_id=None,
) -> SafetyReport:
    return SafetyReport(
        city_id=city_id,
        ride_id=ride_id,
        reporter_user_id=reporter_user_id,
        reported_user_id=reported_user_id,
        source_support_ticket_id=source_support_ticket_id,
        category=category,
        description=description,
        status=SafetyReportStatus.SUBMITTED,
        priority=safety_priority(category),
        response_due_at=safety_response_deadline(created_at, category),
        retention_policy_version="safety-launch-v1",
        created_at=created_at,
        updated_at=created_at,
    )


def add_safety_note(
    report: SafetyReport,
    *,
    author_user_id,
    visibility: CaseNoteVisibility,
    message: str,
    created_at,
) -> SafetyReportNote:
    if visibility == CaseNoteVisibility.PARTICIPANT:
        report.latest_public_message = message
        report.latest_public_message_at = created_at
    report.updated_at = created_at
    return SafetyReportNote(
        report_id=report.id,
        author_user_id=author_user_id,
        visibility=visibility,
        message=message,
        created_at=created_at,
    )


def transition_safety_report(
    report: SafetyReport,
    *,
    target_status: SafetyReportStatus,
    resolution_code: SafetyResolutionCode | None,
    assigned_to_user_id,
    transitioned_at,
) -> None:
    allowed = {
        SafetyReportStatus.SUBMITTED: {SafetyReportStatus.ACKNOWLEDGED},
        SafetyReportStatus.ACKNOWLEDGED: {
            SafetyReportStatus.ESCALATED,
            SafetyReportStatus.RESOLVED,
        },
        SafetyReportStatus.ESCALATED: {SafetyReportStatus.RESOLVED},
        SafetyReportStatus.RESOLVED: {
            SafetyReportStatus.ACKNOWLEDGED,
            SafetyReportStatus.CLOSED,
        },
        SafetyReportStatus.CLOSED: set(),
    }
    if target_status not in allowed[report.status]:
        raise InvalidSafetyTransition(
            f"Safety report cannot transition from {report.status.value} to {target_status.value}."
        )
    if target_status in {SafetyReportStatus.RESOLVED, SafetyReportStatus.CLOSED}:
        if resolution_code is None:
            raise InvalidSafetyTransition("A safety resolution code is required for this transition.")
    elif resolution_code is not None:
        raise InvalidSafetyTransition(
            "A safety resolution code is allowed only when resolving or closing."
        )

    report.status = target_status
    report.assigned_to_user_id = assigned_to_user_id
    report.updated_at = transitioned_at
    if target_status == SafetyReportStatus.ACKNOWLEDGED:
        if report.first_acknowledged_at is None:
            report.first_acknowledged_at = transitioned_at
        report.resolution_code = None
        report.resolved_at = None
        report.closed_at = None
        report.retention_until = None
    elif target_status == SafetyReportStatus.ESCALATED:
        report.escalated_at = transitioned_at
    elif target_status == SafetyReportStatus.RESOLVED:
        report.resolution_code = resolution_code
        report.resolved_at = transitioned_at
    elif target_status == SafetyReportStatus.CLOSED:
        report.resolution_code = resolution_code
        report.closed_at = transitioned_at
        report.retention_until = transitioned_at + _SAFETY_RETENTION
