package org.example.taximobile.operations.data

import io.ktor.client.HttpClient
import io.ktor.client.request.header
import io.ktor.client.request.get
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
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import org.example.taximobile.operations.model.AdministrativeGrantCreateRequest
import org.example.taximobile.operations.model.AdministrativeGrantChangeRequestRecord
import org.example.taximobile.operations.model.AdministrativeGrantDecisionRequest
import org.example.taximobile.operations.model.AdministrativeGrantRevocationRequest
import org.example.taximobile.operations.model.AdministrativeGrantRecord
import org.example.taximobile.operations.model.PagedResponse

interface StaffAccessGateway {
    suspend fun listActiveGrants(accessToken: String, marketId: String, page: Int): PagedResponse<AdministrativeGrantRecord>
    suspend fun listPendingRequests(accessToken: String, marketId: String, page: Int): PagedResponse<AdministrativeGrantChangeRequestRecord>

    suspend fun requestGrant(
        accessToken: String,
        idempotencyKey: String,
        request: AdministrativeGrantCreateRequest,
    ): AdministrativeGrantChangeRequestRecord

    suspend fun requestRevocation(
        accessToken: String,
        idempotencyKey: String,
        request: AdministrativeGrantRevocationRequest,
    ): AdministrativeGrantChangeRequestRecord

    suspend fun decide(
        accessToken: String,
        idempotencyKey: String,
        requestId: String,
        decision: String,
        request: AdministrativeGrantDecisionRequest,
    ): AdministrativeGrantChangeRequestRecord
}

class KtorStaffAccessGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : StaffAccessGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    override suspend fun listActiveGrants(
        accessToken: String,
        marketId: String,
        page: Int,
    ): PagedResponse<AdministrativeGrantRecord> {
        require(page >= 1)
        return client.get(endpoints.url("operations/administrative-grants")) {
            header(HttpHeaders.Authorization, "Bearer $accessToken")
            parameter("market_id", marketId)
            parameter("include_revoked", false)
            parameter("page", page)
            parameter("limit", 100)
        }.decode()
    }

    override suspend fun listPendingRequests(
        accessToken: String,
        marketId: String,
        page: Int,
    ): PagedResponse<AdministrativeGrantChangeRequestRecord> {
        require(page >= 1)
        return client.get(endpoints.url("operations/administrative-grant-requests")) {
            header(HttpHeaders.Authorization, "Bearer $accessToken")
            parameter("market_id", marketId)
            parameter("status", "PENDING")
            parameter("page", page)
            parameter("limit", 100)
        }.decode()
    }

    override suspend fun requestGrant(
        accessToken: String,
        idempotencyKey: String,
        request: AdministrativeGrantCreateRequest,
    ): AdministrativeGrantChangeRequestRecord = client.post(
        endpoints.url("operations/administrative-grant-requests/create")
    ) {
        authorizeCommand(accessToken, idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun requestRevocation(
        accessToken: String,
        idempotencyKey: String,
        request: AdministrativeGrantRevocationRequest,
    ): AdministrativeGrantChangeRequestRecord = client.post(
        endpoints.url("operations/administrative-grant-requests/revoke")
    ) {
        authorizeCommand(accessToken, idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun decide(
        accessToken: String,
        idempotencyKey: String,
        requestId: String,
        decision: String,
        request: AdministrativeGrantDecisionRequest,
    ): AdministrativeGrantChangeRequestRecord {
        val decisionPath = when (decision) {
            "approve" -> "approve"
            "reject" -> "reject"
            "cancel" -> "cancel"
            else -> error("Unsupported staff-grant decision")
        }
        return client.post(
            endpoints.url("operations/administrative-grant-requests/$requestId/$decisionPath")
        ) {
            authorizeCommand(accessToken, idempotencyKey)
            contentType(ContentType.Application.Json)
            setBody(request)
        }.decode()
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorizeCommand(
        accessToken: String,
        idempotencyKey: String,
    ) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
        header("Idempotency-Key", idempotencyKey)
    }

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) {
            throw OperationsApiException(status.value, detail(body).ifBlank { "Request failed (${status.value})." })
        }
        return runCatching { json.decodeFromString<T>(body) }.getOrElse {
            throw OperationsApiException(status.value, "The staff-access API returned an unreadable response.")
        }
    }

    private fun detail(body: String): String = runCatching {
        when (val element = json.parseToJsonElement(body)) {
            is JsonObject -> detailValue(element["detail"])
                .ifBlank { detailValue((element["error"] as? JsonObject)?.get("message")) }
            else -> body
        }
    }.getOrDefault(body)

    private fun detailValue(value: JsonElement?): String = when (value) {
        is JsonPrimitive -> value.contentOrNull.orEmpty()
        is JsonArray -> value.joinToString("; ") { item ->
            (item as? JsonObject)?.get("msg")?.let(::detailValue).orEmpty()
        }
        is JsonObject -> value["msg"]?.let(::detailValue).orEmpty().ifBlank { value.toString() }
        null -> ""
    }
}
