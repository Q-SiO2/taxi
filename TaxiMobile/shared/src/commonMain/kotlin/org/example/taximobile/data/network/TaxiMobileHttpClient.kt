package org.example.taximobile.data.network

import io.ktor.client.HttpClientConfig
import io.ktor.client.plugins.DefaultRequest
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.client.request.header
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

enum class TaxiMobileClientSurface {
    ANDROID_PASSENGER,
    ANDROID_DRIVER,
    IOS_PASSENGER,
    IOS_DRIVER,
    WEB_APPLICANT,
    WEB_OPERATIONS,
}

data class TaxiMobileClientIdentity(
    val surface: TaxiMobileClientSurface,
    val version: String,
    val build: String,
) {
    init {
        val numericBuild = build.toLongOrNull()
        require(CLIENT_VERSION_PATTERN.matches(version)) {
            "TaxiMobile client version must be a numeric release version."
        }
        require(
            CLIENT_BUILD_PATTERN.matches(build) &&
                numericBuild != null &&
                numericBuild in 1L..2_147_483_647L
        ) {
            "TaxiMobile client build must be a positive bounded integer."
        }
    }
}

/** Apply this configuration from a platform-specific Ktor client engine. */
fun HttpClientConfig<*>.configureTaxiMobileTransport(
    identity: TaxiMobileClientIdentity? = null,
) {
    install(WebSockets)
    if (identity != null) {
        install(DefaultRequest) {
            header("X-TaxiMobile-Client", identity.surface.name)
            header("X-TaxiMobile-Version", identity.version)
            header("X-TaxiMobile-Build", identity.build)
        }
    }
    install(ContentNegotiation) {
        json(Json {
            ignoreUnknownKeys = true
            explicitNulls = false
        })
    }
}

private val CLIENT_VERSION_PATTERN = Regex(
    "(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(\\.(0|[1-9][0-9]*))?"
)
private val CLIENT_BUILD_PATTERN = Regex("[1-9][0-9]{0,9}")
