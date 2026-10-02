package org.example.taximobile.domain.realtime

/** A message is only a signal to reload an authorization-checked REST resource. */
data class LiveRideEvent(val type: String, val rideId: String)

interface LiveEventGateway {
    /** One attempt; connection admission precedes catch-up, and cancellation must propagate. */
    suspend fun listen(
        onConnected: suspend () -> Unit,
        onRideEvent: suspend (LiveRideEvent) -> Unit,
    )
}
