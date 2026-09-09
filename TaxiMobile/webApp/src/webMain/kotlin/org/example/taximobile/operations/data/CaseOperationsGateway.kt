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
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import org.example.taximobile.operations.model.CaseAlertAcknowledgeCommand
import org.example.taximobile.operations.model.CaseAlertRecord
import org.example.taximobile.operations.model.CaseOperationsSnapshot
import org.example.taximobile.operations.model.MANAGE_SAFETY_CASES
import org.example.taximobile.operations.model.MANAGE_SUPPORT_CASES
import org.example.taximobile.operations.model.MANAGE_CASE_RETENTION
import org.example.taximobile.operations.model.LegalHoldCreateCommand
import org.example.taximobile.operations.model.LegalHoldReleaseCommand
import org.example.taximobile.operations.model.LegalHoldRecord
import org.example.taximobile.operations.model.CaseRetentionActionRecord
import org.example.taximobile.operations.model.OperationsSession
import org.example.taximobile.operations.model.PagedResponse
import org.example.taximobile.operations.model.SafetyCaseDetail
import org.example.taximobile.operations.model.SafetyCaseSummary
import org.example.taximobile.operations.model.SafetyTransitionCommand
import org.example.taximobile.operations.model.SupportCaseDetail
import org.example.taximobile.operations.model.SupportCaseSummary
import org.example.taximobile.operations.model.SupportSafetyEscalationCommand
import org.example.taximobile.operations.model.SupportSafetyEscalationReceipt
import org.example.taximobile.operations.model.SupportTransitionCommand
import org.example.taximobile.operations.model.SupportTriageCommand

interface CaseOperationsGateway {
    suspend fun load(
        accessToken: String,
        session: OperationsSession,
        cityId: String?,
    ): CaseOperationsSnapshot

    suspend fun supportCase(accessToken: String, ticketId: String): SupportCaseDetail
    suspend fun safetyCase(accessToken: String, reportId: String): SafetyCaseDetail

    suspend fun triageSupport(
        accessToken: String,
        ticketId: String,
        idempotencyKey: String,
        command: SupportTriageCommand,
    ): SupportCaseDetail

    suspend fun transitionSupport(
        accessToken: String,
        ticketId: String,
        idempotencyKey: String,
        command: SupportTransitionCommand,
    ): SupportCaseDetail

    suspend fun escalateSupport(
        accessToken: String,
        ticketId: String,
        idempotencyKey: String,
        command: SupportSafetyEscalationCommand,
    ): SupportSafetyEscalationReceipt

    suspend fun transitionSafety(
        accessToken: String,
        reportId: String,
        idempotencyKey: String,
        command: SafetyTransitionCommand,
    ): SafetyCaseDetail

    suspend fun acknowledgeAlert(
        accessToken: String,
        alertId: String,
        idempotencyKey: String,
        reason: String,
    ): CaseAlertRecord

    suspend fun placeLegalHold(
        accessToken: String,
        idempotencyKey: String,
        command: LegalHoldCreateCommand,
    ): LegalHoldRecord

    suspend fun releaseLegalHold(
        accessToken: String,
        holdId: String,
        idempotencyKey: String,
        reasonCode: String,
    ): LegalHoldRecord
}

class KtorCaseOperationsGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : CaseOperationsGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    override suspend fun load(
        accessToken: String,
        session: OperationsSession,
        cityId: String?,
    ): CaseOperationsSnapshot = coroutineScope {
        val support = if (session.hasPermission(MANAGE_SUPPORT_CASES)) async {
            client.get(endpoints.url("operations/support/tickets")) {
                authorize(accessToken)
                cityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<SupportCaseSummary>>()
        } else null
        val safety = if (session.hasPermission(MANAGE_SAFETY_CASES)) async {
            client.get(endpoints.url("operations/safety/reports")) {
                authorize(accessToken)
                cityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<SafetyCaseSummary>>()
        } else null
        val alerts = if (
            session.hasPermission(MANAGE_SUPPORT_CASES) ||
            session.hasPermission(MANAGE_SAFETY_CASES)
        ) async {
            client.get(endpoints.url("operations/case-alerts")) {
                authorize(accessToken)
                cityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<CaseAlertRecord>>()
        } else null
        val holds = if (session.hasPermission(MANAGE_CASE_RETENTION)) async {
            client.get(endpoints.url("operations/case-retention/holds")) {
                authorize(accessToken)
                cityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<LegalHoldRecord>>()
        } else null
        val retentionActions = if (session.hasPermission(MANAGE_CASE_RETENTION)) async {
            client.get(endpoints.url("operations/case-retention/actions")) {
                authorize(accessToken)
                cityId?.let { parameter("city_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<CaseRetentionActionRecord>>()
        } else null

        CaseOperationsSnapshot(
            supportCases = support?.await(),
            safetyCases = safety?.await(),
            alerts = alerts?.await(),
            legalHolds = holds?.await(),
            retentionActions = retentionActions?.await(),
        )
    }

    override suspend fun supportCase(accessToken: String, ticketId: String): SupportCaseDetail =
        client.get(endpoints.url("operations/support/tickets/$ticketId")) {
            authorize(accessToken)
        }.decode()

    override suspend fun safetyCase(accessToken: String, reportId: String): SafetyCaseDetail =
        client.get(endpoints.url("operations/safety/reports/$reportId")) {
            authorize(accessToken)
        }.decode()

    override suspend fun triageSupport(
        accessToken: String,
        ticketId: String,
        idempotencyKey: String,
        command: SupportTriageCommand,
    ): SupportCaseDetail = client.post(endpoints.url("operations/support/tickets/$ticketId/triage")) {
        authorizeCommand(accessToken, idempotencyKey)
        setBody(command)
    }.decode()

    override suspend fun transitionSupport(
        accessToken: String,
        ticketId: String,
        idempotencyKey: String,
        command: SupportTransitionCommand,
    ): SupportCaseDetail = client.post(endpoints.url("operations/support/tickets/$ticketId/transition")) {
        authorizeCommand(accessToken, idempotencyKey)
        setBody(command)
    }.decode()

    override suspend fun escalateSupport(
        accessToken: String,
        ticketId: String,
        idempotencyKey: String,
        command: SupportSafetyEscalationCommand,
    ): SupportSafetyEscalationReceipt = client.post(
        endpoints.url("operations/support/tickets/$ticketId/escalate-safety"),
    ) {
        authorizeCommand(accessToken, idempotencyKey)
        setBody(command)
    }.decode()

    override suspend fun transitionSafety(
        accessToken: String,
        reportId: String,
        idempotencyKey: String,
        command: SafetyTransitionCommand,
    ): SafetyCaseDetail = client.post(endpoints.url("operations/safety/reports/$reportId/transition")) {
        authorizeCommand(accessToken, idempotencyKey)
        setBody(command)
    }.decode()

    override suspend fun acknowledgeAlert(
        accessToken: String,
        alertId: String,
        idempotencyKey: String,
        reason: String,
    ): CaseAlertRecord = client.post(endpoints.url("operations/case-alerts/$alertId/acknowledge")) {
        authorizeCommand(accessToken, idempotencyKey)
        setBody(CaseAlertAcknowledgeCommand(reason.trim()))
    }.decode()

    override suspend fun placeLegalHold(
        accessToken: String,
        idempotencyKey: String,
        command: LegalHoldCreateCommand,
    ): LegalHoldRecord = client.post(endpoints.url("operations/case-retention/holds")) {
        authorizeCommand(accessToken, idempotencyKey)
        setBody(command)
    }.decode()

    override suspend fun releaseLegalHold(
        accessToken: String,
        holdId: String,
        idempotencyKey: String,
        reasonCode: String,
    ): LegalHoldRecord = client.post(endpoints.url("operations/case-retention/holds/$holdId/release")) {
        authorizeCommand(accessToken, idempotencyKey)
        setBody(LegalHoldReleaseCommand(reasonCode))
    }.decode()

    private fun io.ktor.client.request.HttpRequestBuilder.authorize(accessToken: String) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorizeCommand(
        accessToken: String,
        idempotencyKey: String,
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
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
                "The case operations API returned an unreadable response.",
            )
        }
    }

    private fun errorDetail(body: String, statusCode: Int): String {
        if (body.isBlank()) return "The case operations API returned HTTP $statusCode."
        return runCatching {
            json.parseToJsonElement(body).jsonObject["detail"].toCaseDisplayMessage()
                ?: "The case operations API returned HTTP $statusCode."
        }.getOrElse { "The case operations API returned HTTP $statusCode." }
    }
}

private fun JsonElement?.toCaseDisplayMessage(): String? = when (this) {
    is JsonPrimitive -> contentOrNull
    is JsonArray -> mapNotNull { item ->
        when (item) {
            is JsonObject -> (item["msg"] as? JsonPrimitive)?.contentOrNull
            is JsonPrimitive -> item.contentOrNull
            else -> null
        }
    }.joinToString(" ").ifBlank { null }
    else -> null
}
