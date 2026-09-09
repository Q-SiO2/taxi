package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

const val MANAGE_SUPPORT_CASES = "manage_support_cases"
const val MANAGE_SAFETY_CASES = "manage_safety_cases"
const val MANAGE_CASE_RETENTION = "manage_case_retention"

@Serializable
data class CaseNoteRecord(
    val id: String,
    @SerialName("author_user_id") val authorUserId: String,
    val visibility: String,
    val message: String,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class SupportCaseSummary(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("user_id") val userId: String,
    @SerialName("ride_id") val rideId: String? = null,
    val category: String,
    val subject: String,
    val status: String,
    val priority: String,
    @SerialName("assigned_to_user_id") val assignedToUserId: String? = null,
    @SerialName("response_due_at") val responseDueAt: String,
    @SerialName("first_responded_at") val firstRespondedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class SupportCaseDetail(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("user_id") val userId: String,
    @SerialName("ride_id") val rideId: String? = null,
    val category: String,
    val subject: String,
    val status: String,
    val priority: String,
    @SerialName("assigned_to_user_id") val assignedToUserId: String? = null,
    @SerialName("response_due_at") val responseDueAt: String,
    @SerialName("first_responded_at") val firstRespondedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    val description: String,
    @SerialName("resolution_code") val resolutionCode: String? = null,
    @SerialName("resolved_at") val resolvedAt: String? = null,
    @SerialName("closed_at") val closedAt: String? = null,
    @SerialName("retention_policy_version") val retentionPolicyVersion: String,
    @SerialName("retention_until") val retentionUntil: String? = null,
    val notes: List<CaseNoteRecord>,
)

@Serializable
data class SafetyCaseSummary(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("ride_id") val rideId: String,
    @SerialName("reporter_user_id") val reporterUserId: String,
    val category: String,
    val status: String,
    val priority: String,
    @SerialName("assigned_to_user_id") val assignedToUserId: String? = null,
    @SerialName("response_due_at") val responseDueAt: String,
    @SerialName("first_acknowledged_at") val firstAcknowledgedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
)

@Serializable
data class SafetyCaseDetail(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("ride_id") val rideId: String,
    @SerialName("reporter_user_id") val reporterUserId: String,
    val category: String,
    val status: String,
    val priority: String,
    @SerialName("assigned_to_user_id") val assignedToUserId: String? = null,
    @SerialName("response_due_at") val responseDueAt: String,
    @SerialName("first_acknowledged_at") val firstAcknowledgedAt: String? = null,
    @SerialName("created_at") val createdAt: String,
    @SerialName("updated_at") val updatedAt: String,
    @SerialName("reported_user_id") val reportedUserId: String? = null,
    @SerialName("source_support_ticket_id") val sourceSupportTicketId: String? = null,
    val description: String,
    @SerialName("escalated_at") val escalatedAt: String? = null,
    @SerialName("resolved_at") val resolvedAt: String? = null,
    @SerialName("closed_at") val closedAt: String? = null,
    @SerialName("resolution_code") val resolutionCode: String? = null,
    @SerialName("retention_policy_version") val retentionPolicyVersion: String,
    @SerialName("retention_until") val retentionUntil: String? = null,
    val notes: List<CaseNoteRecord>,
)

@Serializable
data class CaseAlertRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("case_type") val caseType: String,
    @SerialName("case_id") val caseId: String,
    val severity: String,
    val status: String,
    @SerialName("response_due_at") val responseDueAt: String,
    @SerialName("first_detected_at") val firstDetectedAt: String,
    @SerialName("last_evaluated_at") val lastEvaluatedAt: String,
    @SerialName("delivery_attempts") val deliveryAttempts: Int,
    @SerialName("next_delivery_at") val nextDeliveryAt: String? = null,
    @SerialName("last_delivered_at") val lastDeliveredAt: String? = null,
    @SerialName("acknowledged_at") val acknowledgedAt: String? = null,
    @SerialName("acknowledged_by_user_id") val acknowledgedByUserId: String? = null,
    @SerialName("resolved_at") val resolvedAt: String? = null,
)

data class CaseOperationsSnapshot(
    val supportCases: PagedResponse<SupportCaseSummary>? = null,
    val safetyCases: PagedResponse<SafetyCaseSummary>? = null,
    val alerts: PagedResponse<CaseAlertRecord>? = null,
    val legalHolds: PagedResponse<LegalHoldRecord>? = null,
    val retentionActions: PagedResponse<CaseRetentionActionRecord>? = null,
)

@Serializable
data class LegalHoldRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("case_kind") val caseKind: String,
    @SerialName("case_id") val caseId: String,
    val status: String,
    @SerialName("reason_code") val reasonCode: String,
    @SerialName("authority_reference") val authorityReference: String,
    @SerialName("placed_by_user_id") val placedByUserId: String,
    @SerialName("placed_at") val placedAt: String,
    @SerialName("review_due_at") val reviewDueAt: String,
    @SerialName("released_by_user_id") val releasedByUserId: String? = null,
    @SerialName("released_at") val releasedAt: String? = null,
    @SerialName("release_reason_code") val releaseReasonCode: String? = null,
)

