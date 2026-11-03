package org.example.taximobile.data.network

import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.contentOrNull

enum class ApiFailureReason { OPERATOR_MEMBERSHIP_REQUIRED }

/** A non-auth backend error safe to display after product-specific translation. */
class ApiRequestException(
    val statusCode: Int,
    message: String,
    val reason: ApiFailureReason? = null,
) : Exception(message)

/** Translate only a known, exact server rejection; never display arbitrary text. */
internal fun apiRequestFailure(statusCode: Int, fallback: String, responseBody: String): ApiRequestException {
    val membershipRequired = statusCode == 409 && responseBody.length <= 4096 && runCatching {
        val error = Json.parseToJsonElement(responseBody).jsonObject["error"]?.jsonObject
        error?.get("code")?.jsonPrimitive?.contentOrNull == "REQUEST_REJECTED" &&
            error?.get("message")?.jsonPrimitive?.contentOrNull == "Active membership with this operator is required."
    }.getOrDefault(false)
    return ApiRequestException(statusCode, fallback,
        if (membershipRequired) ApiFailureReason.OPERATOR_MEMBERSHIP_REQUIRED else null)
}

internal suspend fun HttpResponse.apiFailure(fallback: String): ApiRequestException =
    apiRequestFailure(status.value, fallback, bodyAsText())
