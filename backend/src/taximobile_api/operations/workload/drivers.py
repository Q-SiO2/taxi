"""Synthetic driver admission and bounded offer discovery; never eligibility bypass."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from uuid import UUID

from .client import WorkloadClient


@dataclass(frozen=True)
class SyntheticDriverCredential:
    user_id: UUID
    access_token: str = field(repr=False)


def parse_driver_credentials(raw: str, *, count: int) -> tuple[SyntheticDriverCredential, ...]:
    try:
        if not isinstance(raw, str) or len(raw) > 512000:
            raise ValueError()
        data = json.loads(raw)
        if not isinstance(data, list) or len(data) != count or not 1 <= count <= 50:
            raise ValueError()
        credentials = []
        for entry in data:
            if not isinstance(entry, dict) or set(entry) != {"user_id", "access_token"}:
                raise ValueError()
            token = entry["access_token"]
            if (not isinstance(token, str) or not 1 <= len(token) <= 8192
                    or not token.isascii() or any(c.isspace() or ord(c) < 33 for c in token)):
                raise ValueError()
            credentials.append(SyntheticDriverCredential(UUID(entry["user_id"]), token))
        if len({item.user_id for item in credentials}) != count or len({item.access_token for item in credentials}) != count:
            raise ValueError()
        return tuple(credentials)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise ValueError("Driver credentials must be a bounded list of distinct user_id/access_token pairs matching --users.") from None


class DriverClient(WorkloadClient):
    def __init__(self, client, config, metrics, credential):
        super().__init__(client, config, metrics)
        self.token = credential.access_token
        self.expected_user_id = str(credential.user_id)
        self.busy = asyncio.Lock()
        self.touched = False

    async def preflight(self) -> None:
        identity = await self.request("driver_identity", "GET", "/api/v1/me", 200)
        roles = identity.get("roles")
        self.check(identity.get("id") == self.expected_user_id
                   and isinstance(roles, list) and "DRIVER" in roles
                   and all(role in ("PASSENGER", "DRIVER") for role in roles), "driver_identity")
        profile = await self.request("driver_profile", "GET", "/api/v1/drivers/me", 200)
        self.check(profile.get("user_id") == self.expected_user_id
                   and isinstance(profile.get("display_name"), str)
                   and profile["display_name"].startswith("Synthetic ")
                   and profile.get("account_status") == "ACTIVE"
                   and profile.get("verification_status") == "APPROVED"
                   and profile.get("availability_status") == "OFFLINE", "driver_profile")
        offers = await self.request("driver_preflight_offers", "GET", "/api/v1/drivers/me/ride-offers", 200)
        self.check(offers.get("offers") == [], "driver_preflight_offers")

    async def ready(self) -> None:
        self.touched = True
        location = await self.request("driver_location", "POST", "/api/v1/drivers/me/location", 200,
            payload={"latitude": self.config.pickup[0], "longitude": self.config.pickup[1],
                     "observed_at": datetime.now(UTC).isoformat(), "accuracy": 5})
        self.check(location.get("accepted") is True, "driver_location")
        online = await self.request("driver_online", "POST", "/api/v1/drivers/me/availability/online", 200,
            payload={"city_id": str(self.config.city_id), "service_type": "ON_DEMAND"})
        self.check(online.get("status") == "AVAILABLE"
                   and online.get("city_id") == str(self.config.city_id)
                   and online.get("service_type") == "ON_DEMAND", "driver_online")

    async def confirm_offline(self) -> None:
        availability = await self.request("driver_cleanup_state", "GET", "/api/v1/drivers/me/availability", 200)
        if availability.get("status") == "AVAILABLE":
            await self.request("driver_cleanup_offline", "POST", "/api/v1/drivers/me/availability/offline", 200)
            availability = await self.request("driver_cleanup_restore", "GET", "/api/v1/drivers/me/availability", 200)
        self.check(availability.get("status") == "OFFLINE", "driver_cleanup_state")


async def find_driver(passenger, drivers, ride_id):
    # Fifty rounds cap API fanout as well as elapsed time; the outer run and
    # each HTTP request have their own deadlines. Never act on unrelated offers.
    for _ in range(50):
        for driver in drivers:
            if driver.busy.locked():
                continue
            # Reads do not lease a driver. Otherwise synchronized passengers
            # can repeatedly lock opposite drivers, skip their own offer and
            # never make progress despite both offers being available.
            result = await driver.request("driver_offers", "GET", "/api/v1/drivers/me/ride-offers", 200)
            offers = result.get("offers")
            driver.check(isinstance(offers, list), "driver_offers")
            matching = [offer for offer in offers if isinstance(offer, dict) and offer.get("ride_id") == ride_id]
            driver.check(len(matching) <= 1, "driver_offers")
            if matching and not driver.busy.locked():
                offer_id = driver.resource_id(matching[0], "driver_offers")
                await driver.busy.acquire()  # Immediate; no check/acquire suspension.
                return driver, offer_id
        await asyncio.sleep(.2)
    passenger.check(False, "driver_offer_deadline")


@asynccontextmanager
async def claim_driver(passenger, drivers, ride_id):
    driver, offer_id = await find_driver(passenger, drivers, ride_id)
    try:
        yield driver, offer_id
    finally:
        driver.busy.release()