@Serializable
data class CaseRetentionActionRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("case_kind") val caseKind: String,
    @SerialName("case_id") val caseId: String,
    val action: String,
    @SerialName("retention_policy_version") val retentionPolicyVersion: String,
    @SerialName("retention_due_at") val retentionDueAt: String,
    @SerialName("executed_at") val executedAt: String,
    @SerialName("erased_note_count") val erasedNoteCount: Int,
)

@Serializable
data class LegalHoldCreateCommand(
    @SerialName("case_kind") val caseKind: String,
    @SerialName("case_id") val caseId: String,
    @SerialName("reason_code") val reasonCode: String,
    @SerialName("authority_reference") val authorityReference: String,
    @SerialName("review_due_at") val reviewDueAt: String,
)

@Serializable
data class LegalHoldReleaseCommand(@SerialName("reason_code") val reasonCode: String)

@Serializable
data class SupportTriageCommand(
    val priority: String,
    @SerialName("assigned_to_user_id") val assignedToUserId: String? = null,
    @SerialName("participant_message") val participantMessage: String,
    @SerialName("internal_note") val internalNote: String,
)

@Serializable
data class SupportTransitionCommand(
    @SerialName("target_status") val targetStatus: String,
    @SerialName("resolution_code") val resolutionCode: String? = null,
    @SerialName("participant_message") val participantMessage: String? = null,
    @SerialName("internal_note") val internalNote: String,
)

@Serializable
data class SupportSafetyEscalationCommand(
    val category: String,
    @SerialName("internal_note") val internalNote: String,
)

@Serializable
data class SupportSafetyEscalationReceipt(
    @SerialName("safety_report_id") val safetyReportId: String,
    @SerialName("source_support_ticket_id") val sourceSupportTicketId: String,
    @SerialName("city_id") val cityId: String,
    val status: String,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class SafetyTransitionCommand(
    @SerialName("target_status") val targetStatus: String,
    @SerialName("assigned_to_user_id") val assignedToUserId: String? = null,
    @SerialName("resolution_code") val resolutionCode: String? = null,
    @SerialName("participant_message") val participantMessage: String,
    @SerialName("internal_note") val internalNote: String,
)

@Serializable
data class CaseAlertAcknowledgeCommand(val reason: String)

fun supportTransitionTargets(status: String): List<String> = when (status) {
    "IN_PROGRESS" -> listOf("RESOLVED")
    "RESOLVED" -> listOf("IN_PROGRESS", "CLOSED")
    else -> emptyList()
}

fun safetyTransitionTargets(status: String): List<String> = when (status) {
    "SUBMITTED" -> listOf("ACKNOWLEDGED")
    "ACKNOWLEDGED" -> listOf("ESCALATED", "RESOLVED")
    "ESCALATED" -> listOf("RESOLVED")
    "RESOLVED" -> listOf("ACKNOWLEDGED", "CLOSED")
    else -> emptyList()
}
