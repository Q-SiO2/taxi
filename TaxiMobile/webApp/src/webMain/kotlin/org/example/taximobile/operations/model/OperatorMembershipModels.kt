package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlin.time.Instant

internal val operatorMembershipWireJson = Json { explicitNulls = true; encodeDefaults = true }

@Serializable
data class OperatorMembershipRecord(
    val id: String,
    @SerialName("cooperative_id") val cooperativeId: String,
    @SerialName("driver_id") val driverId: String? = null,
    val status: String,
    @SerialName("membership_number") val membershipNumber: String? = null,
    @SerialName("joined_at") val joinedAt: String? = null,
    @SerialName("ended_at") val endedAt: String? = null,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class OperatorMembershipPage(
    @SerialName("operator_id") val operatorId: String,
    @SerialName("cooperative_id") val cooperativeId: String,
    @SerialName("cooperative_status") val cooperativeStatus: String,
    val items: List<OperatorMembershipRecord>,
    val page: Int,
    val limit: Int,
    val total: Int,
)

@Serializable
data class OperatorMembershipCreateRequest(
    @SerialName("driver_id") val driverId: String,
    val status: String,
    @SerialName("membership_number") val membershipNumber: String?,
    @SerialName("joined_at") val joinedAt: String?,
    @SerialName("ended_at") val endedAt: String?,
    val reason: String,
)

@Serializable
data class OperatorMembershipUpdateRequest(
    val status: String,
    @SerialName("membership_number") val membershipNumber: String?,
    @SerialName("joined_at") val joinedAt: String?,
    @SerialName("ended_at") val endedAt: String?,
    @SerialName("expected_updated_at") val expectedUpdatedAt: String,
    val reason: String,
)

@Serializable
data class OperatorMembershipPolicyRequest(
    @SerialName("requires_active_membership") val requiresActiveMembership: Boolean,
)

fun validMembershipDates(joinedAt: String, endedAt: String): Boolean = runCatching {
    val joined = joinedAt.trim().takeIf { it.isNotEmpty() }?.let { Instant.parse(it) }
    val ended = endedAt.trim().takeIf { it.isNotEmpty() }?.let { Instant.parse(it) }
    joined == null || ended == null || ended >= joined
}.getOrDefault(false)

fun validMembershipDriverId(value: String): Boolean =
    Regex("[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
        .matches(value.trim())
