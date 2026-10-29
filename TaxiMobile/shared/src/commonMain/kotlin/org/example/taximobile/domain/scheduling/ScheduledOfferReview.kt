package org.example.taximobile.domain.scheduling

import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds
import kotlin.time.Instant

/** Advisory review only. The server alone decides expiry, conflicts and assignment. */
fun ScheduledOffer.responseSecondsRemaining(elapsed: Duration = readStartedAt.elapsedNow()): Int? = try {
    val initial = Instant.parse(expiresAt) - Instant.parse(serverTime)
    if (!elapsed.isFinite() || elapsed.isNegative() || initial > Int.MAX_VALUE.seconds) return null
    val remaining = initial - elapsed
    if (remaining <= Duration.ZERO) 0 else {
        val whole = remaining.inWholeSeconds
        (whole + if (remaining > whole.seconds) 1 else 0).toInt()
    }
} catch (_: IllegalArgumentException) {
    null
}

val ScheduledOffer.canReviewAcceptance: Boolean
    get() = id.isNotBlank() && status == "PENDING" &&
        serviceType in setOf("ON_DEMAND", "FIXED_ROUTE") &&
        scheduledCityTime(scheduledFor, cityTimezone) != null &&
        cancellationTerms.isSupportedForReview && (responseSecondsRemaining() ?: 0) > 0
