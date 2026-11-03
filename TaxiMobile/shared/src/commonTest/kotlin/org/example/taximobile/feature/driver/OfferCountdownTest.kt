package org.example.taximobile.feature.driver

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue
import org.example.taximobile.domain.drivers.DriverRideOffer
import org.example.taximobile.domain.rides.Coordinates
import kotlin.time.TestTimeSource
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.seconds

@OptIn(kotlin.time.ExperimentalTime::class)
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

    @Test fun a_delayed_or_copied_offer_keeps_the_original_monotonic_anchor() {
        val clock=TestTimeSource()
        val current=offer.copy(readStartedAt=clock.markNow())
        assertEquals(40,offerCountdown(current)?.remainingSeconds)
        clock+=39.seconds
        assertEquals(1,offerCountdown(current.copy())?.remainingSeconds)
        clock+=1.seconds
        assertTrue(requireNotNull(offerCountdown(current)).expired)
        clock+=100.seconds
        assertEquals(0,offerCountdown(current)?.remainingSeconds)
    }

    @Test fun fractional_seconds_are_ceiled_without_extending_an_expired_envelope() {
        assertEquals(40,offerCountdown(offer,1.milliseconds)?.remainingSeconds)
        assertEquals(39,offerCountdown(offer,1000.milliseconds)?.remainingSeconds)
        assertEquals(1,offerCountdown(offer,39999.milliseconds)?.remainingSeconds)
        assertEquals(0,offerCountdown(offer,40000.milliseconds)?.remainingSeconds)
    }

    @Test fun invalid_elapsed_time_and_unrepresentable_windows_are_unavailable() {
        assertNull(offerCountdown(offer,(-1).seconds))
        assertNull(offerCountdown(offer,Duration.INFINITE))
        assertNull(offerCountdown(offer.copy(expiresAt="2126-08-13T10:00:45Z"),Duration.ZERO))
        assertEquals(0,offerCountdown(offer.copy(serverTimeAtFetch=offer.expiresAt),Duration.ZERO)?.remainingSeconds)
    }

    @Test fun server_time_may_precede_a_concurrently_issued_row_without_inventing_the_deadline() {
        // The actual backend captures server_time before querying current offers.
        val current=offer.copy(serverTimeAtFetch="2026-08-13T09:59:59Z")
        assertEquals(46,offerCountdown(current,Duration.ZERO)?.remainingSeconds)
        assertEquals(1f,offerCountdown(current,Duration.ZERO)?.remainingFraction)
        assertEquals(45,offerCountdown(current,1.seconds)?.remainingSeconds)
    }
}
