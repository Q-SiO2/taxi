package org.example.taximobile.domain.realtime

/** A message is only a signal to reload an authorization-checked REST resource. */
data class LiveRideEvent(val type: String, val rideId: String)

interface LiveEventGateway {
    suspend fun listen(onRideEvent: suspend (LiveRideEvent) -> Unit)
}
