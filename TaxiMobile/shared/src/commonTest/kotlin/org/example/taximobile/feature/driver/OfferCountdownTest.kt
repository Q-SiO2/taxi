package org.example.taximobile.feature.driver

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue
import org.example.taximobile.domain.drivers.DriverRideOffer
import org.example.taximobile.domain.rides.Coordinates

class OfferCountdownTest {
    private val offer = DriverRideOffer(
        id = "offer-1",
        rideId = "ride-1",
        pickup = Coordinates(33.5731, -7.5898),
        issuedAt = "2026-08-13T10:00:00Z",
        expiresAt = "2026-08-13T10:00:45Z",
        serverTimeAtFetch = "2026-08-13T10:00:05Z",
    )

    @Test
    fun countdown_uses_server_time_and_monotonic_elapsed_seconds() {
        val initial = requireNotNull(offerCountdown(offer, elapsedSinceFetchSeconds = 0))
        assertEquals(40, initial.remainingSeconds)
        assertEquals(40f / 45f, initial.remainingFraction)
        assertFalse(initial.expired)

        val later = requireNotNull(offerCountdown(offer, elapsedSinceFetchSeconds = 10))
        assertEquals(30, later.remainingSeconds)
        assertEquals(30f / 45f, later.remainingFraction)
    }

    @Test
    fun countdown_expires_locally_without_authorizing_any_business_transition() {
        val expired = requireNotNull(offerCountdown(offer, elapsedSinceFetchSeconds = 40))
        assertEquals(0, expired.remainingSeconds)
        assertEquals(0f, expired.remainingFraction)
        assertTrue(expired.expired)
    }

    @Test
    fun malformed_or_non_positive_server_timing_is_not_invented() {
        assertNull(offerCountdown(offer.copy(issuedAt = "not-an-instant"), 0))
        assertNull(offerCountdown(offer.copy(issuedAt = offer.expiresAt), 0))
    }
}
