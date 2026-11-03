package org.example.taximobile.operations.ui

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import org.example.taximobile.operations.model.PUBLIC_ACTIVATION_READINESS_GATES
import org.example.taximobile.operations.model.POST_LAUNCH_REVIEW_GATE

class OperationsComponentsTest {
    @Test
    fun bookingLabelsDoNotPromiseAssignmentOrInventUnknownRefundTerms() {
        listOf("SCHEDULED", "OFFERING", "DRIVER_COMMITTED", "DISPATCH_HANDOFF", "LIVE_RIDE_CREATED",
            "UNFULFILLED", "CANCELLED", "NO_CHARGE", "SURCHARGE_RETAINED", "REFUND_PENDING", "REFUNDED")
            .forEach { assertNotNull(bookingCodeResource(it), it) }
        assertNotEquals(bookingCodeResource("OFFERING"), bookingCodeResource("LIVE_RIDE_CREATED"))
        assertNotEquals(bookingCodeResource("DRIVER_COMMITTED"), bookingCodeResource("LIVE_RIDE_CREATED"))
        assertNotEquals(bookingCodeResource("REFUND_PENDING"), bookingCodeResource("REFUNDED"))
        listOf("ALWAYS_FULL", "FULL_BEFORE_CUTOFF", "NON_REFUNDABLE")
            .forEach { assertNotNull(bookingRefundCodeResource(it), it) }
        assertNull(bookingRefundCodeResource("FUTURE_POLICY"))
        assertNull(bookingRefundCodeResource("non_refundable"))
        assertNull(bookingCodeResource("FUTURE_STATUS"))
    }

    @Test
    fun caseLabelsCoverControlledChoicesWithoutConflatingNotesOrResponseState() {
        listOf("SUPPORT", "SAFETY", "OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED", "SUBMITTED",
            "ACKNOWLEDGED", "ESCALATED", "LOW", "NORMAL", "HIGH", "URGENT", "INTERNAL", "PARTICIPANT",
            "RIDE_PROBLEM", "FARE_DISPUTE", "ACCOUNT_ACCESS", "OTHER", "IMMEDIATE_DANGER", "HARASSMENT",
            "ASSAULT", "UNSAFE_DRIVING", "DISCRIMINATION", "VEHICLE_SAFETY", "OTHER_SAFETY",
            "INFORMATION_PROVIDED", "ACTION_TAKEN", "REFUND_RECORDED", "DUPLICATE", "OUT_OF_SCOPE", "NO_ACTION",
            "SAFETY_ACTION_TAKEN", "REFERRED_TO_AUTHORITIES", "NO_PLATFORM_ACTION", "LITIGATION",
            "REGULATORY_REQUEST", "LAW_ENFORCEMENT_REQUEST", "DISPUTE_PRESERVATION", "OTHER_LEGAL_OBLIGATION",
            "OBLIGATION_ENDED", "REQUEST_WITHDRAWN", "SUPERSEDED", "PLACED_IN_ERROR", "ACTIVE", "RELEASED",
            "ERASED", "PERSONAL_DATA_ERASED").forEach { assertNotNull(caseCodeResource(it), it) }
        assertNotEquals(caseCodeResource("INTERNAL"), caseCodeResource("PARTICIPANT"))
        assertNotEquals(caseCodeResource("ACKNOWLEDGED"), caseCodeResource("RESOLVED"))
        assertNotEquals(caseCodeResource("LOW"), caseCodeResource("URGENT"))
        assertNotEquals(caseCodeResource("ACTIVE"), caseCodeResource("RELEASED"))
        assertNull(caseCodeResource("FUTURE_CASE_STATE"))
        assertNull(caseCodeResource("resolved"))
    }

    @Test
    fun paymentLabelsKeepClaimsAndRefundsDistinctFromCompletedPayments() {
        listOf("CASH", "MANUAL_TRANSFER", "EXTERNAL_TRANSFER", "PENDING", "PROCESSING",
            "COMPLETED", "FAILED", "CANCELLED", "DISPUTED", "REFUNDED", "RETIRED",
            "DRAFT", "IN_REVIEW", "APPROVED", "ACTIVE", "VERIFIED", "submit", "approve", "activate")
            .forEach { assertNotNull(paymentCodeResource(it), it) }
        assertNotEquals(paymentCodeResource("PROCESSING"), paymentCodeResource("COMPLETED"))
        assertNotEquals(paymentCodeResource("PENDING"), paymentCodeResource("COMPLETED"))
        assertNotEquals(paymentCodeResource("REFUNDED"), paymentCodeResource("COMPLETED"))
        assertNull(paymentCodeResource("FUTURE_STATUS"))
        assertNull(paymentCodeResource("verified"))
    }

    @Test
    fun readinessLabelsCoverTheRecordedGateContractWithoutGuessingFutureOutcomes() {
        (PUBLIC_ACTIVATION_READINESS_GATES + POST_LAUNCH_REVIEW_GATE).forEach { code ->
            assertNotNull(rolloutCodeResource(code), code)
        }
        listOf("DRAFT", "CONFIGURING", "PILOT", "ACTIVE", "PAUSED", "RETIRED", "PENDING", "PASSED", "FAILED")
            .forEach { assertNotNull(rolloutCodeResource(it), it) }
        assertNotEquals(rolloutCodeResource("PENDING"), rolloutCodeResource("PASSED"))
        assertNotEquals(rolloutCodeResource("FAILED"), rolloutCodeResource("PASSED"))
        assertNull(rolloutCodeResource("FUTURE_CHECK"))
        assertNull(rolloutCodeResource("passed"))
    }

    @Test
    fun compactTimestampPreservesSecondsAndMarksUtc() {
        assertEquals("2026-08-24 13:14:15 UTC", compactTimestamp("2026-08-24T13:14:15.987654Z"))
        assertEquals("2026-08-24 13:14:15 UTC", compactTimestamp("2026-08-24T13:14:15+00:00"))
    }

    @Test
    fun compactTimestampHandlesMissingAndOffsetValues() {
        assertEquals("—", compactTimestamp(null))
        assertEquals("2026-08-24 13:14:15 +01:00", compactTimestamp("2026-08-24T13:14:15+01:00"))
        assertEquals("2026-08-24 13:14:15 -01:00", compactTimestamp("2026-08-24T13:14:15-01:00"))
    }
}
