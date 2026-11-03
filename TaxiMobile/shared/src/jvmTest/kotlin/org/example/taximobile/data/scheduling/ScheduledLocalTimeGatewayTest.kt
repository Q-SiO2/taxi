package org.example.taximobile.data.scheduling

import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.http.*
import io.ktor.http.content.TextContent
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.configureTaxiMobileTransport
import kotlin.test.*

class ScheduledLocalTimeGatewayTest {
    private fun wire(date: String = "2026-11-01", time: String = "09:30", options: String = """[{"scheduled_for":"2026-11-01T08:30:00Z","utc_offset_seconds":3600}]""") =
        """{"city_id":"city","city_timezone":"Africa/Casablanca","local_date":"$date","local_time":"$time","booking_available":true,"rules_version":"2026b","options":$options}"""
    private fun gateway(client: HttpClient) = KtorScheduledBookingGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }

    @Test fun authorized_planning_read_sends_only_clock_input_without_an_idempotency_command() = runBlocking<Unit> {
        var calls = 0
        val client = HttpClient(MockEngine { request ->
            calls++
            assertEquals(HttpMethod.Post, request.method)
            assertEquals("/api/v1/cities/city/scheduled-time-options", request.url.encodedPath)
            assertEquals("Bearer synthetic-access", request.headers[HttpHeaders.Authorization])
            assertNull(request.headers["Idempotency-Key"])
            assertEquals(Json.parseToJsonElement("""{"local_date":"2026-11-01","local_time":"09:30"}""").jsonObject,
                Json.parseToJsonElement((request.body as TextContent).text).jsonObject)
            respond(wire(), headers = headersOf(HttpHeaders.ContentType, "application/json"))
        }) { configureTaxiMobileTransport() }
        try {
            val value = gateway(client).localTimeOptions("city", "Africa/Casablanca", "2026-11-01", "09:30")
            assertEquals("2026-11-01T08:30:00Z", value.options.single().scheduledFor)
            assertEquals(1, calls)
        } finally { client.close() }
    }

    @Test fun gaps_and_overlaps_are_not_collapsed_to_one_default_instant() = runBlocking<Unit> {
        for ((date, count, options) in listOf(
            Triple("2026-03-22", 0, "[]"),
            Triple("2026-02-15", 2, """[{"scheduled_for":"2026-02-15T01:30:00Z","utc_offset_seconds":3600},{"scheduled_for":"2026-02-15T02:30:00Z","utc_offset_seconds":0}]"""),
        )) {
            val client = HttpClient(MockEngine { respond(wire(date, "02:30", options), headers = headersOf(HttpHeaders.ContentType, "application/json")) }) { configureTaxiMobileTransport() }
            try { assertEquals(count, gateway(client).localTimeOptions("city", "Africa/Casablanca", date, "02:30").options.size) }
            finally { client.close() }
        }
    }

    @Test fun malformed_or_stale_context_is_sanitized_without_retry() = runBlocking<Unit> {
        for (body in listOf("PRIVATE-invalid", wire().replace("\"city\"", "\"other-city\""),
            wire().replace("Africa/Casablanca", "UTC"), wire().replace("2026-11-01T08:30:00Z", "2026-11-02T08:30:00Z"),
            wire().replace("3600", "0"), wire().replace("true", "\"PRIVATE-invalid\""))) {
            var calls = 0
            val client = HttpClient(MockEngine { calls++; respond(body, headers = headersOf(HttpHeaders.ContentType, "application/json")) }) { configureTaxiMobileTransport() }
            try {
                val error = assertFailsWith<ApiRequestException> { gateway(client).localTimeOptions("city", "Africa/Casablanca", "2026-11-01", "09:30") }
                assertEquals(502, error.statusCode)
                assertFalse(error.message.orEmpty().contains("PRIVATE-invalid"))
                assertEquals(1, calls)
            } finally { client.close() }
        }
    }

    @Test fun missing_capability_and_rule_unavailability_are_explicit_single_attempt_failures() = runBlocking<Unit> {
        for (status in listOf(HttpStatusCode.NotFound, HttpStatusCode.MethodNotAllowed, HttpStatusCode.ServiceUnavailable)) {
            var calls = 0
            val client = HttpClient(MockEngine { calls++; respond("{}", status, headersOf(HttpHeaders.ContentType, "application/json")) }) { configureTaxiMobileTransport() }
            try {
                val error = assertFailsWith<ApiRequestException> { gateway(client).localTimeOptions("city", "Africa/Casablanca", "2026-11-01", "09:30") }
                assertEquals(status.value, error.statusCode)
                assertEquals(1, calls)
            } finally { client.close() }
        }
    }

    @Test fun cancellation_network_failure_and_rejected_access_remain_distinct() = runBlocking<Unit> {
        for (kind in listOf("cancel", "network", "unauthorized")) {
            var calls = 0
            val client = HttpClient(MockEngine {
                calls++
                when (kind) {
                    "cancel" -> throw CancellationException("Synthetic cancellation")
                    "network" -> throw IllegalStateException("Synthetic transport loss")
                    else -> respond("{}", HttpStatusCode.Unauthorized, headersOf(HttpHeaders.ContentType, "application/json"))
                }
            }) { configureTaxiMobileTransport() }
            try {
                when (kind) {
                    "cancel" -> assertFailsWith<CancellationException> { gateway(client).localTimeOptions("city", "Africa/Casablanca", "2026-11-01", "09:30") }
                    "network" -> assertFailsWith<AuthenticationNetworkException> { gateway(client).localTimeOptions("city", "Africa/Casablanca", "2026-11-01", "09:30") }
                    else -> assertFailsWith<AuthenticationRejectedException> { gateway(client).localTimeOptions("city", "Africa/Casablanca", "2026-11-01", "09:30") }
                }
                assertEquals(1, calls)
            } finally { client.close() }
        }
    }
}
