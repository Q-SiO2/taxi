package org.example.taximobile.data.realtime

import io.ktor.client.HttpClient
import io.ktor.client.engine.HttpClientEngineBase
import io.ktor.client.engine.HttpClientEngineConfig
import io.ktor.client.request.HttpRequestData
import io.ktor.client.request.HttpResponseData
import io.ktor.utils.io.InternalAPI
import io.ktor.client.plugins.websocket.WebSocketCapability
import org.example.taximobile.data.network.configureTaxiMobileTransport
import kotlin.test.Test
import kotlin.test.assertFailsWith
import kotlin.test.assertSame
import kotlin.test.assertEquals
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.runBlocking
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException

/** No network engine or additional dependency is needed to prove token-stage cancellation. */
class KtorLiveEventGatewayTest {
    @Test
    fun `credential acquisition cancellation is propagated unchanged`() = runBlocking<Unit> {
        val cancellation = CancellationException("synthetic cancellation")
        val client = HttpClient(UnusedLiveEngine())
        try {
            val gateway = KtorLiveEventGateway(client, ApiConfiguration("https://synthetic.invalid")) {
                throw cancellation
            }
            val thrown = assertFailsWith<CancellationException> { gateway.listen({}, {}) }
            assertSame(cancellation, thrown)
        } finally { client.close() }
    }

    @Test
    fun `definitive credential rejection is not a network failure`() = runBlocking<Unit> {
        val client = HttpClient(UnusedLiveEngine())
        try {
            val gateway = KtorLiveEventGateway(client, ApiConfiguration("https://synthetic.invalid")) {
                throw AuthenticationRejectedException()
            }
            assertFailsWith<AuthenticationRejectedException> { gateway.listen({}, {}) }
        } finally { client.close() }
    }

    @Test
    fun `credential-stage network failure remains a recoverable typed failure`() = runBlocking<Unit> {
        val client = HttpClient(UnusedLiveEngine())
        try {
            val gateway = KtorLiveEventGateway(client, ApiConfiguration("https://synthetic.invalid")) {
                throw AuthenticationNetworkException()
            }
            assertFailsWith<AuthenticationNetworkException> { gateway.listen({}, {}) }
        } finally { client.close() }
    }

    @Test
    fun `socket engine cancellation is not translated to a network retry`() = runBlocking<Unit> {
        val engine = FailingLiveEngine(CancellationException("synthetic socket cancellation"))
        val client = HttpClient(engine) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorLiveEventGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
            assertFailsWith<CancellationException> { gateway.listen({}, {}) }
            assertEquals(1, engine.requests)
        } finally { client.close() }
    }

    @Test
    fun `socket engine transport failure is translated to a recoverable network error`() = runBlocking<Unit> {
        val engine = FailingLiveEngine(IllegalStateException("synthetic transport failure"))
        val client = HttpClient(engine) { configureTaxiMobileTransport() }
        try {
            val gateway = KtorLiveEventGateway(client, ApiConfiguration("https://synthetic.invalid")) { "synthetic-access" }
            assertFailsWith<AuthenticationNetworkException> { gateway.listen({}, {}) }
            assertEquals(1, engine.requests)
        } finally { client.close() }
    }
}

@OptIn(InternalAPI::class)
private class FailingLiveEngine(private val failure: Throwable) : HttpClientEngineBase("synthetic-failing-live-engine") {
    override val config = HttpClientEngineConfig()
    override val supportedCapabilities = setOf(WebSocketCapability)
    var requests = 0
    override suspend fun execute(data: HttpRequestData): HttpResponseData {
        requests++
        throw failure
    }
}

@OptIn(InternalAPI::class)
private class UnusedLiveEngine : HttpClientEngineBase("synthetic-unused-live-engine") {
    override val config = HttpClientEngineConfig()
    override suspend fun execute(data: HttpRequestData): HttpResponseData =
        error("The credential-stage test must not issue a network request")
}
