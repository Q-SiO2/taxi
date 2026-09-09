package org.example.taximobile.feature.location

import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_foreground_driver_location_unavailable

/**
 * Pure scheduling policy for foreground-only driver location observations.
 *
 * This class neither requests platform permission nor sends data. Platform
 * roots call it while rendering the driver app, then use an already-authorized
 * one-shot location request and the authenticated driver gateway. Leaving the
 * foreground or every non-operational availability state disarms it.
 */
class ForegroundDriverLocationPolicy(
    private val availableIntervalMillis: Long = 15_000,
    private val activeRideIntervalMillis: Long = 10_000,
    private val unavailableBackoffMillis: Long = 60_000,
) {
    private var operationalWindowActive = false
    private var nextEligibleAtMillis = 0L

    init {
        require(availableIntervalMillis > 0)
        require(activeRideIntervalMillis > 0)
        require(unavailableBackoffMillis > 0)
    }

    fun shouldRequest(
        nowMillis: Long,
        availability: DriverAvailabilityStatus?,
        appInForeground: Boolean,
        networkUsable: Boolean,
        platformRequestInFlight: Boolean,
        appActionInFlight: Boolean,
    ): Boolean {
        val operational = availability != null && availability in OPERATIONAL_LOCATION_STATES
        if (!appInForeground || !networkUsable || !operational) {
            operationalWindowActive = false
            nextEligibleAtMillis = 0L
            return false
        }
        if (!operationalWindowActive) {
            operationalWindowActive = true
            nextEligibleAtMillis = nowMillis
        }
        if (platformRequestInFlight || appActionInFlight || nowMillis < nextEligibleAtMillis) {
            return false
        }
        nextEligibleAtMillis = nowMillis + when (availability) {
            DriverAvailabilityStatus.AVAILABLE,
            DriverAvailabilityStatus.OFFERED_RIDE -> availableIntervalMillis
            else -> activeRideIntervalMillis
        }
        return true
    }

    /** Avoids repeatedly probing disabled services or revoked permission. */
    fun recordUnavailable(nowMillis: Long) {
        if (operationalWindowActive) {
            nextEligibleAtMillis = maxOf(nextEligibleAtMillis, nowMillis + unavailableBackoffMillis)
        }
    }

    companion object {
        val OPERATIONAL_LOCATION_STATES = setOf(
            DriverAvailabilityStatus.AVAILABLE,
            DriverAvailabilityStatus.OFFERED_RIDE,
            DriverAvailabilityStatus.EN_ROUTE,
            DriverAvailabilityStatus.AT_PICKUP,
            DriverAvailabilityStatus.ON_RIDE,
        )
    }
}

fun foregroundDriverLocationUnavailableMessage(): UiMessage =
    UiMessage(Res.string.message_foreground_driver_location_unavailable)
