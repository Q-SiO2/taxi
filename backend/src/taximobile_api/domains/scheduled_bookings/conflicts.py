"""Recognize only the migrated, expected driver-window exclusion violation."""

from sqlalchemy.exc import IntegrityError


def is_driver_window_conflict(error: IntegrityError) -> bool:
    # asyncpg exposes SQLSTATE on SQLAlchemy's adapter and constraint_name on
    # its original cause. Do not parse exception text: it may contain private
    # SQL parameters, and another integrity fault is not a driver's conflict.
    original = error.orig
    cause = getattr(original, "__cause__", None)
    state = getattr(original, "sqlstate", None) or getattr(cause, "sqlstate", None)
    constraint = getattr(original, "constraint_name", None) or getattr(cause, "constraint_name", None)
    return state == "23P01" and constraint == "ex_scheduled_commitments_driver_window"
