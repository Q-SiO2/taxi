package org.example.taximobile.operations.model

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse

class CaseOperationsModelsTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `case destinations require an explicit queue permission`() {
        assertEquals(
            listOf(OperationsDestination.CASE_OPERATIONS),
            availableDestinations(setOf(MANAGE_SUPPORT_CASES)),
        )
        assertEquals(
            listOf(OperationsDestination.CASE_OPERATIONS),
            availableDestinations(setOf(MANAGE_SAFETY_CASES)),
        )
    }

    @Test
    fun `support escalation receipt contains no restricted safety detail`() {
        val receipt = json.decodeFromString<SupportSafetyEscalationReceipt>(
            """{
              "safety_report_id":"report-1",
              "source_support_ticket_id":"ticket-1",
              "city_id":"city-1",
              "status":"SUBMITTED",
              "created_at":"2026-08-30T12:00:00Z",
              "reported_user_id":"must-be-ignored",
              "description":"must-be-ignored"
            }""",
        )

        assertEquals("report-1", receipt.safetyReportId)
        assertFalse(receipt.toString().contains("must-be-ignored"))
    }

    @Test
    fun `case state machines expose only documented next transitions`() {
        assertEquals(listOf("RESOLVED"), supportTransitionTargets("IN_PROGRESS"))
        assertEquals(listOf("IN_PROGRESS", "CLOSED"), supportTransitionTargets("RESOLVED"))
        assertEquals(listOf("ACKNOWLEDGED"), safetyTransitionTargets("SUBMITTED"))
        assertEquals(listOf("ESCALATED", "RESOLVED"), safetyTransitionTargets("ACKNOWLEDGED"))
        assertEquals(emptyList(), safetyTransitionTargets("CLOSED"))
    }

    @Test
    fun `legal hold response preserves controlled evidence without case text`() {
        val hold = json.decodeFromString<LegalHoldRecord>(
            """{
              "id":"hold-1","city_id":"city-1","case_kind":"SUPPORT","case_id":"ticket-1",
              "status":"ACTIVE","reason_code":"DISPUTE_PRESERVATION",
              "authority_reference":"LEGAL-2026-1","placed_by_user_id":"admin-1",
              "placed_at":"2026-08-30T12:00:00Z","review_due_at":"2026-09-30T12:00:00Z"
            }""",
        )

        assertEquals("LEGAL-2026-1", hold.authorityReference)
        assertEquals("SUPPORT", hold.caseKind)
    }
}
