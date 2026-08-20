package org.example.taximobile.data.routing

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.HttpStatusCode
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import org.example.taximobile.core.network.ApiConfiguration
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.routing.RouteManeuver
import org.example.taximobile.domain.routing.RoutePlan
import org.example.taximobile.domain.routing.RoutingGateway

class KtorRoutingGateway(
    private val client: HttpClient,
    private val api: ApiConfiguration,
    private val accessToken: suspend () -> String,
    private val language: () -> String = { "en" },
) : RoutingGateway {
    override suspend fun route(origin: Coordinates, destination: Coordinates): RoutePlan = try {
        val response = client.post(api.endpoint("routing/route")) {
            header(HttpHeaders.Authorization, "Bearer ${accessToken()}")
            contentType(ContentType.Application.Json)
            setBody(RouteRequest(origin.toRequest(), destination.toRequest(), normalizedLanguage(language())))
        }
        if (response.status == HttpStatusCode.Unauthorized) throw AuthenticationRejectedException()
        if (!response.status.isSuccess()) {
            throw ApiRequestException(response.status.value, "A driving route is temporarily unavailable.")
        }
        response.body<RouteResponse>().toRoutePlan()
    } catch (error: AuthenticationRejectedException) {
        throw error
    } catch (error: ApiRequestException) {
        throw error
    } catch (_: Exception) {
        throw AuthenticationNetworkException()
    }
}

private fun Coordinates.toRequest() = CoordinateDto(latitude, longitude)

@Serializable
private data class RouteRequest(val origin: CoordinateDto, val destination: CoordinateDto, val language: String)

internal fun normalizedLanguage(languageTag: String): String = when (
    languageTag.substringBefore('-').substringBefore('_').lowercase()
) {
    "ar" -> "ar"
    "fr" -> "fr"
    else -> "en"
}

@Serializable
private data class CoordinateDto(val latitude: Double, val longitude: Double)

@Serializable
private data class RouteResponse(
    @SerialName("distance_meters") val distanceMeters: Int,
    @SerialName("duration_seconds") val durationSeconds: Int,
    val geometry: List<CoordinateDto>,
    val maneuvers: List<RouteManeuverDto>,
) {
    fun toRoutePlan() = RoutePlan(
        distanceMeters = distanceMeters,
        durationSeconds = durationSeconds,
        geometry = geometry.map { Coordinates(it.latitude, it.longitude) },
        maneuvers = maneuvers.map { it.toDomain() },
    )
}

@Serializable
private data class RouteManeuverDto(
    val instruction: String,
    @SerialName("distance_meters") val distanceMeters: Int,
    @SerialName("duration_seconds") val durationSeconds: Int,
    @SerialName("begin_shape_index") val beginShapeIndex: Int,
    @SerialName("end_shape_index") val endShapeIndex: Int,
) {
    fun toDomain() = RouteManeuver(
        instruction,
        distanceMeters,
        durationSeconds,
        beginShapeIndex,
        endShapeIndex,
    )
}
