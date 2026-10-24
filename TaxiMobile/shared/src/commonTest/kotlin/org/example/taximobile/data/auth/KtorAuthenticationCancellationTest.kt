package org.example.taximobile.data.auth

import io.ktor.client.HttpClient
import io.ktor.client.engine.HttpClientEngineBase
import io.ktor.client.engine.HttpClientEngineConfig
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.HttpResponseData
import io.ktor.utils.io.InternalAPI
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.configureTaxiMobileTransport
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class KtorAuthenticationCancellationTest {
    @Test fun refresh_cancellation_propagates_without_network_normalization() = runBlocking<Unit> {
        val engine = CancelledAuthenticationEngine()
        val client = HttpClient(engine) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorAuthenticationGateway(client, ApiConfiguration("https://synthetic.invalid"))
            assertFailsWith<CancellationException> { gateway.refresh("synthetic-refresh") }
            assertEquals(1, engine.calls)
        } finally { client.close() }
    }

    @Test fun account_preflight_cancellation_propagates_without_network_normalization() = runBlocking<Unit> {
        val engine = CancelledAuthenticationEngine()
        val client = HttpClient(engine) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorAuthenticationGateway(client, ApiConfiguration("https://synthetic.invalid"))
            assertFailsWith<CancellationException> { gateway.currentAccount("synthetic-access") }
            assertEquals(1, engine.calls)
        } finally { client.close() }
    }
}

@OptIn(InternalAPI::class)
private class CancelledAuthenticationEngine : HttpClientEngineBase("synthetic-auth-cancellation") {
    override val config = HttpClientEngineConfig()
    var calls = 0
    override suspend fun execute(data: HttpRequestData): HttpResponseData {
        calls++
        throw CancellationException("Synthetic auth cancellation")
    }
}
