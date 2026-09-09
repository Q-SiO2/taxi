package org.example.taximobile.operations.data

import io.ktor.client.HttpClient
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.parameter
import io.ktor.client.request.patch
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
import org.example.taximobile.operations.model.MANAGE_CITY_TARIFFS
import org.example.taximobile.operations.model.MANAGE_OPERATOR_FEE_POLICIES
import org.example.taximobile.operations.model.MANAGE_SCHEDULING_POLICY
import org.example.taximobile.operations.model.OperatorFeePolicyCreateRequest
import org.example.taximobile.operations.model.OperatorFeePolicyRecord
import org.example.taximobile.operations.model.OperatorFeePolicyUpdateRequest
import org.example.taximobile.operations.model.OperationsSession
import org.example.taximobile.operations.model.PagedResponse
import org.example.taximobile.operations.model.PricingEconomicsSnapshot
import org.example.taximobile.operations.model.PricingPolicyCommandRequest
import org.example.taximobile.operations.model.PricingRuleCreateRequest
import org.example.taximobile.operations.model.PricingRuleRecord
import org.example.taximobile.operations.model.PricingRuleUpdateRequest
import org.example.taximobile.operations.model.SchedulingPolicyCreateRequest
import org.example.taximobile.operations.model.SchedulingPolicyRecord
import org.example.taximobile.operations.model.SchedulingPolicyUpdateRequest

/** Isolated API boundary for the Phase 14 reviewed policy lifecycle. */
interface PricingEconomicsGateway {
    suspend fun loadPricingEconomics(
        accessToken: String,
        session: OperationsSession,
        cityId: String,
        operatorId: String?,
    ): PricingEconomicsSnapshot

    suspend fun createPricingRule(accessToken: String, cityId: String, request: PricingRuleCreateRequest): PricingRuleRecord
    suspend fun updatePricingRule(accessToken: String, id: String, request: PricingRuleUpdateRequest): PricingRuleRecord
    suspend fun transitionPricingRule(accessToken: String, record: PricingRuleRecord, target: String, reason: String): PricingRuleRecord

    suspend fun createOperatorFeePolicy(
        accessToken: String,
        cityId: String,
        request: OperatorFeePolicyCreateRequest,
    ): OperatorFeePolicyRecord
    suspend fun updateOperatorFeePolicy(
        accessToken: String,
        id: String,
        request: OperatorFeePolicyUpdateRequest,
    ): OperatorFeePolicyRecord
    suspend fun transitionOperatorFeePolicy(
        accessToken: String,
        record: OperatorFeePolicyRecord,
        target: String,
        reason: String,
    ): OperatorFeePolicyRecord

    suspend fun createSchedulingPolicy(
        accessToken: String,
        cityId: String,
        request: SchedulingPolicyCreateRequest,
    ): SchedulingPolicyRecord
    suspend fun updateSchedulingPolicy(
        accessToken: String,
        id: String,
        request: SchedulingPolicyUpdateRequest,
    ): SchedulingPolicyRecord
    suspend fun transitionSchedulingPolicy(
        accessToken: String,
        record: SchedulingPolicyRecord,
        target: String,
        reason: String,
    ): SchedulingPolicyRecord
}

class KtorPricingEconomicsGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : PricingEconomicsGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    override suspend fun loadPricingEconomics(
        accessToken: String,
        session: OperationsSession,
        cityId: String,
        operatorId: String?,
    ): PricingEconomicsSnapshot = coroutineScope {
        val tariffs = if (session.hasPermission(MANAGE_CITY_TARIFFS)) async {
            list<PricingRuleRecord>(accessToken, "operations/cities/$cityId/pricing-rules", operatorId)
        } else null
        val fees = if (session.hasPermission(MANAGE_OPERATOR_FEE_POLICIES)) async {
            list<OperatorFeePolicyRecord>(accessToken, "operations/cities/$cityId/operator-fee-policies", operatorId)
        } else null
        val schedules = if (session.hasPermission(MANAGE_SCHEDULING_POLICY)) async {
            list<SchedulingPolicyRecord>(accessToken, "operations/cities/$cityId/scheduling-policies", operatorId)
        } else null
        PricingEconomicsSnapshot(
            pricingRules = tariffs?.await(),
            operatorFeePolicies = fees?.await(),
            schedulingPolicies = schedules?.await(),
        )
    }

    override suspend fun createPricingRule(
        accessToken: String,
        cityId: String,
        request: PricingRuleCreateRequest,
    ): PricingRuleRecord = post(accessToken, "operations/cities/$cityId/pricing-rules", request)

    override suspend fun updatePricingRule(
        accessToken: String,
        id: String,
        request: PricingRuleUpdateRequest,
    ): PricingRuleRecord = patch(accessToken, "operations/pricing-rules/$id", request)

    override suspend fun transitionPricingRule(
        accessToken: String,
        record: PricingRuleRecord,
        target: String,
        reason: String,
    ): PricingRuleRecord = command(
        accessToken,
        "operations/pricing-rules/${record.id}/${target.action()}",
        record.optimisticVersion,
        reason,
    )

    override suspend fun createOperatorFeePolicy(
        accessToken: String,
        cityId: String,
        request: OperatorFeePolicyCreateRequest,
    ): OperatorFeePolicyRecord = post(accessToken, "operations/cities/$cityId/operator-fee-policies", request)

    override suspend fun updateOperatorFeePolicy(
        accessToken: String,
        id: String,
        request: OperatorFeePolicyUpdateRequest,
    ): OperatorFeePolicyRecord = patch(accessToken, "operations/operator-fee-policies/$id", request)

    override suspend fun transitionOperatorFeePolicy(
        accessToken: String,
        record: OperatorFeePolicyRecord,
        target: String,
        reason: String,
    ): OperatorFeePolicyRecord = command(
        accessToken,
        "operations/operator-fee-policies/${record.id}/${target.action()}",
        record.optimisticVersion,
        reason,
    )

    override suspend fun createSchedulingPolicy(
        accessToken: String,
        cityId: String,
        request: SchedulingPolicyCreateRequest,
    ): SchedulingPolicyRecord = post(accessToken, "operations/cities/$cityId/scheduling-policies", request)

    override suspend fun updateSchedulingPolicy(
        accessToken: String,
        id: String,
        request: SchedulingPolicyUpdateRequest,
    ): SchedulingPolicyRecord = patch(accessToken, "operations/scheduling-policies/$id", request)

    override suspend fun transitionSchedulingPolicy(
        accessToken: String,
        record: SchedulingPolicyRecord,
        target: String,
        reason: String,
    ): SchedulingPolicyRecord = command(
        accessToken,
        "operations/scheduling-policies/${record.id}/${target.action()}",
        record.optimisticVersion,
        reason,
    )

    private suspend inline fun <reified T> list(
        accessToken: String,
        path: String,
        operatorId: String?,
    ): PagedResponse<T> = client.get(endpoints.url(path)) {
        authorize(accessToken)
        operatorId?.let { parameter("operator_id", it) }
        parameter("page", 1)
        parameter("limit", 100)
    }.decode()

    private suspend inline fun <reified Request, reified Response> post(
        accessToken: String,
        path: String,
        request: Request,
    ): Response = client.post(endpoints.url(path)) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    private suspend inline fun <reified Request, reified Response> patch(
        accessToken: String,
        path: String,
        request: Request,
    ): Response = client.patch(endpoints.url(path)) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    private suspend inline fun <reified Response> command(
        accessToken: String,
        path: String,
        expectedVersion: Int,
        reason: String,
    ): Response = post(
        accessToken,
        path,
        PricingPolicyCommandRequest(expectedVersion, reason.trim()),
    )

    private fun String.action(): String = when (this) {
        "IN_REVIEW" -> "submit"
        "ACTIVE" -> "activate"
        else -> throw IllegalArgumentException("Unsupported pricing-policy transition $this")
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorize(accessToken: String) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
    }

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) throw OperationsApiException(status.value, errorDetail(body, status.value))
        return try {
            json.decodeFromString<T>(body)
        } catch (_: Throwable) {
            throw OperationsApiException(status.value, "The pricing API returned an unreadable response.")
        }
    }

    private fun errorDetail(body: String, statusCode: Int): String {
        if (body.isBlank()) return "The pricing API returned HTTP $statusCode."
        return runCatching {
            json.parseToJsonElement(body).jsonObject["detail"].toPricingDisplayMessage()
                ?: "The pricing API returned HTTP $statusCode."
        }.getOrElse { "The pricing API returned HTTP $statusCode." }
    }
}

private fun JsonElement?.toPricingDisplayMessage(): String? = when (this) {
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
