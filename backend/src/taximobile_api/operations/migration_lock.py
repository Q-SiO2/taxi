"""One cooperative Alembic executor per database, without an indefinite wait.

The complete migration chain must remain in one PostgreSQL transaction. A future
nontransactional migration needs a different lock lifetime and new release tests;
silently adding an autocommit block would invalidate this guarantee.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection


# Stable database-scoped advisory namespace: ASCII TAXI / MIGR. These are not
# table/row identifiers and must not be changed between application releases.
MIGRATION_LOCK_NAMESPACE = 0x54415849
MIGRATION_LOCK_RESOURCE = 0x4D494752
MIGRATION_BUSY_MESSAGE = (
    "Another TaxiMobile migration is running for this database. "
    "Retry after it finishes; do not start a second migrator."
)


class MigrationAlreadyRunning(RuntimeError):
    pass


def acquire_migration_lock(connection: Connection) -> None:
    """Acquire inside the outer migration transaction, before version reads/DDL.

    PostgreSQL releases this lock on commit, rollback or connection loss. A busy
    result is deliberately fail-fast; deployment orchestration owns retry policy.
    """
    if not connection.in_transaction():
        raise RuntimeError("Migration lock requires the outer migration transaction.")
    acquired = connection.scalar(
        text("SELECT pg_try_advisory_xact_lock(:namespace, :resource)"),
        {"namespace": MIGRATION_LOCK_NAMESPACE, "resource": MIGRATION_LOCK_RESOURCE},
    )
    if acquired is not True:
        raise MigrationAlreadyRunning(MIGRATION_BUSY_MESSAGE)


# Offline rendering performs no database access. The generated transactional SQL
# must enforce the same gate when an operator later executes that script.
OFFLINE_MIGRATION_LOCK_SQL = f"""
DO $$ BEGIN
    IF NOT pg_try_advisory_xact_lock({MIGRATION_LOCK_NAMESPACE}, {MIGRATION_LOCK_RESOURCE}) THEN
        RAISE EXCEPTION '{MIGRATION_BUSY_MESSAGE}';
    END IF;
END $$
"""
