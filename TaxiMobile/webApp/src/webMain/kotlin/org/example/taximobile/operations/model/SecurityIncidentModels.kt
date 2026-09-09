package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlin.time.Instant

const val MANAGE_SECURITY_INCIDENTS = "manage_security_incidents"

enum class SecurityIncidentSeverity(val label: String) {
    SEV1("SEV1 · critical"),
    SEV2("SEV2 · high"),
    SEV3("SEV3 · moderate"),
    SEV4("SEV4 · low"),
}

enum class SecurityIncidentCategory(val label: String) {
    ACCOUNT_COMPROMISE("Account compromise"),
    PROVIDER_CREDENTIAL_EXPOSURE("Provider credential exposure"),
    DATA_EXPOSURE("Data exposure"),
    MALICIOUS_ACCESS("Malicious access"),
    SERVICE_ABUSE("Service abuse"),
    OTHER("Other reviewed security event"),
}

enum class SecurityIncidentTimelineKind(val label: String) {
    EVIDENCE_LINKED("Evidence linked"),
    CONTAINMENT_ACTION("Containment action"),
    COMMUNICATION_DECISION("Communication decision"),
    RECOVERY_ACTION("Recovery action"),
    POSTMORTEM_ACTION("Postmortem action"),
}

enum class SecurityIncidentPostmortemOutcome(val label: String) {
    CONTROL_CHANGED("Control changed"),
    FOLLOW_UP_REQUIRED("Follow-up required"),
    NO_FURTHER_ACTION("No further action"),
}

enum class SecurityIncidentResponsibility(val label: String) {
    SECURITY_RESPONSE_LEAD("Security response lead"),
    COMMUNICATIONS_LEAD("Communications lead"),
    OPERATIONS_LIAISON("Operations liaison"),
    POSTMORTEM_OWNER("Postmortem owner"),
}

enum class SecurityIncidentTransition(
    val label: String,
    val sourceStatus: String,
    val targetStatus: String,
    val confirmationPhrase: String,
) {
    START_CONTAINMENT("Start containment", "OPEN", "CONTAINING", "START CONTAINMENT"),
    MARK_CONTAINED("Mark contained", "CONTAINING", "CONTAINED", "MARK CONTAINED"),
    START_RECOVERY("Start recovery", "CONTAINED", "RECOVERING", "START RECOVERY"),
    MARK_RECOVERED("Mark recovered", "RECOVERING", "RECOVERED", "MARK RECOVERED"),
    CLOSE("Close incident", "RECOVERED", "CLOSED", "CLOSE INCIDENT"),
}

@Serializable
data class SecurityIncidentRecord(
    val id: String,
    val reference: String,
    @SerialName("market_id") val marketId: String,
    @SerialName("city_id") val cityId: String? = null,
    val severity: String,
    val category: String,
    val status: String,
    val summary: String,
    @SerialName("reported_by_user_id") val reportedByUserId: String,
    @SerialName("lead_user_id") val leadUserId: String,
    @SerialName("detected_at") val detectedAt: String,
    @SerialName("opened_at") val openedAt: String,
    @SerialName("containment_due_at") val containmentDueAt: String,
    @SerialName("contained_at") val containedAt: String? = null,
    @SerialName("recovered_at") val recoveredAt: String? = null,
    @SerialName("closed_at") val closedAt: String? = null,
    @SerialName("postmortem_due_at") val postmortemDueAt: String? = null,
    @SerialName("postmortem_completed_at") val postmortemCompletedAt: String? = null,
    @SerialName("postmortem_completed_by_user_id") val postmortemCompletedByUserId: String? = null,
    @SerialName("postmortem_outcome") val postmortemOutcome: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
)

@Serializable
data class SecurityIncidentTimelineRecord(
    val id: String,
    @SerialName("incident_id") val incidentId: String,
    val sequence: Int,
    val kind: String,
    @SerialName("actor_user_id") val actorUserId: String,
    @SerialName("occurred_at") val occurredAt: String,
    @SerialName("recorded_at") val recordedAt: String,
    val summary: String,
    @SerialName("audit_log_id") val auditLogId: String? = null,
    @SerialName("external_reference") val externalReference: String? = null,
)

