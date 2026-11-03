package org.example.taximobile.feature.driver

import kotlin.time.Instant
import kotlin.time.Duration
import kotlin.time.Duration.Companion.seconds
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
 * The anchor precedes the owned request, so transport delay is conservative.
 * This display cannot authorize an assignment or change the server deadline.
 */
fun offerCountdown(offer: DriverRideOffer, elapsedSinceFetchSeconds: Int): OfferCountdown? =
    offerCountdown(offer, elapsedSinceFetchSeconds.seconds)

fun offerCountdown(offer: DriverRideOffer, elapsed: Duration = offer.readStartedAt.elapsedNow()): OfferCountdown? = try {
    val issued = Instant.parse(offer.issuedAt)
    val expires = Instant.parse(offer.expiresAt)
    val serverTime = Instant.parse(offer.serverTimeAtFetch)
    val total = expires - issued
    val initial = expires - serverTime
    if (total <= Duration.ZERO || total > Int.MAX_VALUE.seconds || initial > Int.MAX_VALUE.seconds ||
        !elapsed.isFinite() || elapsed.isNegative()) return null
    val remaining = (initial - elapsed).coerceAtLeast(Duration.ZERO)
    val whole = remaining.inWholeSeconds
    val remainingSeconds = (whole + if (remaining > whole.seconds) 1 else 0).toInt()
    OfferCountdown(
        remainingSeconds = remainingSeconds,
        remainingFraction = (remaining / total).coerceIn(0.0, 1.0).toFloat(),
    )
} catch (_: IllegalArgumentException) {
    null
}
