package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

enum class CityAuthorizationAction(val label: String, val reasons: List<String>) {
    SUSPEND("Suspend", listOf("SAFETY_REVIEW", "ELIGIBILITY_REVIEW")),
    REVOKE("Revoke", listOf("OPERATING_PERMISSION_WITHDRAWN")),
    REINSTATE("Reinstate", listOf("ELIGIBILITY_REVIEW_PASSED")),
}

fun cityAuthorizationActions(status: String): List<CityAuthorizationAction> = when (status) {
    "ACTIVE" -> listOf(CityAuthorizationAction.SUSPEND, CityAuthorizationAction.REVOKE)
    "SUSPENDED" -> listOf(CityAuthorizationAction.REINSTATE, CityAuthorizationAction.REVOKE)
    "EXPIRED" -> listOf(CityAuthorizationAction.REVOKE)
    else -> emptyList()
}

@Serializable
data class CityAuthorizationDecisionRequest(
    @SerialName("expected_application_version") val expectedApplicationVersion: Int,
    val action: String,
    @SerialName("reason_code") val reasonCode: String,
)