@Serializable
data class SecurityIncidentResponsibilityRecord(
    val id: String,
    @SerialName("incident_id") val incidentId: String,
    val responsibility: String,
    @SerialName("assigned_user_id") val assignedUserId: String,
    @SerialName("assigned_by_user_id") val assignedByUserId: String,
    @SerialName("assignment_reference") val assignmentReference: String,
    @SerialName("assigned_at") val assignedAt: String,
    @SerialName("released_at") val releasedAt: String? = null,
    @SerialName("released_by_user_id") val releasedByUserId: String? = null,
    @SerialName("release_reference") val releaseReference: String? = null,
    @SerialName("incident_version") val incidentVersion: Int,
)

data class SecurityIncidentWorkspace(
    val incidents: PagedResponse<SecurityIncidentRecord>,
)

@Serializable
data class SecurityIncidentCreateRequest(
    @SerialName("market_id") val marketId: String,
    @SerialName("city_id") val cityId: String? = null,
    val severity: String,
    val category: String,
    val summary: String,
    @SerialName("detected_at") val detectedAt: String,
    @SerialName("containment_due_at") val containmentDueAt: String,
)

@Serializable
data class SecurityIncidentTimelineCreateRequest(
    val kind: String,
    val summary: String,
    @SerialName("occurred_at") val occurredAt: String,
    @SerialName("audit_log_id") val auditLogId: String? = null,
    @SerialName("external_reference") val externalReference: String? = null,
)

@Serializable
data class SecurityIncidentTransitionRequest(
    val transition: String,
    @SerialName("expected_version") val expectedVersion: Int,
    val summary: String,
    @SerialName("occurred_at") val occurredAt: String,
    @SerialName("postmortem_due_at") val postmortemDueAt: String? = null,
)

@Serializable
data class SecurityIncidentPostmortemCompleteRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val outcome: String,
    val summary: String,
    @SerialName("occurred_at") val occurredAt: String,
    @SerialName("audit_log_id") val auditLogId: String? = null,
    @SerialName("external_reference") val externalReference: String? = null,
)

@Serializable
data class SecurityIncidentResponsibilityAssignRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    @SerialName("assigned_user_id") val assignedUserId: String,
    @SerialName("occurred_at") val occurredAt: String,
    @SerialName("external_reference") val externalReference: String,
)

