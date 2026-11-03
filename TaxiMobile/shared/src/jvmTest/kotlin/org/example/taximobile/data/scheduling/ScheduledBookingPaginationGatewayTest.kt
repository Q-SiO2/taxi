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

class ScheduledBookingPaginationGatewayTest {
    @Test fun twenty_first_booking_is_reached_by_an_explicit_read_only_second_page() = runBlocking {
        val requested = mutableListOf<Int>()
        val client = HttpClient(MockEngine { request ->
            assertEquals(HttpMethod.Get, request.method)
            assertNull(request.headers["Idempotency-Key"])
            assertEquals("20", request.url.parameters["limit"])
            val page = request.url.parameters["page"]!!.toInt().also { requested += it }
            val items = (if (page == 1) (1..20) else (21..21)).joinToString(",") { bookingWire("booking-$it") }
            respond("""{"items":[$items],"page":$page,"limit":20,"total":21}""", headers = headersOf(HttpHeaders.ContentType, "application/json"))
        }) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorScheduledBookingGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
            val first = gateway.passengerBookings()
            assertEquals(20, first.items.size)
            assertTrue(first.hasNext)
            assertEquals(listOf(1), requested)
            val second = gateway.passengerBookings(2)
            assertEquals("booking-21", second.items.single().id)
            assertEquals(21, second.total)
            assertFalse(second.hasNext)
            assertEquals(listOf(1, 2), requested)
        } finally { client.close() }
    }
    @Test fun malformed_or_mismatched_pages_are_sanitized_and_not_retried() = runBlocking {
        for (payload in listOf(
            """{"items":[],"page":1,"limit":20,"total":0}""",
            """{"items":[],"page":2,"limit":100,"total":0}""",
            """{"items":[]}""", "{private-invalid-json",
            """{"items":[${bookingWire("same")},${bookingWire("same")}],"page":2,"limit":20,"total":2}""",
        )) {
            var calls = 0
            val client = HttpClient(MockEngine { calls++; respond(payload, headers = headersOf(HttpHeaders.ContentType, "application/json")) }) { configureTaxiMobileTransport() }
            try {
                val gateway = KtorScheduledBookingGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
                val error = assertFailsWith<ApiRequestException> { gateway.passengerBookings(2) }
                assertEquals(502, error.statusCode)
                assertFalse(error.message.orEmpty().contains("private-invalid-json"))
                assertEquals(1, calls)
                assertFailsWith<IllegalArgumentException> { gateway.passengerBookings(0) }
                assertEquals(1, calls)
            } finally { client.close() }
        }
    }
    @Test fun page_read_cancellation_is_not_reclassified_as_a_bad_page() = runBlocking<Unit> {
        val client = HttpClient(MockEngine { throw CancellationException("Synthetic cancellation") }) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorScheduledBookingGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
            assertFailsWith<CancellationException> { gateway.passengerBookings(2) }
        } finally { client.close() }
    }
}
