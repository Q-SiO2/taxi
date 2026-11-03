package org.example.taximobile.domain.scheduling

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ScheduledCancellationTermsTest {
    @Test fun only_exact_supported_modes_and_contract_cutoffs_are_reviewable() {
        for (mode in listOf("ALWAYS_FULL", "FULL_BEFORE_CUTOFF", "NON_REFUNDABLE")) {
            for (cutoff in listOf(0, 60, 10080)) assertTrue(ScheduledCancellationTerms(cutoff, mode, "Untrusted summary").isSupportedForReview)
            for (cutoff in listOf(-1, 10081, Int.MIN_VALUE, Int.MAX_VALUE)) assertFalse(ScheduledCancellationTerms(cutoff, mode, "Refund guaranteed").isSupportedForReview)
        }
        for (mode in listOf("", "FULL", "always_full", "FUTURE_PRIVATE_POLICY", "NON_REFUNDABLE ")) {
            assertFalse(ScheduledCancellationTerms(60, mode, "Refund guaranteed").isSupportedForReview)
        }
    }
}
