from datetime import UTC, datetime, timedelta
from uuid import uuid4

from taximobile_api.domains.rides.models import Ride, RideOffer, RideOfferStatus, RideStatus
from taximobile_api.domains.rides.service import offer_failure


def test_offer_requires_pending_unexpired_matching_ride() -> None:
    ride = Ride(passenger_id=uuid4(), status=RideStatus.MATCHING)
    offer = RideOffer(ride_id=ride.id, driver_id=uuid4(), status=RideOfferStatus.PENDING, expires_at=datetime.now(UTC) + timedelta(seconds=30))
    assert offer_failure(offer, ride, datetime.now(UTC)) is None

    offer.status = RideOfferStatus.DECLINED
    assert offer_failure(offer, ride, datetime.now(UTC)) == "Ride offer is no longer pending."

    offer.status = RideOfferStatus.PENDING
    offer.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert offer_failure(offer, ride, datetime.now(UTC)) == "Ride offer has expired."
