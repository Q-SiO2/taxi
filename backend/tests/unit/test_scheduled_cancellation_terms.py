"""Unknown or malformed terms must never become a claimed financial policy."""
from types import SimpleNamespace

import pytest

from taximobile_api.domains.scheduled_bookings.router import cancellation_terms, policy_cancellation_terms

UNAVAILABLE = "Cancellation terms are unavailable; refresh before confirming."


def terms(kind, mode, cutoff):
    if kind == "booking":
        return cancellation_terms(SimpleNamespace(policy_snapshot={
            "surcharge_refund_mode": mode, "passenger_cancel_cutoff_minutes": cutoff,
        }))
    return policy_cancellation_terms(SimpleNamespace(
        surcharge_refund_mode=SimpleNamespace(value=mode), passenger_cancel_cutoff_minutes=cutoff,
    ))


@pytest.mark.parametrize("kind", ["booking", "quote"])
@pytest.mark.parametrize("mode,expected", [
    ("ALWAYS_FULL", "Cancellation does not retain the scheduling surcharge."),
    ("FULL_BEFORE_CUTOFF", "The scheduling surcharge is refundable until 60 minutes before pickup."),
    ("NON_REFUNDABLE", "The scheduling surcharge is non-refundable after confirmation."),
])
def test_known_terms_keep_the_exact_declared_financial_meaning(kind, mode, expected):
    result = terms(kind, mode, 60)
    assert result.summary == expected
    assert result.surcharge_refund_mode == mode and result.passenger_cancel_cutoff_minutes == 60


@pytest.mark.parametrize("kind", ["booking", "quote"])
@pytest.mark.parametrize("mode", ["FUTURE_PRIVATE_POLICY", "always_full", ""])
def test_unrecognized_mode_is_unavailable_never_guessed_non_refundable(kind, mode):
    result = terms(kind, mode, 60)
    assert result.summary == UNAVAILABLE
    assert "non-refundable" not in result.summary and "PRIVATE" not in result.summary
    assert result.surcharge_refund_mode == mode


@pytest.mark.parametrize("kind", ["booking", "quote"])
@pytest.mark.parametrize("mode", ["ALWAYS_FULL", "FULL_BEFORE_CUTOFF", "NON_REFUNDABLE"])
@pytest.mark.parametrize("cutoff", [-1, 10081])
def test_invalid_cutoff_cannot_be_presented_as_reviewable_terms(kind, mode, cutoff):
    assert terms(kind, mode, cutoff).summary == UNAVAILABLE
