package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

const val MANAGE_ACCOUNT_SECURITY = "manage_account_security"

enum class AccountSecurityAction(
    val pathSegment: String,
    val label: String,
    val confirmationPhrase: String,
) {
    REVOKE_SESSIONS("sessions/revoke", "Revoke all sessions", "REVOKE"),
    SUSPEND("suspend", "Suspend account", "SUSPEND"),
    REACTIVATE("reactivate", "Reactivate account", "REACTIVATE"),
}

val ACCOUNT_SECURITY_REASON_CODES = listOf(
    "ACCOUNT_COMPROMISE",
    "VERIFIED_USER_REQUEST",
    "SAFETY_CONTAINMENT",
    "LEGAL_REQUIREMENT",
    "SECURITY_INCIDENT",
)

@Serializable
data class AccountSecurityActionRequest(
    @SerialName("reason_code") val reasonCode: String,
    @SerialName("case_reference") val caseReference: String,
)

@Serializable
data class AccountSecurityActionResponse(
    @SerialName("user_id") val userId: String,
    val status: String,
    @SerialName("sessions_revoked") val sessionsRevoked: Int,
    @SerialName("device_registrations_revoked") val deviceRegistrationsRevoked: Int,
    @SerialName("changed_at") val changedAt: String,
)

private val uuidPattern = Regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
private val caseReferencePattern = Regex("^(SUP|SAF|SEC)-[A-Z0-9][A-Z0-9-]{2,67}$")

fun accountSecurityInputError(
    marketId: String?,
    targetUserId: String,
    action: AccountSecurityAction,
    reasonCode: String,
    caseReference: String,
    confirmation: String,
): String? = when {
    marketId.isNullOrBlank() -> "Select the market associated with the reviewed case."
    !uuidPattern.matches(targetUserId.trim()) -> "Enter the exact target user UUID from an authorized case record."
    reasonCode !in ACCOUNT_SECURITY_REASON_CODES -> "Choose one controlled reason code."
    !caseReferencePattern.matches(caseReference.trim().uppercase()) ->
        "Use an approved SUP-, SAF-, or SEC- case reference."
    confirmation.trim().uppercase() != action.confirmationPhrase ->
        "Type ${action.confirmationPhrase} to confirm this account-wide action."
    else -> null
}
