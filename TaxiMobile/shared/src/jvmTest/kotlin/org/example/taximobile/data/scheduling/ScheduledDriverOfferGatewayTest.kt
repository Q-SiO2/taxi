package org.example.taximobile.data.scheduling

import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.http.*
import kotlinx.coroutines.runBlocking
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.configureTaxiMobileTransport
import org.example.taximobile.domain.scheduling.canReviewAcceptance
import org.example.taximobile.domain.scheduling.responseSecondsRemaining
import kotlin.test.*
import kotlin.time.Duration.Companion.seconds
import kotlin.time.TestTimeSource

@OptIn(kotlin.time.ExperimentalTime::class)
class ScheduledDriverOfferGatewayTest {
    @Test fun the_owned_read_counts_network_delay_and_never_sends_a_command() = runBlocking {
        val clock = TestTimeSource()
        var calls = 0
        val payload = bookingWire("offer-synthetic").trimEnd().removeSuffix("}")
            .replace("\"status\":\"SCHEDULED\"", "\"status\":\"PENDING\"")
            .replace("\"service_type\":\"POINT_TO_POINT\"", "\"service_type\":\"ON_DEMAND\"") +
            """, "booking_id":"booking-21", "server_time":"2026-11-01T08:00:00Z", "expires_at":"2026-11-01T08:01:00Z"}"""
        val client = HttpClient(MockEngine { request ->
            calls++
            assertEquals(HttpMethod.Get,request.method)
            assertEquals("/api/v1/drivers/me/scheduled-offers",request.url.encodedPath)
            assertNull(request.headers["Idempotency-Key"])
            assertEquals("Bearer synthetic-access",request.headers[HttpHeaders.Authorization])
            clock += 20.seconds
            respond("""{"items":[$payload]}""", headers = headersOf(HttpHeaders.ContentType,"application/json"))
        }) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorScheduledBookingGateway(client,ApiConfiguration("https://synthetic.invalid"),readClock = clock) { "synthetic-access" }
            val offer = gateway.driverOffers().single()
            assertEquals(40,offer.responseSecondsRemaining())
            assertTrue(offer.canReviewAcceptance)
            clock += 40.seconds
            assertEquals(0,offer.responseSecondsRemaining())
            assertFalse(offer.canReviewAcceptance)
            assertEquals(1,calls)
        } finally { client.close() }
    }
}
