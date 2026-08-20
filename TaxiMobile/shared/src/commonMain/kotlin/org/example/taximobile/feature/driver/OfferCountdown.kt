package org.example.taximobile.feature.driver

import kotlin.time.Instant
import org.example.taximobile.domain.drivers.DriverRideOffer

data class OfferCountdown(
    val remainingSeconds: Int,
    val remainingFraction: Float,
) {
    val expired: Boolean
        get() = remainingSeconds <= 0
}

/**
 * Uses server time from the offer-list response, not the device wall clock.
 * Only monotonic elapsed seconds after receipt are supplied by the UI.
 */
fun offerCountdown(offer: DriverRideOffer, elapsedSinceFetchSeconds: Int): OfferCountdown? = try {
    val issued = Instant.parse(offer.issuedAt)
    val expires = Instant.parse(offer.expiresAt)
    val serverTime = Instant.parse(offer.serverTimeAtFetch)
    val totalMillis = (expires - issued).inWholeMilliseconds
    val initialRemainingMillis = (expires - serverTime).inWholeMilliseconds
    if (totalMillis <= 0) return null
    val remainingMillis = (initialRemainingMillis - elapsedSinceFetchSeconds.coerceAtLeast(0) * 1_000L).coerceAtLeast(0)
    val remainingSeconds = if (remainingMillis == 0L) 0 else ((remainingMillis + 999L) / 1_000L).toInt()
    OfferCountdown(
        remainingSeconds = remainingSeconds,
        remainingFraction = (remainingMillis.toDouble() / totalMillis.toDouble()).coerceIn(0.0, 1.0).toFloat(),
    )
} catch (_: IllegalArgumentException) {
    null
}