private val incidentUuidPattern = Regex(
    "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
private val incidentReferencePattern = Regex("^[A-Za-z0-9][A-Za-z0-9._:/-]{2,159}$")

fun securityIncidentCreateInputError(
    marketId: String?,
    summary: String,
    detectedAt: String,
    containmentDueAt: String,
): String? {
    if (marketId.isNullOrBlank()) return "Select one authorized market."
    if (summary.trim().length !in 10..500) return "Enter a summary between 10 and 500 characters."
    val detected = runCatching { Instant.parse(detectedAt.trim()) }.getOrNull()
        ?: return "Enter a timezone-aware ISO detection timestamp."
    val due = runCatching { Instant.parse(containmentDueAt.trim()) }.getOrNull()
        ?: return "Enter a timezone-aware ISO containment deadline."
    if (due <= detected) return "Containment deadline must be after detection."
    return null
}

fun securityIncidentTimelineInputError(
    incident: SecurityIncidentRecord?,
    summary: String,
    occurredAt: String,
    auditLogId: String,
    externalReference: String,
    confirmation: String,
): String? = when {
    incident == null -> "Select an incident before appending a timeline fact."
    summary.trim().length !in 10..500 -> "Enter a timeline summary between 10 and 500 characters."
    runCatching { Instant.parse(occurredAt.trim()) }.isFailure ->
        "Enter a timezone-aware ISO occurrence timestamp."
    auditLogId.isBlank() && externalReference.isBlank() ->
        "Link a scoped audit UUID or an approved external runbook reference."
    auditLogId.isNotBlank() && !incidentUuidPattern.matches(auditLogId.trim()) ->
        "The audit link must be an exact UUID."
    externalReference.isNotBlank() && !incidentReferencePattern.matches(externalReference.trim()) ->
        "The external reference may use only letters, digits, dot, underscore, colon, slash, or hyphen."
    confirmation.trim().uppercase() != "APPEND" -> "Type APPEND to add an immutable timeline fact."
    else -> null
}

fun securityIncidentTransitionFor(status: String): SecurityIncidentTransition? =
    SecurityIncidentTransition.entries.firstOrNull { it.sourceStatus == status }

fun securityIncidentTransitionInputError(
    incident: SecurityIncidentRecord?,
    transition: SecurityIncidentTransition?,
    summary: String,
    occurredAt: String,
    postmortemDueAt: String,
    confirmation: String,
): String? = when {
    incident == null || transition == null || transition.sourceStatus != incident.status ->
        "Reload the incident before choosing its next lifecycle action."
    summary.trim().length !in 10..500 -> "Enter an action summary between 10 and 500 characters."
    runCatching { Instant.parse(occurredAt.trim()) }.isFailure ->
        "Enter a timezone-aware ISO occurrence timestamp."
    transition == SecurityIncidentTransition.CLOSE &&
        runCatching { Instant.parse(postmortemDueAt.trim()) }.isFailure ->
        "Closing requires a timezone-aware ISO postmortem deadline."
    transition != SecurityIncidentTransition.CLOSE && postmortemDueAt.isNotBlank() ->
        "A postmortem deadline is accepted only when closing."
    confirmation.trim().uppercase() != transition.confirmationPhrase ->
        "Type ${transition.confirmationPhrase} to confirm this transition."
    else -> null
}

fun securityIncidentPostmortemInputError(
    incident: SecurityIncidentRecord?,
    outcome: SecurityIncidentPostmortemOutcome,
    summary: String,
    occurredAt: String,
    auditLogId: String,
    externalReference: String,
    confirmation: String,
): String? {
    if (incident == null || incident.status != "CLOSED") {
        return "Close the incident before completing its postmortem."
    }
    if (incident.postmortemCompletedAt != null) {
        return "This postmortem is already complete. Append a correction to the timeline instead."
    }
    if (summary.trim().length !in 10..500) {
        return "Enter a postmortem summary between 10 and 500 characters."
    }
    val occurred = runCatching { Instant.parse(occurredAt.trim()) }.getOrNull()
        ?: return "Enter a timezone-aware ISO completion timestamp."
    val closed = incident.closedAt?.let { runCatching { Instant.parse(it) }.getOrNull() }
        ?: return "Reload the authoritative closure timestamp."
    if (occurred < closed) return "Postmortem completion cannot precede incident closure."
    if (auditLogId.isBlank() && externalReference.isBlank()) {
        return "Link a scoped audit UUID or an approved postmortem/follow-up reference."
    }
    if (auditLogId.isNotBlank() && !incidentUuidPattern.matches(auditLogId.trim())) {
        return "The audit link must be an exact UUID."
    }
    if (externalReference.isNotBlank() && !incidentReferencePattern.matches(externalReference.trim())) {
        return "The external reference may use only letters, digits, dot, underscore, colon, slash, or hyphen."
    }
    if (outcome == SecurityIncidentPostmortemOutcome.FOLLOW_UP_REQUIRED && externalReference.isBlank()) {
        return "Follow-up required must link the approved external work reference."
    }
    if (confirmation.trim().uppercase() != "COMPLETE POSTMORTEM") {
        return "Type COMPLETE POSTMORTEM to record the one-time completion."
    }
    return null
}

fun securityIncidentResponsibilityInputError(
    incident: SecurityIncidentRecord?,
    assignedUserId: String,
    occurredAt: String,
    externalReference: String,
    confirmation: String,
): String? {
    if (incident == null) return "Select an incident before assigning responsibility."
    if (incident.postmortemCompletedAt != null) {
        return "Completed incidents cannot receive new responsibility assignments."
    }
    if (!incidentUuidPattern.matches(assignedUserId.trim())) {
        return "Enter the exact approved responder UUID."
    }
    val occurred = runCatching { Instant.parse(occurredAt.trim()) }.getOrNull()
        ?: return "Enter a timezone-aware ISO assignment timestamp."
    val opened = runCatching { Instant.parse(incident.openedAt) }.getOrNull()
        ?: return "Reload the authoritative incident opening timestamp."
    if (occurred < opened) return "Assignment cannot precede incident opening."
    if (!incidentReferencePattern.matches(externalReference.trim())) {
        return "Link an approved roster, shift, or incident-command reference."
    }
    if (confirmation.trim().uppercase() != "ASSIGN RESPONSIBILITY") {
        return "Type ASSIGN RESPONSIBILITY to replace the active assignment."
    }
    return null
}
