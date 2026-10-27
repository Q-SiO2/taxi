package org.example.taximobile.data.network

import io.ktor.client.HttpClient
import io.ktor.client.engine.HttpClientEngineBase
import io.ktor.client.engine.HttpClientEngineConfig
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.HttpResponseData
import io.ktor.http.content.OutgoingContent
import io.ktor.utils.io.InternalAPI
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.rides.KtorRideGateway
import org.example.taximobile.data.scheduling.KtorScheduledBookingGateway
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RidePaymentMethod
import org.example.taximobile.domain.scheduling.ScheduledEconomics
import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertNotNull
import kotlin.test.assertIs

/** Real Ktor request pipelines with deterministic failures, never live providers. */
class RideSchedulingCancellationTest {
    @Test fun local_clock_read_cancellation_is_not_a_network_failure() = fixture { _, scheduled, engine ->
        assertFailsWith<CancellationException> { scheduled.localTimeOptions("synthetic-city", "Africa/Casablanca", "2026-11-01", "09:30") }
        assertEquals(1, engine.requests.size)
    }
    private val pickup = Coordinates(34.03, -5.00)
    private val destination = Coordinates(34.04, -5.01)
    private val scheduledFor = "2026-11-01T08:30:00Z"
    private val economics = ScheduledEconomics(
        "8.00", "3.00", "0.00", "11.00", "8.00", "3.00", "MAD",
        "synthetic-fare-v1", "synthetic-fee-v1", "synthetic-schedule-v1",
    )

    @Test fun scheduled_list_cancellation_is_not_a_network_failure() = fixture { _, scheduled, engine ->
        assertFailsWith<CancellationException> { scheduled.passengerBookings() }
        assertEquals(1, engine.requests.size)
    }

    @Test fun scheduled_estimate_cancellation_is_not_a_network_failure() = fixture { _, scheduled, engine ->
        assertFailsWith<CancellationException> {
            scheduled.estimatePointToPoint(scheduledFor, "synthetic-city", pickup, destination)
        }
        assertEquals(1, engine.requests.size)
    }

    @Test fun scheduled_point_to_point_creation_cancellation_is_not_retried() = fixture { _, scheduled, engine ->
        assertFailsWith<CancellationException> {
            scheduled.createPointToPoint(scheduledFor, "synthetic-city", pickup, destination, reviewedEconomics = economics)
        }
        assertEquals(1, engine.requests.size)
    }

    @Test fun scheduled_fixed_route_creation_cancellation_is_not_retried() = fixture { _, scheduled, engine ->
        assertFailsWith<CancellationException> {
            scheduled.createFixedRoute(scheduledFor, "synthetic-direction", reviewedEconomics = economics)
        }
        assertEquals(1, engine.requests.size)
    }

    @Test fun scheduled_accept_cancellation_is_not_a_network_failure() = fixture { _, scheduled, engine ->
        assertFailsWith<CancellationException> { scheduled.acceptOffer("synthetic-offer") }
        assertEquals(1, engine.requests.size)
    }

    @Test fun scheduled_cancel_propagates_second_attempt_cancellation_and_keeps_original_key() =
        fixture(firstTransportFailure = true) { _, scheduled, engine ->
            assertFailsWith<CancellationException> { scheduled.cancelPassengerBooking("synthetic-booking", "PASSENGER_REQUEST") }
            assertSameCommand(engine)
        }

    @Test fun fixed_route_catalog_cancellation_is_not_a_network_failure() = fixture { rides, _, engine ->
        assertFailsWith<CancellationException> { rides.fixedRoutes("synthetic-city") }
        assertEquals(1, engine.requests.size)
    }

    @Test fun immediate_fixed_route_creation_cancellation_is_not_retried() = fixture { rides, _, engine ->
        assertFailsWith<CancellationException> { rides.requestFixedRoute("synthetic-direction", RidePaymentMethod.CASH) }
        assertEquals(1, engine.requests.size)
    }

    @Test fun immediate_point_to_point_creation_propagates_second_attempt_cancellation() =
        fixture(firstTransportFailure = true) { rides, _, engine ->
            assertFailsWith<CancellationException> { rides.requestRide(pickup, destination) }
            assertSameCommand(engine)
        }

    @Test fun ordinary_transport_failure_still_has_one_bounded_same_key_retry() =
        fixture(onlyTransportFailures = true) { rides, _, engine ->
            assertFailsWith<AuthenticationNetworkException> { rides.cancelRide("synthetic-ride", "PASSENGER_REQUEST") }
            assertSameCommand(engine)
        }

    private fun assertSameCommand(engine: CancelledJourneyEngine) {
        assertEquals(2, engine.requests.size)
        val first = engine.requests[0]
        val retry = engine.requests[1]
        assertEquals(first.url, retry.url)
        assertEquals(first.method, retry.method)
        val key = assertNotNull(first.headers["Idempotency-Key"])
        assertEquals(key, retry.headers["Idempotency-Key"])
        assertContentEquals(
            assertIs<OutgoingContent.ByteArrayContent>(first.body).bytes(),
            assertIs<OutgoingContent.ByteArrayContent>(retry.body).bytes(),
        )
    }

    private fun fixture(
        firstTransportFailure: Boolean = false,
        onlyTransportFailures: Boolean = false,
        check: suspend (KtorRideGateway, KtorScheduledBookingGateway, CancelledJourneyEngine) -> Unit,
    ) = runBlocking<Unit> {
        val engine = CancelledJourneyEngine(firstTransportFailure, onlyTransportFailures)
        val client = HttpClient(engine) { configureTaxiMobileTransport() }
        val api = ApiConfiguration("https://synthetic.invalid")
        try {
            check(KtorRideGateway(client, api) { "synthetic-access" },
                  KtorScheduledBookingGateway(client, api) { "synthetic-access" }, engine)
        } finally {
            client.close()
        }
    }
}

@OptIn(InternalAPI::class)
private class CancelledJourneyEngine(
    private val firstTransportFailure: Boolean,
    private val onlyTransportFailures: Boolean,
) : HttpClientEngineBase("synthetic-journey-cancellation") {
    override val config = HttpClientEngineConfig()
    val requests = mutableListOf<HttpRequestData>()
    override suspend fun execute(data: HttpRequestData): HttpResponseData {
        requests += data
        if (onlyTransportFailures || (firstTransportFailure && requests.size == 1)) {
            throw IllegalStateException("Synthetic transport loss")
        }
        throw CancellationException("Synthetic journey cancellation")
    }
}
