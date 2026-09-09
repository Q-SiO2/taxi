package org.example.taximobile.data.places

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.parameter
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.places.PlaceAttribution
import org.example.taximobile.domain.places.PlaceDiscoveryGateway
import org.example.taximobile.domain.places.PlaceKind
import org.example.taximobile.domain.places.PlaceResult
import org.example.taximobile.domain.places.PlaceSearch
import org.example.taximobile.domain.places.ReversePlace
import org.example.taximobile.domain.rides.Coordinates

class KtorPlaceDiscoveryGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
    private val language: () -> String = { "en" },
) : PlaceDiscoveryGateway {
    override suspend fun search(cityId: String, query: String): PlaceSearch = request {
        val response = client.get(api.endpoint("places/search")) {
            authorize()
            parameter("city_id", cityId)
            parameter("query", query.trim())
            parameter("language", normalizedPlaceLanguage(language()))
            parameter("limit", 8)
        }
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "Place search is unavailable.")
        }
        response.body<PlaceSearchResponse>().toDomain()
    }

    override suspend fun reverse(cityId: String, coordinate: Coordinates): ReversePlace = request {
        val response = client.get(api.endpoint("places/reverse")) {
            authorize()
            parameter("city_id", cityId)
            parameter("latitude", coordinate.latitude)
            parameter("longitude", coordinate.longitude)
            parameter("language", normalizedPlaceLanguage(language()))
        }
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "Address lookup is unavailable.")
        }
        response.body<ReversePlaceResponse>().toDomain()
    }

    private suspend fun <T> request(block: suspend () -> T): T = try {
        block()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (_: Exception) {
        throw AuthenticationNetworkException()
    }

    private suspend fun io.ktor.client.request.HttpRequestBuilder.authorize() {
        header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
    }
}

internal fun normalizedPlaceLanguage(languageTag: String): String = when (
    languageTag.substringBefore('-').substringBefore('_').lowercase()
) {
    "ar" -> "ar"
    "fr" -> "fr"
    else -> "en"
}

@Serializable
private data class PlaceCoordinateResponse(val latitude: Double, val longitude: Double)

@Serializable
private data class PlaceAttributionResponse(val text: String, val url: String) {
    fun toDomain() = PlaceAttribution(text, url)
}

@Serializable
private data class PlaceResultResponse(
    val id: String,
    @SerialName("primary_text") val primaryText: String,
    @SerialName("secondary_text") val secondaryText: String? = null,
    val coordinate: PlaceCoordinateResponse,
    val kind: String,
    @SerialName("pickup_serviceable") val pickupServiceable: Boolean,
) {
    fun toDomain() = PlaceResult(
        id = id,
        primaryText = primaryText,
        secondaryText = secondaryText,
        coordinate = Coordinates(coordinate.latitude, coordinate.longitude),
        kind = runCatching { PlaceKind.valueOf(kind) }.getOrDefault(PlaceKind.UNKNOWN),
        pickupServiceable = pickupServiceable,
    )
}

@Serializable
private data class PlaceSearchResponse(
    @SerialName("city_id") val cityId: String,
    val query: String,
    val items: List<PlaceResultResponse>,
    val attribution: PlaceAttributionResponse,
) {
    fun toDomain() = PlaceSearch(cityId, query, items.map { it.toDomain() }, attribution.toDomain())
}

@Serializable
private data class ReversePlaceResponse(
    @SerialName("city_id") val cityId: String,
    val item: PlaceResultResponse? = null,
    val attribution: PlaceAttributionResponse,
) {
    fun toDomain() = ReversePlace(cityId, item?.toDomain(), attribution.toDomain())
}
