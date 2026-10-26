package org.example.taximobile.domain.scheduling

import org.example.taximobile.data.scheduling.scheduledOfferFixture
import kotlin.test.*
import kotlin.time.Duration
import kotlin.time.Duration.Companion.milliseconds
import kotlin.time.Duration.Companion.seconds
import kotlin.time.TestTimeSource

@OptIn(kotlin.time.ExperimentalTime::class)
class ScheduledOfferReviewTest {
    @Test fun countdown_uses_server_envelope_and_ceilings_not_the_device_wall_clock() {
        val clock = TestTimeSource()
        val offer = scheduledOfferFixture(clock.markNow())
        assertEquals(60, offer.responseSecondsRemaining())
        clock += 1.milliseconds
        assertEquals(60, offer.responseSecondsRemaining())
        clock += 999.milliseconds
        assertEquals(59, offer.responseSecondsRemaining())
        assertTrue(offer.canReviewAcceptance)
        assertEquals(60, offer.copy(serverTime = "2026-11-01T09:00:00+01:00").responseSecondsRemaining(Duration.ZERO))
    }

    @Test fun delayed_or_reopened_ui_cannot_restart_the_response_window() {
        val clock = TestTimeSource()
        val offer = scheduledOfferFixture(clock.markNow())
        clock += 60.seconds
        assertEquals(0, offer.responseSecondsRemaining())
        assertFalse(offer.canReviewAcceptance)
        clock += 1000.seconds
        assertEquals(0, offer.copy().responseSecondsRemaining())
    }

    @Test fun invalid_and_unrepresentable_envelopes_are_not_invented() {
        val offer = scheduledOfferFixture()
        for (bad in listOf(offer.copy(expiresAt = "PRIVATE-invalid"), offer.copy(serverTime = "PRIVATE-invalid"),
            offer.copy(expiresAt = "2126-11-01T08:01:00Z"))) {
            assertNull(bad.responseSecondsRemaining())
            assertFalse(bad.canReviewAcceptance)
        }
        assertNull(offer.responseSecondsRemaining((-1).seconds))
        assertNull(offer.responseSecondsRemaining(Duration.INFINITE))
        assertEquals(0, offer.copy(expiresAt = offer.serverTime).responseSecondsRemaining())
    }

    @Test fun only_pending_supported_service_and_terms_can_be_reviewed_for_acceptance() {
        val offer = scheduledOfferFixture()
        assertTrue(offer.canReviewAcceptance)
        assertTrue(offer.copy(serviceType = "FIXED_ROUTE").canReviewAcceptance)
        for (bad in listOf(offer.copy(status = "EXPIRED"), offer.copy(status = "FUTURE_PRIVATE_STATUS"),
            offer.copy(serviceType = "FUTURE_PRIVATE_SERVICE"), offer.copy(id = ""),
            offer.copy(cancellationTerms = offer.cancellationTerms.copy(surchargeRefundMode = "FUTURE_PRIVATE_POLICY")),
            offer.copy(cancellationTerms = offer.cancellationTerms.copy(passengerCancelCutoffMinutes = -1)))) {
            assertFalse(bad.canReviewAcceptance)
        }
    }
}
