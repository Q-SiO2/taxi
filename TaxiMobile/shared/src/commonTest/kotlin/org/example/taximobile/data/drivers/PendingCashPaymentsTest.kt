package org.example.taximobile.data.drivers

import io.ktor.client.HttpClient
import io.ktor.client.engine.HttpClientEngineBase
import io.ktor.client.engine.HttpClientEngineConfig
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.HttpResponseData
import io.ktor.utils.io.InternalAPI
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.configureTaxiMobileTransport
import kotlin.test.*

class PendingCashPaymentsTest {
    private val json = Json { ignoreUnknownKeys = true }
    private val row = """{"payment_id":"payment-1","ride_id":"ride-1","amount":"35.00","currency":"MAD","created_at":"2026-10-05T12:00:00Z","completed_at":null,"method":"CASH","status":"PENDING"}"""
    private fun response(item: String = row, page: Int = 1, total: Int = 21) = """{"items":[$item],"page":$page,"limit":20,"total":$total}"""

    @Test fun exact_server_amount_and_pagination_are_preserved() {
        val page = json.decodeFromString<PendingCashPaymentsResponse>(response()).toDomain(1)
        assertEquals("35.00", page.items.single().amount)
        assertEquals("ride-1", page.items.single().rideId)
        assertTrue(page.hasNext)
        assertFalse(page.hasPrevious)
    }
    @Test fun settled_and_non_cash_items_are_never_projected_as_pending_cash() {
        for (bad in listOf(row.replace("PENDING", "COMPLETED"), row.replace("CASH", "MANUAL_TRANSFER"))) {
            assertFailsWith<IllegalArgumentException> { json.decodeFromString<PendingCashPaymentsResponse>(response(bad)).toDomain(1) }
        }
    }
    @Test fun unknown_method_and_missing_status_do_not_default_to_cash() {
        assertFailsWith<SerializationException> { json.decodeFromString<PendingCashPaymentsResponse>(response(row.replace(",\"status\":\"PENDING\"", ""))) }
        assertFailsWith<IllegalArgumentException> { json.decodeFromString<PendingCashPaymentsResponse>(response(row.replace("CASH", "UNKNOWN"))).toDomain(1) }
    }
    @Test fun mismatched_page_and_duplicate_items_are_rejected() {
        assertFailsWith<IllegalArgumentException> { json.decodeFromString<PendingCashPaymentsResponse>(response()).toDomain(2) }
        assertFailsWith<IllegalArgumentException> { json.decodeFromString<PendingCashPaymentsResponse>(response("$row,$row")).toDomain(1) }
    }
    @Test fun malformed_amount_is_not_a_confirmable_payment() {
        assertFailsWith<IllegalArgumentException> { json.decodeFromString<PendingCashPaymentsResponse>(response(row.replace("35.00", "-35.00"))).toDomain(1) }
    }
    @Test fun cancellation_of_queue_read_is_not_a_network_error() = runBlocking<Unit> {
        val engine = CancelledCashEngine()
        val client = HttpClient(engine) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorDriverRideGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
            assertFailsWith<CancellationException> { gateway.pendingCashPayments() }
            assertEquals(1, engine.calls)
        } finally { client.close() }
    }
    @Test fun cancelled_settlement_is_not_retried() = runBlocking<Unit> {
        val engine = CancelledCashEngine()
        val client = HttpClient(engine) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorDriverRideGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
            assertFailsWith<CancellationException> { gateway.settleCash("synthetic-ride") }
            assertEquals(1, engine.calls)
        } finally { client.close() }
    }
}

@OptIn(InternalAPI::class)
private class CancelledCashEngine : HttpClientEngineBase("synthetic-cash-cancellation") {
    override val config = HttpClientEngineConfig()
    var calls = 0
    override suspend fun execute(data: HttpRequestData): HttpResponseData {
        calls++
        throw CancellationException("Synthetic cancellation")
    }
}
