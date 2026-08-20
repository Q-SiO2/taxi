package org.example.taximobile.feature.location

/**
 * Admits one foreground platform-location request at a time. Repeated taps are
 * ignored instead of cancelling the callback already owned by the first tap.
 */
class OneShotLocationGate {
    var inFlight: Boolean = false
        private set

    fun tryStart(): Boolean {
        if (inFlight) return false
        inFlight = true
        return true
    }

    fun finish() {
        inFlight = false
    }
}

