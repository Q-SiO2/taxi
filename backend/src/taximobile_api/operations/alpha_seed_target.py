"""Explicit target and credentials for the isolated synthetic Railway alpha."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from urllib.parse import urlparse

from sqlalchemy import select, text

from taximobile_api.domains.auth.models import User


ALPHA_CONFIRMATION = "CONFIRM_RAILWAY_SYNTHETIC_ALPHA"
ALPHA_PROJECT_ID = "9f841575-c4f3-4a4d-bb83-2e6ff92e436e"
ALPHA_ENVIRONMENT_ID = "ed891bc6-51ff-4acc-aed3-bb536931b855"
ALPHA_DATABASE = "taximobile_alpha_ed891bc651ff"
ALPHA_SEED_LOCK_KEY = 607_194_520_261_012


class AlphaSeedRefused(ValueError):
    """The bootstrap cannot safely create an isolated synthetic cohort."""


@dataclass(frozen=True, slots=True)
class RailwayAlphaTarget:
    project_id: str
    environment_id: str
    suffix: str
    password: str = field(repr=False)

    def validate(self, *, environment: str, database_url: str, confirmation: str) -> None:
        parsed = urlparse(database_url.replace("postgresql+asyncpg://", "postgresql://", 1))
        if (confirmation != ALPHA_CONFIRMATION or environment != "staging"
                or self.project_id != ALPHA_PROJECT_ID or self.environment_id != ALPHA_ENVIRONMENT_ID):
            raise AlphaSeedRefused("Explicit confirmation and the named Railway staging identities are required.")
        if (parsed.scheme != "postgresql" or parsed.hostname != "alpha-postgis.railway.internal"
                or parsed.port != 5432 or parsed.path != "/" + ALPHA_DATABASE
                or parsed.username != "taximobile_runtime" or not parsed.password
                or parsed.query or parsed.fragment):
            raise AlphaSeedRefused("Only the isolated private alpha database and runtime login may be seeded.")
        if not re.fullmatch(r"[0-9a-f]{8}", self.suffix) or not 32 <= len(self.password) <= 128:
            raise AlphaSeedRefused("A fixed synthetic suffix and private 32–128 character password are required.")


async def require_pristine_alpha(session) -> None:
    # Serialize bootstrap jobs. Lock accounts against ordinary registration too:
    # another transaction must not insert while the pristine check is in flight.
    # Both locks are released by the seed's existing surrounding transaction.
    await session.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"),
                          {"lock_key": ALPHA_SEED_LOCK_KEY})
    await session.execute(text("LOCK TABLE users IN SHARE ROW EXCLUSIVE MODE"))
    if await session.scalar(select(User.id).limit(1)) is not None:
        raise AlphaSeedRefused("Alpha already contains accounts; bootstrap never overwrites or resets data.")
