package org.example.taximobile.domain.scheduling

import kotlin.time.Instant
import kotlinx.datetime.LocalDateTime
import kotlinx.datetime.UtcOffset

data class ScheduledLocalTimeOption(val scheduledFor: String, val utcOffsetSeconds: Int)

/** Backend clock resolution only: not a fare, reservation or booking approval. */
data class ScheduledLocalTimeOptions(
    val cityId: String,
    val cityTimezone: String,
    val localDate: String,
    val localTime: String,
    val bookingAvailable: Boolean,
    val rulesVersion: String,
    val options: List<ScheduledLocalTimeOption>,
)

fun isScheduledLocalClockInput(date: String, time: String): Boolean = try {
    date.matches(Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}")) &&
        time.matches(Regex("([01][0-9]|2[0-3]):[0-5][0-9]")) &&
        LocalDateTime.parse("${date}T$time").second == 0
} catch (_: IllegalArgumentException) {
    false
}

/** Reject stale context and data that this client cannot present faithfully. */
fun ScheduledLocalTimeOptions.matchesRequest(city: String, timezone: String, date: String, time: String): Boolean = try {
    if (city.isBlank() || cityId != city || cityTimezone != timezone || localDate != date || localTime != time ||
        !isScheduledLocalClockInput(date, time) || rulesVersion.isBlank() || rulesVersion.length > 32 ||
        options.size > 2 || scheduledCityTime("2026-01-01T00:00:00Z", timezone) == null) return false
    val instants = options.map { Instant.parse(it.scheduledFor) }
    if (instants.zipWithNext().any { (a, b) -> a >= b }) return false
    options.all { option ->
        val shown = scheduledCityTime(option.scheduledFor, timezone) ?: return false
        val offset = if (shown.utcOffset == "UTC") 0 else UtcOffset.parse(shown.utcOffset.removePrefix("UTC")).totalSeconds
        shown.date == date && shown.time == time && offset == option.utcOffsetSeconds
    }
} catch (_: IllegalArgumentException) {
    false
}
