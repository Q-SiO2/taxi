from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from taximobile_api.domains.support.models import (
    CaseNoteVisibility,
    SupportCategory,
    SupportPriority,
    SupportResolutionCode,
    SupportTicketStatus,
)
from taximobile_api.domains.support.service import (
    InvalidSupportTransition,
    add_support_note,
    create_support_ticket_record,
    transition_support_ticket,
    triage_support_ticket,
)


def ticket(category: SupportCategory = SupportCategory.RIDE_PROBLEM):
    created_at = datetime(2026, 8, 24, 12, tzinfo=UTC)
    return create_support_ticket_record(
        city_id=uuid4(),
        user_id=uuid4(),
        ride_id=uuid4(),
        category=category,
        subject="Ride issue",
        description="Controlled support description.",
        created_at=created_at,
    )


def test_support_defaults_are_category_specific_and_bounded() -> None:
    account = ticket(SupportCategory.ACCOUNT_ACCESS)
    other = ticket(SupportCategory.OTHER)

    assert account.priority == SupportPriority.HIGH
    assert account.response_due_at - account.created_at == timedelta(hours=4)
    assert other.priority == SupportPriority.LOW
    assert other.response_due_at - other.created_at == timedelta(hours=72)


def test_triage_assigns_and_never_extends_an_existing_deadline() -> None:
    case = ticket(SupportCategory.ACCOUNT_ACCESS)
    original_deadline = case.response_due_at
    assignee_id = uuid4()

    triage_support_ticket(
        case,
        priority=SupportPriority.LOW,
        assigned_to_user_id=assignee_id,
        triaged_at=case.created_at + timedelta(minutes=10),
    )

    assert case.status == SupportTicketStatus.IN_PROGRESS
    assert case.assigned_to_user_id == assignee_id
    assert case.response_due_at == original_deadline
    assert case.first_responded_at == case.created_at + timedelta(minutes=10)


def test_support_resolution_reopen_and_close_preserve_append_only_policy() -> None:
    case = ticket()
    case.id = uuid4()
    assignee_id = uuid4()
    triage_support_ticket(
        case,
        priority=SupportPriority.NORMAL,
        assigned_to_user_id=assignee_id,
        triaged_at=case.created_at + timedelta(minutes=5),
    )
    resolved_at = case.created_at + timedelta(hours=1)
    transition_support_ticket(
        case,
        target_status=SupportTicketStatus.RESOLVED,
        resolution_code=SupportResolutionCode.ACTION_TAKEN,
        transitioned_at=resolved_at,
    )
    public_note = add_support_note(
        case,
        author_user_id=assignee_id,
        visibility=CaseNoteVisibility.PARTICIPANT,
        message="We completed the reviewed action.",
        created_at=resolved_at,
    )
    internal_note = add_support_note(
        case,
        author_user_id=assignee_id,
        visibility=CaseNoteVisibility.INTERNAL,
        message="Restricted evidence summary.",
        created_at=resolved_at,
    )

    assert case.latest_public_message == public_note.message
    assert internal_note.message not in case.latest_public_message

    transition_support_ticket(
        case,
        target_status=SupportTicketStatus.IN_PROGRESS,
        resolution_code=None,
        transitioned_at=resolved_at + timedelta(hours=1),
    )
    assert case.resolution_code is None
    transition_support_ticket(
        case,
        target_status=SupportTicketStatus.RESOLVED,
        resolution_code=SupportResolutionCode.INFORMATION_PROVIDED,
        transitioned_at=resolved_at + timedelta(hours=2),
    )
    closed_at = resolved_at + timedelta(hours=3)
    transition_support_ticket(
        case,
        target_status=SupportTicketStatus.CLOSED,
        resolution_code=SupportResolutionCode.INFORMATION_PROVIDED,
        transitioned_at=closed_at,
    )
    assert case.status == SupportTicketStatus.CLOSED
    assert case.retention_until == closed_at + timedelta(days=730)


def test_support_state_machine_rejects_skips_and_missing_resolution() -> None:
    case = ticket()
    with pytest.raises(InvalidSupportTransition):
        transition_support_ticket(
            case,
            target_status=SupportTicketStatus.CLOSED,
            resolution_code=SupportResolutionCode.NO_ACTION,
            transitioned_at=case.created_at,
        )
    triage_support_ticket(
        case,
        priority=SupportPriority.NORMAL,
        assigned_to_user_id=uuid4(),
        triaged_at=case.created_at,
    )
    with pytest.raises(InvalidSupportTransition):
        transition_support_ticket(
            case,
            target_status=SupportTicketStatus.RESOLVED,
            resolution_code=None,
            transitioned_at=case.created_at,
        )
