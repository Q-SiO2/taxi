package org.example.taximobile.data.scheduling

import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.http.*
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.configureTaxiMobileTransport
import kotlin.test.*

class ScheduledBookingDetailGatewayTest {
    @Test fun fresh_detail_is_a_single_authorized_read_and_retains_unknown_terms() = runBlocking {
        var calls = 0
        val client = HttpClient(MockEngine { request ->
            calls++
            assertEquals(HttpMethod.Get, request.method)
            assertEquals("/api/v1/scheduled-bookings/booking-21", request.url.encodedPath)
            assertEquals("Bearer synthetic-access", request.headers[HttpHeaders.Authorization])
            assertNull(request.headers["Idempotency-Key"])
            respond(bookingWire("booking-21").replace("FULL_BEFORE_CUTOFF", "FUTURE_PRIVATE_POLICY"), headers = headersOf(HttpHeaders.ContentType, "application/json"))
        }) { configureTaxiMobileTransport() }
        try {
            val booking = KtorScheduledBookingGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }.passengerBooking("booking-21")
            assertEquals("booking-21", booking.id)
            assertFalse(booking.cancellationTerms.isSupportedForReview)
            assertEquals("FUTURE_PRIVATE_POLICY", booking.cancellationTerms.surchargeRefundMode)
            assertEquals(1, calls)
        } finally { client.close() }
    }

    @Test fun different_record_and_server_denial_are_not_retried() = runBlocking {
        for (status in listOf(HttpStatusCode.OK, HttpStatusCode.Forbidden)) {
            var calls = 0
            val client = HttpClient(MockEngine { calls++; respond(bookingWire("wrong-booking"), status, headersOf(HttpHeaders.ContentType, "application/json")) }) { configureTaxiMobileTransport() }
            try {
                val error = assertFailsWith<ApiRequestException> { KtorScheduledBookingGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }.passengerBooking("booking-21") }
                assertEquals(if (status == HttpStatusCode.OK) 502 else 403, error.statusCode)
                assertEquals(1, calls)
            } finally { client.close() }
        }
    }

    @Test fun detail_read_cancellation_propagates_without_a_command_or_retry() = runBlocking<Unit> {
        var calls = 0
        val client = HttpClient(MockEngine { calls++; throw CancellationException("Synthetic cancellation") }) { configureTaxiMobileTransport() }
        try {
            assertFailsWith<CancellationException> { KtorScheduledBookingGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }.passengerBooking("booking-21") }
            assertEquals(1, calls)
        } finally { client.close() }
    }
}
