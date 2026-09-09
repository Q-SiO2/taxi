package org.example.taximobile.operations.model

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class SecurityIncidentModelsTest {
    private val incident = SecurityIncidentRecord(
        id = "eef3fa3a-5740-4b47-a22b-b4638a0870fa",
        reference = "SEC-EEF3FA3A57404B47A22BB4638A0870FA",
        marketId = "7f5b1477-0773-4a3c-80ef-ae7a4db56fa7",
        severity = "SEV2",
        category = "ACCOUNT_COMPROMISE",
        status = "OPEN",
        summary = "Synthetic compromised account incident for a controlled exercise.",
        reportedByUserId = "eef3fa3a-5740-4b47-a22b-b4638a0870fa",
        leadUserId = "eef3fa3a-5740-4b47-a22b-b4638a0870fa",
        detectedAt = "2026-09-07T10:00:00Z",
        openedAt = "2026-09-07T10:01:00Z",
        containmentDueAt = "2026-09-07T12:00:00Z",
        optimisticVersion = 1,
    )

    @Test
    fun permission_exposes_only_the_security_incident_destination() {
        assertEquals(
            listOf(OperationsDestination.SECURITY_INCIDENTS),
            availableDestinations(setOf(MANAGE_SECURITY_INCIDENTS)),
        )
    }

    @Test
    fun lifecycle_exposes_only_the_next_forward_transition() {
        assertEquals(
            SecurityIncidentTransition.START_CONTAINMENT,
            securityIncidentTransitionFor("OPEN"),
        )
        assertEquals(SecurityIncidentTransition.CLOSE, securityIncidentTransitionFor("RECOVERED"))
        assertNull(securityIncidentTransitionFor("CLOSED"))
    }

    @Test
    fun creation_requires_scope_bounded_summary_and_ordered_iso_times() {
        assertNull(
            securityIncidentCreateInputError(
                marketId = incident.marketId,
                summary = incident.summary,
                detectedAt = incident.detectedAt,
                containmentDueAt = incident.containmentDueAt,
            )
        )
        assertTrue(
            securityIncidentCreateInputError(
                marketId = incident.marketId,
                summary = incident.summary,
                detectedAt = incident.containmentDueAt,
                containmentDueAt = incident.detectedAt,
            )!!.contains("after", ignoreCase = true)
        )
    }

    @Test
    fun timeline_requires_reference_and_destructive_confirmation() {
        assertNull(
            securityIncidentTimelineInputError(
                incident = incident,
                summary = "The synthetic account sessions were revoked through the audited command.",
                occurredAt = "2026-09-07T10:02:00Z",
                auditLogId = "eef3fa3a-5740-4b47-a22b-b4638a0870fa",
                externalReference = "",
                confirmation = "append",
            )
        )
        assertNotNull(
            securityIncidentTimelineInputError(
                incident = incident,
                summary = "The synthetic account sessions were revoked through the audited command.",
                occurredAt = "2026-09-07T10:02:00Z",
                auditLogId = "",
                externalReference = "",
                confirmation = "APPEND",
            )
        )
    }

    @Test
    fun transition_confirmation_and_response_decoding_preserve_version_authority() {
        val transition = SecurityIncidentTransition.START_CONTAINMENT
        assertNull(
            securityIncidentTransitionInputError(
                incident = incident,
                transition = transition,
                summary = "Containment started under the reviewed synthetic incident procedure.",
                occurredAt = "2026-09-07T10:03:00Z",
                postmortemDueAt = "",
                confirmation = transition.confirmationPhrase,
            )
        )
        assertNotNull(
            securityIncidentTransitionInputError(
                incident = incident.copy(status = "CONTAINED"),
                transition = transition,
                summary = "Containment started under the reviewed synthetic incident procedure.",
                occurredAt = "2026-09-07T10:03:00Z",
                postmortemDueAt = "",
                confirmation = transition.confirmationPhrase,
            )
        )

        val decoded = Json { ignoreUnknownKeys = true }.decodeFromString<SecurityIncidentRecord>(
            """{"id":"eef3fa3a-5740-4b47-a22b-b4638a0870fa","reference":"SEC-EEF3","market_id":"7f5b1477-0773-4a3c-80ef-ae7a4db56fa7","city_id":null,"severity":"SEV2","category":"ACCOUNT_COMPROMISE","status":"CONTAINING","summary":"Synthetic incident","reported_by_user_id":"eef3fa3a-5740-4b47-a22b-b4638a0870fa","lead_user_id":"eef3fa3a-5740-4b47-a22b-b4638a0870fa","detected_at":"2026-09-07T10:00:00Z","opened_at":"2026-09-07T10:01:00Z","containment_due_at":"2026-09-07T12:00:00Z","contained_at":null,"recovered_at":null,"closed_at":null,"postmortem_due_at":null,"optimistic_version":2}"""
        )
        assertEquals(2, decoded.optimisticVersion)
        assertEquals("CONTAINING", decoded.status)
    }

    @Test
    fun postmortem_completion_requires_closed_unfinished_state_and_linked_follow_up() {
        val closed = incident.copy(
            status = "CLOSED",
            closedAt = "2026-09-07T11:00:00Z",
            postmortemDueAt = "2026-09-14T11:00:00Z",
            optimisticVersion = 6,
        )
        assertNull(
            securityIncidentPostmortemInputError(
                incident = closed,
                outcome = SecurityIncidentPostmortemOutcome.FOLLOW_UP_REQUIRED,
                summary = "The exercise produced one approved follow-up remediation action.",
                occurredAt = "2026-09-07T12:00:00Z",
                auditLogId = "",
                externalReference = "POSTMORTEM-SEC-001",
                confirmation = "complete postmortem",
            )
        )
        assertNotNull(
            securityIncidentPostmortemInputError(
                incident = closed,
                outcome = SecurityIncidentPostmortemOutcome.FOLLOW_UP_REQUIRED,
                summary = "The exercise produced one approved follow-up remediation action.",
                occurredAt = "2026-09-07T12:00:00Z",
                auditLogId = "eef3fa3a-5740-4b47-a22b-b4638a0870fa",
                externalReference = "",
                confirmation = "COMPLETE POSTMORTEM",
            )
        )
        assertNotNull(
            securityIncidentPostmortemInputError(
                incident = closed.copy(
                    postmortemCompletedAt = "2026-09-07T12:00:00Z",
                    postmortemOutcome = "FOLLOW_UP_REQUIRED",
                ),
                outcome = SecurityIncidentPostmortemOutcome.FOLLOW_UP_REQUIRED,
                summary = "The exercise produced one approved follow-up remediation action.",
                occurredAt = "2026-09-07T12:00:00Z",
                auditLogId = "",
                externalReference = "POSTMORTEM-SEC-001",
                confirmation = "COMPLETE POSTMORTEM",
            )
        )
    }

    @Test
    fun responsibility_assignment_requires_exact_authority_inputs_and_decodes_history() {
        assertNull(
            securityIncidentResponsibilityInputError(
                incident = incident,
                assignedUserId = "7a5afc39-1f17-477f-80bc-542e7fa19cbd",
                occurredAt = "2026-09-07T10:02:00Z",
                externalReference = "ROSTER-CASABLANCA-2026-09-07-A",
                confirmation = "assign responsibility",
            )
        )
        assertNotNull(
            securityIncidentResponsibilityInputError(
                incident = incident,
                assignedUserId = "responder@example.invalid",
                occurredAt = "2026-09-07T10:02:00Z",
                externalReference = "ROSTER-CASABLANCA-2026-09-07-A",
                confirmation = "ASSIGN RESPONSIBILITY",
            )
        )
        assertNotNull(
            securityIncidentResponsibilityInputError(
                incident = incident.copy(postmortemCompletedAt = "2026-09-08T10:00:00Z"),
                assignedUserId = "7a5afc39-1f17-477f-80bc-542e7fa19cbd",
                occurredAt = "2026-09-07T10:02:00Z",
                externalReference = "ROSTER-CASABLANCA-2026-09-07-A",
                confirmation = "ASSIGN RESPONSIBILITY",
            )
        )

        val decoded = Json { ignoreUnknownKeys = true }
            .decodeFromString<SecurityIncidentResponsibilityRecord>(
                """{"id":"4c6c164e-fe8c-4a46-8702-c0b0b99b7be3","incident_id":"eef3fa3a-5740-4b47-a22b-b4638a0870fa","responsibility":"COMMUNICATIONS_LEAD","assigned_user_id":"7a5afc39-1f17-477f-80bc-542e7fa19cbd","assigned_by_user_id":"eef3fa3a-5740-4b47-a22b-b4638a0870fa","assignment_reference":"ROSTER-CASABLANCA-2026-09-07-A","assigned_at":"2026-09-07T10:02:00Z","released_at":null,"released_by_user_id":null,"release_reference":null,"incident_version":2}"""
            )
        assertEquals(SecurityIncidentResponsibility.COMMUNICATIONS_LEAD.name, decoded.responsibility)
        assertEquals(2, decoded.incidentVersion)
        assertNull(decoded.releasedAt)
    }
}
