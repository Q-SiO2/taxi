package org.example.taximobile.data.rides

import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.http.HttpHeaders
import io.ktor.http.headersOf
import kotlinx.coroutines.runBlocking
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.network.configureTaxiMobileTransport
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RidePaymentMethod
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class RideEstimateCapabilityGatewayTest {
    private val pickup = Coordinates(34.03, -5.00)
    private val destination = Coordinates(34.04, -5.01)

    @Test
    fun missing_payment_capabilities_cannot_become_an_implicit_cash_quote() = runBlocking {
        for (fixedRoute in listOf(false, true)) {
            var calls = 0
            val client = HttpClient(MockEngine {
                calls++
                respond(estimateResponse(), headers = headersOf(HttpHeaders.ContentType, "application/json"))
            }) { configureTaxiMobileTransport() }
            try {
                val gateway = KtorRideGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
                val error = assertFailsWith<ApiRequestException> {
                    if (fixedRoute) gateway.estimateFixedRoute("synthetic-direction")
                    else gateway.estimateRide(pickup, destination)
                }
                assertEquals(502, error.statusCode)
                assertEquals(1, calls)
            } finally {
                client.close()
            }
        }
    }

    @Test
    fun advertised_methods_remain_the_only_quote_choices() = runBlocking {
        for (fixedRoute in listOf(false, true)) {
            val client = HttpClient(MockEngine {
                respond(
                    estimateResponse("\"payment_methods\":[\"MANUAL_TRANSFER\",\"CASH\"]"),
                    headers = headersOf(HttpHeaders.ContentType, "application/json"),
                )
            }) { configureTaxiMobileTransport() }
            try {
                val gateway = KtorRideGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
                val estimate = if (fixedRoute) gateway.estimateFixedRoute("synthetic-direction")
                else gateway.estimateRide(pickup, destination)
                assertEquals(listOf(RidePaymentMethod.MANUAL_TRANSFER, RidePaymentMethod.CASH), estimate.paymentMethods)
            } finally {
                client.close()
            }
        }
    }

    private fun estimateResponse(capabilities: String? = null): String =
        """{"estimate":{"amount":"35.00","currency":"MAD","pricing_rule_version":"v1"}${capabilities?.let { ",$it" }.orEmpty()}}"""
}
