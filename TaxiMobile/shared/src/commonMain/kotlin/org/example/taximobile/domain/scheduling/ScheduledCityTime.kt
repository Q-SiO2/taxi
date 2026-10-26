package org.example.taximobile.domain.scheduling

import kotlin.time.Instant
import kotlinx.datetime.DateTimeArithmeticException
import kotlinx.datetime.TimeZone
import kotlinx.datetime.offsetAt
import kotlinx.datetime.toLocalDateTime
import org.example.taximobile.core.time.cityTimeZoneSupportAvailable

/** Display-only data. Never use this representation for server deadlines or pricing. */
data class ScheduledCityTime(val date: String, val time: String, val utcOffset: String)

data class ScheduledCityWindow(val from: ScheduledCityTime, val until: ScheduledCityTime)

private val namedCityZones by lazy {
    if (cityTimeZoneSupportAvailable()) TimeZone.availableZoneIds + "UTC" else emptySet()
}

fun scheduledCityTime(timestamp: String, cityTimezone: String): ScheduledCityTime? = try {
    if (cityTimezone !in namedCityZones) return null
    val instant = Instant.parse(timestamp)
    cityTime(instant, TimeZone.of(cityTimezone))
} catch (_: IllegalArgumentException) {
    null
} catch (_: DateTimeArithmeticException) {
    null
}

fun scheduledCityWindow(from: String, until: String, cityTimezone: String): ScheduledCityWindow? = try {
    if (cityTimezone !in namedCityZones) return null
    val start = Instant.parse(from)
    val end = Instant.parse(until)
    if (start >= end) return null
    val zone = TimeZone.of(cityTimezone)
    ScheduledCityWindow(cityTime(start, zone), cityTime(end, zone))
} catch (_: IllegalArgumentException) {
    null
} catch (_: DateTimeArithmeticException) {
    null
}

private fun cityTime(instant: Instant, zone: TimeZone): ScheduledCityTime {
    val local = instant.toLocalDateTime(zone)
    val time = buildString {
        append(local.hour.toString().padStart(2, '0'))
        append(':'); append(local.minute.toString().padStart(2, '0'))
        if (local.second != 0 || local.nanosecond != 0) {
            append(':'); append(local.second.toString().padStart(2, '0'))
            if (local.nanosecond != 0) {
                append('.'); append(local.nanosecond.toString().padStart(9, '0').trimEnd('0'))
            }
        }
    }
    val offset = zone.offsetAt(instant)
    return ScheduledCityTime(local.date.toString(), time, if (offset.totalSeconds == 0) "UTC" else "UTC$offset")
}
