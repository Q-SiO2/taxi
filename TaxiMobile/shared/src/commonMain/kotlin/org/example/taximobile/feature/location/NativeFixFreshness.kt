package org.example.taximobile.feature.location

/** Monotonic acquisition facts only; never substitutes request/delivery time for a fix. */
fun nativeFixAcquiredAfterRequest(
    requestStartedNanos: Long,
    fixElapsedRealtimeNanos: Long,
    receivedAtNanos: Long,
): Boolean = requestStartedNanos >= 0L && fixElapsedRealtimeNanos > requestStartedNanos &&
    receivedAtNanos >= fixElapsedRealtimeNanos &&
    receivedAtNanos - fixElapsedRealtimeNanos <= 30_000_000_000L
