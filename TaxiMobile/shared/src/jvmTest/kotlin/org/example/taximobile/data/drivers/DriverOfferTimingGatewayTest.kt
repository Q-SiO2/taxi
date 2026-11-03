package org.example.taximobile.data.drivers

import io.ktor.client.HttpClient
import io.ktor.client.engine.mock.MockEngine
import io.ktor.client.engine.mock.respond
import io.ktor.http.*
import kotlinx.coroutines.runBlocking
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.network.configureTaxiMobileTransport
import org.example.taximobile.feature.driver.offerCountdown
import kotlin.test.*
import kotlin.time.TestTimeSource
import kotlin.time.Duration.Companion.seconds

@OptIn(kotlin.time.ExperimentalTime::class)
class DriverOfferTimingGatewayTest {
    @Test fun read_delay_counts_against_the_server_relative_window()=runBlocking {
        val clock=TestTimeSource()
        var calls=0
        val client=HttpClient(MockEngine { request->
            calls++
            assertEquals(HttpMethod.Get,request.method)
            assertEquals("/api/v1/drivers/me/ride-offers",request.url.encodedPath)
            assertNull(request.headers["Idempotency-Key"])
            assertEquals("Bearer synthetic-access",request.headers[HttpHeaders.Authorization])
            clock+=30.seconds
            respond("""{"server_time":"2026-08-13T10:00:05Z","offers":[{
              "id":"synthetic-offer","ride_id":"synthetic-ride","pickup":{"latitude":34.03,"longitude":-5.0},
              "issued_at":"2026-08-13T10:00:00Z","expires_at":"2026-08-13T10:00:45Z"}]}""",
              headers=headersOf(HttpHeaders.ContentType,"application/json"))
        }){configureTaxiMobileTransport()}
        try {
            val offer=KtorDriverOfferGateway(client,ApiConfiguration("https://synthetic.invalid"),readClock=clock){"synthetic-access"}.currentOffers().single()
            assertEquals(10,offerCountdown(offer)?.remainingSeconds)
            clock+=10.seconds
            assertTrue(requireNotNull(offerCountdown(offer)).expired)
            assertEquals(1,calls)
        } finally {client.close()}
    }
}
