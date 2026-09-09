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
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.example.taximobile.operations.model.PagedResponse
import org.example.taximobile.operations.model.SecurityIncidentCreateRequest
import org.example.taximobile.operations.model.SecurityIncidentPostmortemCompleteRequest
import org.example.taximobile.operations.model.SecurityIncidentRecord
import org.example.taximobile.operations.model.SecurityIncidentResponsibilityAssignRequest
import org.example.taximobile.operations.model.SecurityIncidentResponsibilityRecord
import org.example.taximobile.operations.model.SecurityIncidentTimelineCreateRequest
import org.example.taximobile.operations.model.SecurityIncidentTimelineRecord
import org.example.taximobile.operations.model.SecurityIncidentTransitionRequest
import org.example.taximobile.operations.model.SecurityIncidentWorkspace

interface SecurityIncidentGateway {
    suspend fun load(
        accessToken: String,
        marketId: String?,
    ): SecurityIncidentWorkspace

    suspend fun create(
        accessToken: String,
        idempotencyKey: String,
        request: SecurityIncidentCreateRequest,
    ): SecurityIncidentRecord

    suspend fun get(accessToken: String, incidentId: String): SecurityIncidentRecord

    suspend fun timeline(
        accessToken: String,
        incidentId: String,
    ): PagedResponse<SecurityIncidentTimelineRecord>

    suspend fun responsibilities(
        accessToken: String,
        incidentId: String,
    ): PagedResponse<SecurityIncidentResponsibilityRecord>

    suspend fun appendTimeline(
        accessToken: String,
        incidentId: String,
        idempotencyKey: String,
        request: SecurityIncidentTimelineCreateRequest,
    ): SecurityIncidentTimelineRecord

    suspend fun transition(
        accessToken: String,
        incidentId: String,
        idempotencyKey: String,
        request: SecurityIncidentTransitionRequest,
    ): SecurityIncidentRecord

    suspend fun completePostmortem(
        accessToken: String,
        incidentId: String,
        idempotencyKey: String,
        request: SecurityIncidentPostmortemCompleteRequest,
    ): SecurityIncidentRecord

    suspend fun assignResponsibility(
        accessToken: String,
        incidentId: String,
        responsibility: String,
        idempotencyKey: String,
        request: SecurityIncidentResponsibilityAssignRequest,
    ): SecurityIncidentResponsibilityRecord
}

class KtorSecurityIncidentGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : SecurityIncidentGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    override suspend fun load(
        accessToken: String,
        marketId: String?,
    ): SecurityIncidentWorkspace = SecurityIncidentWorkspace(
        incidents = client.get(endpoints.url("operations/security-incidents")) {
            authorize(accessToken)
            marketId?.let { parameter("market_id", it) }
            parameter("page", 1)
            parameter("limit", 100)
        }.decode(),
    )

    override suspend fun create(
        accessToken: String,
        idempotencyKey: String,
        request: SecurityIncidentCreateRequest,
    ): SecurityIncidentRecord = client.post(
        endpoints.url("operations/security-incidents")
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun get(
        accessToken: String,
        incidentId: String,
    ): SecurityIncidentRecord = client.get(
        endpoints.url("operations/security-incidents/$incidentId")
    ) { authorize(accessToken) }.decode()

    override suspend fun timeline(
        accessToken: String,
        incidentId: String,
    ): PagedResponse<SecurityIncidentTimelineRecord> = client.get(
        endpoints.url("operations/security-incidents/$incidentId/timeline")
    ) {
        authorize(accessToken)
        parameter("page", 1)
        parameter("limit", 100)
    }.decode()

    override suspend fun responsibilities(
        accessToken: String,
        incidentId: String,
    ): PagedResponse<SecurityIncidentResponsibilityRecord> = client.get(
        endpoints.url("operations/security-incidents/$incidentId/responsibilities")
    ) {
        authorize(accessToken)
        parameter("page", 1)
        parameter("limit", 100)
    }.decode()

    override suspend fun appendTimeline(
        accessToken: String,
        incidentId: String,
        idempotencyKey: String,
        request: SecurityIncidentTimelineCreateRequest,
    ): SecurityIncidentTimelineRecord = client.post(
        endpoints.url("operations/security-incidents/$incidentId/timeline")
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun transition(
        accessToken: String,
        incidentId: String,
        idempotencyKey: String,
        request: SecurityIncidentTransitionRequest,
    ): SecurityIncidentRecord = client.post(
        endpoints.url("operations/security-incidents/$incidentId/transitions")
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun completePostmortem(
        accessToken: String,
        incidentId: String,
        idempotencyKey: String,
        request: SecurityIncidentPostmortemCompleteRequest,
    ): SecurityIncidentRecord = client.post(
        endpoints.url("operations/security-incidents/$incidentId/postmortem/complete")
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun assignResponsibility(
        accessToken: String,
        incidentId: String,
        responsibility: String,
        idempotencyKey: String,
        request: SecurityIncidentResponsibilityAssignRequest,
    ): SecurityIncidentResponsibilityRecord {
        val responsibilityId = responsibilityPath(responsibility)
        return client.post(
            endpoints.url(
                "operations/security-incidents/$incidentId/responsibilities/$responsibilityId/assign"
            )
        ) {
            authorize(accessToken)
            header("Idempotency-Key", idempotencyKey)
            contentType(ContentType.Application.Json)
            setBody(request)
        }.decode()
    }

    private fun responsibilityPath(responsibility: String): String = when (responsibility) {
        "SECURITY_RESPONSE_LEAD" -> "SECURITY_RESPONSE_LEAD"
        "COMMUNICATIONS_LEAD" -> "COMMUNICATIONS_LEAD"
        "OPERATIONS_LIAISON" -> "OPERATIONS_LIAISON"
        "POSTMORTEM_OWNER" -> "POSTMORTEM_OWNER"
        else -> error("Unsupported security-incident responsibility")
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorize(accessToken: String) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
    }

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) {
            throw OperationsApiException(status.value, errorDetail(body, status.value))
        }
        return try {
            json.decodeFromString<T>(body)
        } catch (_: Throwable) {
            throw OperationsApiException(
                status.value,
                "The security-incident API returned an unreadable response.",
            )
        }
    }

    private fun errorDetail(body: String, statusCode: Int): String = runCatching {
        val root = json.parseToJsonElement(body).jsonObject
        val detail = root["detail"] ?: root["error"]?.jsonObject?.get("message")
        detail?.jsonPrimitive?.contentOrNull
    }.getOrNull() ?: "Security-incident request failed ($statusCode)."
}
