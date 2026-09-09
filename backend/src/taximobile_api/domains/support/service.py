from datetime import timedelta

from taximobile_api.domains.support.models import (
    CaseNoteVisibility,
    SupportCategory,
    SupportPriority,
    SupportResolutionCode,
    SupportTicket,
    SupportTicketNote,
    SupportTicketStatus,
)


class InvalidSupportTransition(ValueError):
    pass


_RESPONSE_TARGETS = {
    SupportPriority.URGENT: timedelta(hours=1),
    SupportPriority.HIGH: timedelta(hours=4),
    SupportPriority.NORMAL: timedelta(hours=24),
    SupportPriority.LOW: timedelta(hours=72),
}
_SUPPORT_RETENTION = timedelta(days=730)


def default_support_priority(category: SupportCategory) -> SupportPriority:
    if category == SupportCategory.ACCOUNT_ACCESS:
        return SupportPriority.HIGH
    if category == SupportCategory.OTHER:
        return SupportPriority.LOW
    return SupportPriority.NORMAL


def support_response_deadline(created_at, priority: SupportPriority):
    return created_at + _RESPONSE_TARGETS[priority]


def create_support_ticket_record(
    *,
    city_id,
    user_id,
    ride_id,
    category: SupportCategory,
    subject: str,
    description: str,
    created_at,
) -> SupportTicket:
    priority = default_support_priority(category)
    return SupportTicket(
        city_id=city_id,
        user_id=user_id,
        ride_id=ride_id,
        category=category,
        subject=subject,
        description=description,
        status=SupportTicketStatus.OPEN,
        priority=priority,
        response_due_at=support_response_deadline(created_at, priority),
        retention_policy_version="support-launch-v1",
        created_at=created_at,
        updated_at=created_at,
    )


def add_support_note(
    ticket: SupportTicket,
    *,
    author_user_id,
    visibility: CaseNoteVisibility,
    message: str,
    created_at,
) -> SupportTicketNote:
    if visibility == CaseNoteVisibility.PARTICIPANT:
        ticket.latest_public_message = message
        ticket.latest_public_message_at = created_at
    ticket.updated_at = created_at
    return SupportTicketNote(
        ticket_id=ticket.id,
        author_user_id=author_user_id,
        visibility=visibility,
        message=message,
        created_at=created_at,
    )


def triage_support_ticket(
    ticket: SupportTicket,
    *,
    priority: SupportPriority,
    assigned_to_user_id,
    triaged_at,
) -> None:
    if ticket.status in {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}:
        raise InvalidSupportTransition("A resolved or closed ticket cannot be triaged.")
    ticket.priority = priority
    ticket.assigned_to_user_id = assigned_to_user_id
    candidate_deadline = support_response_deadline(ticket.created_at, priority)
    ticket.response_due_at = min(ticket.response_due_at, candidate_deadline)
    if ticket.status == SupportTicketStatus.OPEN:
        ticket.status = SupportTicketStatus.IN_PROGRESS
    if ticket.first_responded_at is None:
        ticket.first_responded_at = triaged_at
    ticket.updated_at = triaged_at


def transition_support_ticket(
    ticket: SupportTicket,
    *,
    target_status: SupportTicketStatus,
    resolution_code: SupportResolutionCode | None,
    transitioned_at,
) -> None:
    allowed = {
        SupportTicketStatus.OPEN: {SupportTicketStatus.IN_PROGRESS},
        SupportTicketStatus.IN_PROGRESS: {SupportTicketStatus.RESOLVED},
        SupportTicketStatus.RESOLVED: {
            SupportTicketStatus.IN_PROGRESS,
            SupportTicketStatus.CLOSED,
        },
        SupportTicketStatus.CLOSED: set(),
    }
    if target_status not in allowed[ticket.status]:
        raise InvalidSupportTransition(
            f"Support ticket cannot transition from {ticket.status.value} to {target_status.value}."
        )
    if target_status in {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}:
        if resolution_code is None:
            raise InvalidSupportTransition("A resolution code is required for this transition.")
    elif resolution_code is not None:
        raise InvalidSupportTransition("A resolution code is allowed only when resolving or closing.")

    ticket.status = target_status
    ticket.updated_at = transitioned_at
    if target_status == SupportTicketStatus.IN_PROGRESS:
        if ticket.first_responded_at is None:
            ticket.first_responded_at = transitioned_at
        ticket.resolution_code = None
        ticket.resolved_at = None
        ticket.closed_at = None
        ticket.retention_until = None
    elif target_status == SupportTicketStatus.RESOLVED:
        ticket.resolution_code = resolution_code
        ticket.resolved_at = transitioned_at
    elif target_status == SupportTicketStatus.CLOSED:
        ticket.resolution_code = resolution_code
        ticket.closed_at = transitioned_at
        ticket.retention_until = transitioned_at + _SUPPORT_RETENTION
