package org.example.taximobile.feature.notifications

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

class PushRefreshHintRelayTest {
    @Test
    fun `allowlisted server hint is delivered without becoming business state`() = runBlocking {
        val relay = PushRefreshHintRelay()
        val rideId = "9f4f11f6-b67f-4a2d-9ae8-0d32d7e506a4"

        assertTrue(relay.submit(" DRIVER_ASSIGNED ", " $rideId "))

        assertEquals(PushRefreshHint("DRIVER_ASSIGNED", rideId), relay.hints.first())
    }

    @Test
    fun `unknown events and malformed resource identifiers are rejected`() {
        val relay = PushRefreshHintRelay()
        val rideId = "9f4f11f6-b67f-4a2d-9ae8-0d32d7e506a4"

        assertFalse(relay.submit("ACCOUNT_SUSPENDED", rideId))
        assertFalse(relay.submit("DRIVER_ASSIGNED", "not-a-uuid"))
        assertFalse(relay.submit(null, rideId))
        assertFalse(relay.submit("RIDE_CANCELLED", null))
    }

    @Test
    fun `only the latest unconsumed hint is retained`() = runBlocking {
        val relay = PushRefreshHintRelay()
        val firstRide = "9f4f11f6-b67f-4a2d-9ae8-0d32d7e506a4"
        val latestRide = "20f2de7c-956d-49a5-abe3-8a964eb03036"

        assertTrue(relay.submit("DRIVER_ASSIGNED", firstRide))
        assertTrue(relay.submit("RIDE_CANCELLED", latestRide))

        assertEquals(PushRefreshHint("RIDE_CANCELLED", latestRide), relay.hints.first())
    }

    @Test
    fun `credential expiry hint is allowlisted only as an authoritative refresh trigger`() = runBlocking {
        val relay = PushRefreshHintRelay()
        val credentialId = "9f4f11f6-b67f-4a2d-9ae8-0d32d7e506a4"

        assertTrue(relay.submit("DRIVER_CREDENTIAL_EXPIRED", credentialId))
        assertEquals(
            PushRefreshHint("DRIVER_CREDENTIAL_EXPIRED", credentialId),
            relay.hints.first(),
        )
    }

    @Test
    fun `city authorization hint prompts authoritative refresh without carrying decision state`() = runBlocking {
        val relay = PushRefreshHintRelay()
        val authorizationId = "9f4f11f6-b67f-4a2d-9ae8-0d32d7e506a4"

        assertTrue(relay.submit("DRIVER_CITY_AUTHORIZATION_CHANGED", authorizationId))
        assertEquals(
            PushRefreshHint("DRIVER_CITY_AUTHORIZATION_CHANGED", authorizationId),
            relay.hints.first(),
        )
    }

    @Test
    fun `scheduled event hints are allowlisted only as authoritative refresh triggers`() = runBlocking {
        val relay = PushRefreshHintRelay()
        val bookingId = "9f4f11f6-b67f-4a2d-9ae8-0d32d7e506a4"
        val eventTypes = listOf(
            "SCHEDULED_OFFER",
            "SCHEDULED_DRIVER_COMMITTED",
            "SCHEDULED_DISPATCH_STARTED",
            "SCHEDULED_FALLBACK_MATCHING",
            "SCHEDULED_UNFULFILLED",
        )

        eventTypes.forEach { eventType ->
            assertTrue(relay.submit(eventType, bookingId))
            assertEquals(PushRefreshHint(eventType, bookingId), relay.hints.first())
        }
    }
}
