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
import org.example.taximobile.operations.model.MANAGE_PAYMENT_CAPABILITIES
import org.example.taximobile.operations.model.ManualTransferReconciliationRecord
import org.example.taximobile.operations.model.ManualTransferRejectRequest
import org.example.taximobile.operations.model.ManualTransferVerifyRequest
import org.example.taximobile.operations.model.OperationsSession
import org.example.taximobile.operations.model.PagedResponse
import org.example.taximobile.operations.model.PaymentCapabilityCommandRequest
import org.example.taximobile.operations.model.PaymentCapabilityCreateRequest
import org.example.taximobile.operations.model.PaymentCapabilityRecord
import org.example.taximobile.operations.model.PaymentOperationsSnapshot
import org.example.taximobile.operations.model.PaymentRecipientCommandRequest
import org.example.taximobile.operations.model.PaymentRecipientCreateRequest
import org.example.taximobile.operations.model.PaymentRecipientRecord
import org.example.taximobile.operations.model.PaymentRefundCreateRequest
import org.example.taximobile.operations.model.PaymentRefundRecord
import org.example.taximobile.operations.model.RECONCILE_PAYMENTS

interface PaymentOperationsGateway {
    suspend fun load(
        accessToken: String,
        session: OperationsSession,
        cityId: String?,
        operatorId: String?,
    ): PaymentOperationsSnapshot

    suspend fun createRecipient(
        accessToken: String,
        cityId: String,
        request: PaymentRecipientCreateRequest,
    ): PaymentRecipientRecord

    suspend fun transitionRecipient(
        accessToken: String,
        record: PaymentRecipientRecord,
        target: String,
        reason: String,
    ): PaymentRecipientRecord

    suspend fun createCapability(
        accessToken: String,
        cityId: String,
        request: PaymentCapabilityCreateRequest,
    ): PaymentCapabilityRecord

    suspend fun transitionCapability(
        accessToken: String,
        record: PaymentCapabilityRecord,
        target: String,
        reason: String,
    ): PaymentCapabilityRecord

    suspend fun verifyTransfer(
        accessToken: String,
        paymentId: String,
        idempotencyKey: String,
        settlementReference: String,
    ): ManualTransferReconciliationRecord

    suspend fun rejectTransfer(
        accessToken: String,
        paymentId: String,
        idempotencyKey: String,
        reason: String,
    ): ManualTransferReconciliationRecord

    suspend fun recordRefund(
        accessToken: String,
        paymentId: String,
        idempotencyKey: String,
        request: PaymentRefundCreateRequest,
    ): PaymentRefundRecord
}

class KtorPaymentOperationsGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : PaymentOperationsGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    override suspend fun load(
        accessToken: String,
        session: OperationsSession,
        cityId: String?,
        operatorId: String?,
    ): PaymentOperationsSnapshot = coroutineScope {
        val recipients = if (cityId != null && session.hasPermission(MANAGE_PAYMENT_CAPABILITIES)) async {
            getPage<PaymentRecipientRecord>(
                accessToken,
                "operations/cities/$cityId/payment-recipient-accounts",
                operatorId,
            )
        } else null
        val capabilities = if (cityId != null && session.hasPermission(MANAGE_PAYMENT_CAPABILITIES)) async {
            getPage<PaymentCapabilityRecord>(
                accessToken,
                "operations/cities/$cityId/payment-capability-versions",
                operatorId,
            )
        } else null
        val transfers = if (session.hasPermission(RECONCILE_PAYMENTS)) async {
            client.get(endpoints.url("operations/payments/manual-transfers")) {
                authorize(accessToken)
                cityId?.let { parameter("city_id", it) }
                operatorId?.let { parameter("operator_id", it) }
                parameter("status", "SUBMITTED")
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<ManualTransferReconciliationRecord>>()
        } else null
        val refunds = if (session.hasPermission(RECONCILE_PAYMENTS)) async {
            client.get(endpoints.url("operations/payments/refunds")) {
                authorize(accessToken)
                cityId?.let { parameter("city_id", it) }
                operatorId?.let { parameter("operator_id", it) }
                parameter("page", 1)
                parameter("limit", 100)
            }.decode<PagedResponse<PaymentRefundRecord>>()
        } else null
        PaymentOperationsSnapshot(
            recipients = recipients?.await(),
            capabilities = capabilities?.await(),
            manualTransfers = transfers?.await(),
            refunds = refunds?.await(),
        )
    }

    override suspend fun createRecipient(
        accessToken: String,
        cityId: String,
        request: PaymentRecipientCreateRequest,
    ): PaymentRecipientRecord = client.post(
        endpoints.url("operations/cities/$cityId/payment-recipient-accounts")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun transitionRecipient(
        accessToken: String,
        record: PaymentRecipientRecord,
        target: String,
        reason: String,
    ): PaymentRecipientRecord = client.post(
        endpoints.url("operations/payment-recipient-accounts/${record.id}/${paymentRecipientAction(target)}")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(PaymentRecipientCommandRequest(record.optimisticVersion, reason))
    }.decode()

    override suspend fun createCapability(
        accessToken: String,
        cityId: String,
        request: PaymentCapabilityCreateRequest,
    ): PaymentCapabilityRecord = client.post(
        endpoints.url("operations/cities/$cityId/payment-capability-versions")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    override suspend fun transitionCapability(
        accessToken: String,
        record: PaymentCapabilityRecord,
        target: String,
        reason: String,
    ): PaymentCapabilityRecord = client.post(
        endpoints.url("operations/payment-capability-versions/${record.id}/${paymentCapabilityAction(target)}")
    ) {
        authorize(accessToken)
        contentType(ContentType.Application.Json)
        setBody(PaymentCapabilityCommandRequest(record.optimisticVersion, reason))
    }.decode()

    override suspend fun verifyTransfer(
        accessToken: String,
        paymentId: String,
        idempotencyKey: String,
        settlementReference: String,
    ): ManualTransferReconciliationRecord = client.post(
        endpoints.url("operations/payments/$paymentId/manual-transfer/verify")
    ) {
        authorizeCommand(accessToken, idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(ManualTransferVerifyRequest(settlementReference))
    }.decode()

    override suspend fun rejectTransfer(
        accessToken: String,
        paymentId: String,
        idempotencyKey: String,
        reason: String,
    ): ManualTransferReconciliationRecord = client.post(
        endpoints.url("operations/payments/$paymentId/manual-transfer/reject")
    ) {
        authorizeCommand(accessToken, idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(ManualTransferRejectRequest(reason))
    }.decode()

    override suspend fun recordRefund(
        accessToken: String,
        paymentId: String,
        idempotencyKey: String,
        request: PaymentRefundCreateRequest,
    ): PaymentRefundRecord = client.post(endpoints.url("operations/payments/$paymentId/refunds")) {
        authorizeCommand(accessToken, idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    private suspend inline fun <reified T> getPage(
        accessToken: String,
        path: String,
        operatorId: String?,
    ): PagedResponse<T> = client.get(endpoints.url(path)) {
        authorize(accessToken)
        operatorId?.let { parameter("operator_id", it) }
        parameter("page", 1)
        parameter("limit", 100)
    }.decode()

    private fun paymentRecipientAction(target: String): String = when (target) {
        "verify" -> "verify"
        "retire" -> "retire"
        else -> error("Unsupported payment-recipient command $target")
    }

    private fun paymentCapabilityAction(target: String): String = when (target) {
        "submit" -> "submit"
        "approve" -> "approve"
        "activate" -> "activate"
        else -> error("Unsupported payment-capability command $target")
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorize(accessToken: String) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
    }

    private fun io.ktor.client.request.HttpRequestBuilder.authorizeCommand(
        accessToken: String,
        idempotencyKey: String,
    ) {
        authorize(accessToken)
        header("Idempotency-Key", idempotencyKey)
    }

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) {
            throw OperationsApiException(status.value, detail(body).ifBlank { "Request failed (${status.value})." })
        }
        return json.decodeFromString(body)
    }

    private fun detail(body: String): String = runCatching {
        val element = json.parseToJsonElement(body)
        when (element) {
            is JsonObject -> detailValue(element["detail"])
            else -> body
        }
    }.getOrDefault(body)

    private fun detailValue(value: JsonElement?): String = when (value) {
        is JsonPrimitive -> value.contentOrNull.orEmpty()
        is JsonArray -> value.joinToString("; ") { item ->
            val objectValue = item as? JsonObject
            objectValue?.get("msg")?.let(::detailValue).orEmpty()
        }
        is JsonObject -> value["msg"]?.let(::detailValue).orEmpty().ifBlank { value.toString() }
        null -> ""
    }
}
