package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlin.time.Instant

enum class AdministrativeGrantScopeKind(val displayName: String) {
    MARKET("Market"),
    OPERATOR("Operator"),
    CITY("City"),
}

data class AdministrativeRoleTemplateOption(
    val value: String,
    val displayName: String,
    val scopeKind: AdministrativeGrantScopeKind,
)

/**
 * Closed mirror of the server-owned administrative role templates.
 *
 * The browser uses this list only to construct valid requests. Permissions are
 * never inferred from it; the operations session and backend remain the sole
 * authorization authorities.
 */
val ADMINISTRATIVE_ROLE_TEMPLATES = listOf(
    AdministrativeRoleTemplateOption("PLATFORM_ADMIN", "Platform admin", AdministrativeGrantScopeKind.MARKET),
    AdministrativeRoleTemplateOption("OPERATOR_ADMIN", "Operator admin", AdministrativeGrantScopeKind.OPERATOR),
    AdministrativeRoleTemplateOption("CITY_MANAGER", "City manager", AdministrativeGrantScopeKind.CITY),
    AdministrativeRoleTemplateOption("DRIVER_REVIEWER", "Driver reviewer", AdministrativeGrantScopeKind.CITY),
    AdministrativeRoleTemplateOption("PRICING_MANAGER", "Pricing manager", AdministrativeGrantScopeKind.CITY),
    AdministrativeRoleTemplateOption("PAYMENT_RECONCILER", "Payment reconciler", AdministrativeGrantScopeKind.CITY),
    AdministrativeRoleTemplateOption("SUPPORT_AGENT", "Support agent", AdministrativeGrantScopeKind.CITY),
    AdministrativeRoleTemplateOption("SAFETY_RESPONDER", "Safety responder", AdministrativeGrantScopeKind.CITY),
    AdministrativeRoleTemplateOption("ANALYST", "Analyst", AdministrativeGrantScopeKind.CITY),
)

@Serializable
data class AdministrativeGrantCreateRequest(
    @SerialName("user_id") val userId: String,
    @SerialName("role_template") val roleTemplate: String,
    @SerialName("market_id") val marketId: String? = null,
    @SerialName("operator_id") val operatorId: String? = null,
    @SerialName("city_id") val cityId: String? = null,
    @SerialName("expires_at") val expiresAt: String? = null,
    val reason: String,
)

@Serializable
data class AdministrativeGrantRevocationRequest(
    @SerialName("grant_id") val grantId: String,
    val reason: String,
)

@Serializable
data class AdministrativeGrantDecisionRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

@Serializable
data class AdministrativeGrantChangeRequestRecord(
    val id: String,
    val action: String,
    val status: String,
    @SerialName("requester_user_id") val requesterUserId: String,
    @SerialName("decided_by_user_id") val decidedByUserId: String? = null,
    @SerialName("target_user_id") val targetUserId: String,
    @SerialName("role_template") val roleTemplate: String,
    @SerialName("market_id") val marketId: String? = null,
    @SerialName("operator_id") val operatorId: String? = null,
    @SerialName("city_id") val cityId: String? = null,
    @SerialName("source_grant_id") val sourceGrantId: String? = null,
    @SerialName("resulting_grant_id") val resultingGrantId: String? = null,
    val reason: String,
    @SerialName("decision_reason") val decisionReason: String? = null,
    @SerialName("requested_grant_expires_at") val requestedGrantExpiresAt: String? = null,
    @SerialName("requested_at") val requestedAt: String,
    @SerialName("decided_at") val decidedAt: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
)

fun administrativeRoleTemplate(value: String): AdministrativeRoleTemplateOption? =
    ADMINISTRATIVE_ROLE_TEMPLATES.firstOrNull { it.value == value }

fun AdministrativeGrantCreateRequest.scopeKind(): AdministrativeGrantScopeKind? =
    administrativeRoleTemplate(roleTemplate)?.scopeKind

fun AdministrativeGrantCreateRequest.scopeId(): String? = when (scopeKind()) {
    AdministrativeGrantScopeKind.MARKET -> marketId
    AdministrativeGrantScopeKind.OPERATOR -> operatorId
    AdministrativeGrantScopeKind.CITY -> cityId
    null -> null
}

fun AdministrativeGrantCreateRequest.matchesSelectedScope(scope: OperationsScope): Boolean =
    when (scopeKind()) {
        AdministrativeGrantScopeKind.MARKET -> marketId != null && marketId == scope.marketId
        AdministrativeGrantScopeKind.OPERATOR -> operatorId != null && operatorId == scope.operatorId
        AdministrativeGrantScopeKind.CITY -> cityId != null && cityId == scope.cityId
        null -> false
    }

fun administrativeGrantDecisionError(
    request: AdministrativeGrantChangeRequestRecord,
    currentUserId: String,
    decision: String,
    reason: String,
): String? {
    if (request.status != "PENDING") return "Refresh and select a pending request."
    if (decision !in setOf("approve", "reject", "cancel")) {
        return "Choose approve, reject, or cancel."
    }
    val isRequester = request.requesterUserId.equals(currentUserId, ignoreCase = true)
    val isTarget = request.targetUserId.equals(currentUserId, ignoreCase = true)
    if (decision == "cancel" && !isRequester) {
        return "Only the original requester may cancel this request."
    }
    if (decision != "cancel" && (isRequester || isTarget)) {
        return "Requester, target, and deciding administrator must be different accounts."
    }
    if (reason.trim().length !in 3..240) {
        return "Enter an audit reason between 3 and 240 characters."
    }
    return null
}

/** Returns the first actionable problem without implying authorization. */
fun administrativeGrantInputError(
    request: AdministrativeGrantCreateRequest,
    currentUserId: String,
    now: Instant,
): String? {
    val role = administrativeRoleTemplate(request.roleTemplate)
        ?: return "Choose one supported administrative role template."
    if (!uuidPattern.matches(request.userId.trim())) {
        return "Enter the exact target user UUID from an approved staff record."
    }
    if (request.userId.trim().equals(currentUserId.trim(), ignoreCase = true)) {
        return "You cannot create or extend a grant for your own account."
    }
    val suppliedScopes = listOfNotNull(request.marketId, request.operatorId, request.cityId)
    if (suppliedScopes.size != 1 || request.scopeId().isNullOrBlank()) {
        return "${role.displayName} requires exactly one ${role.scopeKind.displayName.lowercase()} scope."
    }
    if (!uuidPattern.matches(request.scopeId()!!)) {
        return "Select a valid ${role.scopeKind.displayName.lowercase()} scope."
    }
    if (request.reason.trim().length !in 3..240) {
        return "Enter an audit reason between 3 and 240 characters."
    }
    request.expiresAt?.let { expiresAt ->
        if (!validZonedTimestamp(expiresAt)) {
            return "Expiry must be an ISO 8601 timestamp with Z or an explicit offset."
        }
        val expiry = runCatching { Instant.parse(normalizeAdministrativeInstant(expiresAt)) }.getOrNull()
            ?: return "Expiry must be a valid calendar timestamp."
        if (expiry <= now) return "Expiry must be in the future."
    }
    return null
}

private val uuidPattern =
    Regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")

private fun normalizeAdministrativeInstant(value: String): String {
    val normalized = value.trim()
    return if (Regex("T\\d{2}:\\d{2}(Z|[+-]\\d{2}:\\d{2})$").containsMatchIn(normalized)) {
        normalized.replace(Regex("(Z|[+-]\\d{2}:\\d{2})$")) { match -> ":00${match.value}" }
    } else normalized
}
