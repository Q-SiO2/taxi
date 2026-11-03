package org.example.taximobile.data.drivers

import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.configureTaxiMobileTransport
import kotlin.test.*

class DriverOfferCancellationTest {
    private suspend fun cancelled(operation: suspend (KtorDriverOfferGateway) -> Unit) {
        var calls = 0
        val client = HttpClient(MockEngine { calls++; throw CancellationException("Synthetic cancellation") }) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorDriverOfferGateway(client,ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
            assertFailsWith<CancellationException> { operation(gateway) }
            assertEquals(1,calls)
        } finally { client.close() }
    }
    @Test fun cancelled_offer_read_is_not_a_network_failure_or_retry() = runBlocking { cancelled { it.currentOffers() } }
    @Test fun cancelled_acceptance_is_not_a_network_failure_or_replay() = runBlocking { cancelled { it.accept("synthetic-offer") } }
    @Test fun cancelled_decline_is_not_a_network_failure_or_replay() = runBlocking { cancelled { it.decline("synthetic-offer","DRIVER_DECLINED") } }

    @Test fun ordinary_transport_failure_remains_single_attempt_for_reads_and_actions() = runBlocking {
        for (operation in listOf<suspend (KtorDriverOfferGateway)->Unit>({it.currentOffers()}, {it.accept("synthetic-offer")}, {it.decline("synthetic-offer","DRIVER_DECLINED")})) {
            var calls=0
            val client=HttpClient(MockEngine {calls++;throw java.io.IOException("Synthetic transport failure")}){configureTaxiMobileTransport()}
            try {
                val gateway=KtorDriverOfferGateway(client,ApiConfiguration("https://synthetic.invalid")){"synthetic-access"}
                assertFailsWith<AuthenticationNetworkException>{operation(gateway)}
                assertEquals(1,calls)
            }finally{client.close()}
        }
    }
}
