package org.example.taximobile.operations.data

import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.HttpHeaders
import io.ktor.http.contentType
import io.ktor.http.isSuccess
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.example.taximobile.operations.model.FixedRouteCommandRequest
import org.example.taximobile.operations.model.FixedRouteCreateRequest
import org.example.taximobile.operations.model.FixedRouteFareOptionList
import org.example.taximobile.operations.model.FixedRouteFareOptionRecord
import org.example.taximobile.operations.model.FixedRouteRecord
import org.example.taximobile.operations.model.FixedRouteRetireRequest
import org.example.taximobile.operations.model.FixedRouteVersionCreateRequest
import org.example.taximobile.operations.model.FixedRouteVersionRecord
import org.example.taximobile.operations.model.PagedResponse

interface FixedRoutesGateway {
    suspend fun list(accessToken: String, cityId: String, operatorId: String): PagedResponse<FixedRouteRecord>
    suspend fun fareOptions(accessToken: String, cityId: String, operatorId: String): List<FixedRouteFareOptionRecord>
    suspend fun create(accessToken: String, cityId: String, request: FixedRouteCreateRequest): FixedRouteRecord
    suspend fun createVersion(
        accessToken: String,
        routeId: String,
        request: FixedRouteVersionCreateRequest,
    ): FixedRouteVersionRecord
    suspend fun transitionVersion(
        accessToken: String,
        version: FixedRouteVersionRecord,
        target: String,
        reason: String,
    ): FixedRouteVersionRecord
    suspend fun retireRoute(accessToken: String, routeId: String, reason: String): FixedRouteRecord
}

class KtorFixedRoutesGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : FixedRoutesGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    override suspend fun list(
        accessToken: String,
        cityId: String,
        operatorId: String,
    ): PagedResponse<FixedRouteRecord> = client.get(endpoints.url("operations/cities/$cityId/fixed-routes")) {
        authorize(accessToken)
        parameter("operator_id", operatorId)
        parameter("page", 1)
        parameter("limit", 100)
    }.decode()

    override suspend fun fareOptions(
        accessToken: String,
        cityId: String,
        operatorId: String,
    ): List<FixedRouteFareOptionRecord> = client.get(
        endpoints.url("operations/cities/$cityId/fixed-route-fare-options"),
    ) {
        authorize(accessToken)
        parameter("operator_id", operatorId)
    }.decode<FixedRouteFareOptionList>().items

    override suspend fun create(
        accessToken: String,
        cityId: String,
        request: FixedRouteCreateRequest,
    ): FixedRouteRecord = post(accessToken, "operations/cities/$cityId/fixed-routes", request)

    override suspend fun createVersion(
        accessToken: String,
        routeId: String,
        request: FixedRouteVersionCreateRequest,
    ): FixedRouteVersionRecord = post(accessToken, "operations/fixed-routes/$routeId/versions", request)

    override suspend fun transitionVersion(
        accessToken: String,
        version: FixedRouteVersionRecord,
        target: String,
        reason: String,
    ): FixedRouteVersionRecord = post(
        accessToken,
        "operations/fixed-route-versions/${version.id}/${target.action()}",
        FixedRouteCommandRequest(version.optimisticVersion, reason.trim()),
    )

    override suspend fun retireRoute(
        accessToken: String,
        routeId: String,
        reason: String,
    ): FixedRouteRecord = post(
        accessToken,
        "operations/fixed-routes/$routeId/retire",
        FixedRouteRetireRequest(reason.trim()),
    )

    private suspend inline fun <reified Request, reified Response> post(
        accessToken: String,
        path: String,
        request: Request,
    ): Response = client.post(endpoints.url(path)) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    private fun String.action(): String = when (this) {
        "IN_REVIEW" -> "submit"
        "PUBLISHED" -> "publish"
        "RETIRED" -> "retire"
        else -> throw IllegalArgumentException("Unsupported fixed-route transition $this")
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorize(accessToken: String) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
    }

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) throw OperationsApiException(status.value, errorDetail(body))
        return runCatching { json.decodeFromString<T>(body) }.getOrElse {
            throw OperationsApiException(status.value, "The fixed-route API returned an unreadable response.")
        }
    }

    private fun errorDetail(body: String): String = runCatching {
        json.parseToJsonElement(body).jsonObject["detail"]?.jsonPrimitive?.content
    }.getOrNull() ?: "The fixed-route API request failed."
}
