package org.example.taximobile.data.network

import io.ktor.client.HttpClientConfig
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

/** Apply this configuration from a platform-specific Ktor client engine. */
fun HttpClientConfig<*>.configureTaxiMobileTransport() {
    install(WebSockets)
    install(ContentNegotiation) {
        json(Json {
            ignoreUnknownKeys = true
            explicitNulls = false
        })
    }
}
