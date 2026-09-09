package org.example.taximobile.operations.data

import io.ktor.client.HttpClient
import io.ktor.client.request.header
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
import org.example.taximobile.operations.model.AccountSecurityAction
import org.example.taximobile.operations.model.AccountSecurityActionRequest
import org.example.taximobile.operations.model.AccountSecurityActionResponse

interface AccountSecurityGateway {
    suspend fun apply(
        accessToken: String,
        marketId: String,
        targetUserId: String,
        action: AccountSecurityAction,
        idempotencyKey: String,
        request: AccountSecurityActionRequest,
    ): AccountSecurityActionResponse
}

class KtorAccountSecurityGateway(
    private val client: HttpClient,
    apiBaseUrl: String,
) : AccountSecurityGateway {
    private val endpoints = OperationsApiEndpoints(apiBaseUrl)
    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    override suspend fun apply(
        accessToken: String,
        marketId: String,
        targetUserId: String,
        action: AccountSecurityAction,
        idempotencyKey: String,
        request: AccountSecurityActionRequest,
    ): AccountSecurityActionResponse = client.post(
        endpoints.url("operations/markets/$marketId/users/$targetUserId/${action.pathSegment}")
    ) {
        header(HttpHeaders.Authorization, "Bearer $accessToken")
        header("Idempotency-Key", idempotencyKey)
        contentType(ContentType.Application.Json)
        setBody(request)
    }.decode()

    private suspend inline fun <reified T> HttpResponse.decode(): T {
        val body = bodyAsText()
        if (!status.isSuccess()) {
            throw OperationsApiException(status.value, errorDetail(body, status.value))
        }
        return try {
            json.decodeFromString<T>(body)
        } catch (_: Throwable) {
            throw OperationsApiException(status.value, "The account-security API returned an unreadable response.")
        }
    }

    private fun errorDetail(body: String, statusCode: Int): String = runCatching {
        val root = json.parseToJsonElement(body).jsonObject
        val detail = root["detail"] ?: root["error"]?.jsonObject?.get("message")
        detail?.jsonPrimitive?.contentOrNull
    }.getOrNull() ?: "Account-security request failed ($statusCode)."
}
