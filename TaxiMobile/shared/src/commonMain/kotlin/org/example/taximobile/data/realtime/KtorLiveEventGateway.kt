package org.example.taximobile.data.realtime

import io.ktor.client.HttpClient
import io.ktor.client.plugins.websocket.webSocket
import io.ktor.client.request.header
import io.ktor.http.HttpHeaders
import io.ktor.websocket.Frame
import io.ktor.websocket.readText
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.domain.realtime.LiveEventGateway
import org.example.taximobile.domain.realtime.LiveRideEvent
import kotlinx.coroutines.CancellationException

class KtorLiveEventGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
) : LiveEventGateway {
    override suspend fun listen(
        onConnected: suspend () -> Unit,
        onRideEvent: suspend (LiveRideEvent) -> Unit,
    ) {
        try {
            val token = accessToken()
            client.webSocket(
                urlString = api.websocketEndpoint("events"),
                request = { header(HttpHeaders.Authorization, "Bearer $token") },
            ) {
                onConnected()
                for (frame in incoming) {
                    if (frame !is Frame.Text) continue
                    val event = json.decodeFromString<LiveEventResponse>(frame.readText())
                    onRideEvent(LiveRideEvent(event.type, event.rideId))
                }
            }
        } catch (error: CancellationException) {
            throw error
        } catch (error: AuthenticationRejectedException) {
            throw error
        } catch (error: Exception) {
            // Shared subscription ownership handles bounded reconnect. A failed
            // attempt must never replace REST-confirmed business state.
            throw AuthenticationNetworkException()
        }
    }

    private companion object {
        val json = Json { ignoreUnknownKeys = true }
    }
}

@Serializable
private data class LiveEventResponse(
    val type: String,
    @kotlinx.serialization.SerialName("ride_id") val rideId: String,
)
