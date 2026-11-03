package org.example.taximobile.domain.drivers

import kotlin.time.Instant
import org.example.taximobile.domain.rides.Coordinates

/** Native acquisition facts. Never replace [observedAtEpochMillis] with send time. */
data class DriverLocationObservation(
    val coordinates: Coordinates,
    val observedAtEpochMillis: Long,
    val accuracyMeters: Double,
) {
    fun isUsableAt(nowEpochMillis: Long): Boolean {
        val ageMillis = nowEpochMillis - observedAtEpochMillis
        return coordinates.latitude.isFinite() && coordinates.latitude in -90.0..90.0 &&
            coordinates.longitude.isFinite() && coordinates.longitude in -180.0..180.0 &&
            accuracyMeters.isFinite() && accuracyMeters in 0.0..100.0 &&
            ageMillis in -5_000L..30_000L
    }

    val observedAtIso: String
        get() = Instant.fromEpochMilliseconds(observedAtEpochMillis).toString()
}
