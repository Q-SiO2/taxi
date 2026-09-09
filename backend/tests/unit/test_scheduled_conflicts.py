"""Closed metadata classification, never SQL/error-message inference."""

import pytest
from sqlalchemy.exc import IntegrityError

from taximobile_api.domains.scheduled_bookings.conflicts import is_driver_window_conflict


WINDOW = "ex_scheduled_commitments_driver_window"


@pytest.mark.parametrize("state,constraint,wrapped,expected", [
    ("23P01", WINDOW, False, True),
    ("23P01", WINDOW, True, True),
    ("23503", WINDOW, False, False),
    ("23505", WINDOW, True, False),
    ("23P01", "different_constraint", True, False),
    (None, WINDOW, False, False),
    ("23P01", None, True, False),
    (None, None, False, False),
])
def test_only_exact_constraint_and_sqlstate_are_expected_conflicts(state, constraint, wrapped, expected):
    original = Exception(f"private SQL and {WINDOW} text is not diagnostic authority")
    original.sqlstate = state
    if wrapped:
        cause = Exception("private driver window")
        cause.constraint_name = constraint
        original.__cause__ = cause
    else:
        original.constraint_name = constraint
    error = IntegrityError("private SQL", {"private": "values"}, original)
    assert is_driver_window_conflict(error) is expected


def test_original_asyncpg_cause_can_supply_both_metadata_fields():
    cause = Exception("private")
    cause.sqlstate = "23P01"
    cause.constraint_name = WINDOW
    original = Exception("adapter")
    original.__cause__ = cause
    assert is_driver_window_conflict(IntegrityError("private SQL", {}, original))
