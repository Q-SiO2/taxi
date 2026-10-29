package org.example.taximobile.feature.scheduling

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.listSaver
import kotlin.random.Random
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.domain.scheduling.ScheduledLocalTimeOptions
import org.example.taximobile.domain.scheduling.isScheduledLocalClockInput
import org.example.taximobile.domain.scheduling.matchesRequest

/** Ephemeral read identity, never sent as a command or authentication token. */
internal fun newScheduledReadId(): String = List(2) { Random.nextLong().toULong().toString(16).padStart(16, '0') }.joinToString("")

internal fun normalizeClockDigits(value: String): String = value.map { c -> when (c) {
    in '٠'..'٩' -> '0' + (c - '٠')
    in '۰'..'۹' -> '0' + (c - '۰')
    else -> c
} }.joinToString("")

internal data class ScheduledClockRead(val id: String, val cityId: String, val timezone: String, val date: String, val time: String)

/** Form inputs survive recreation; read results, choices and review authority do not. */
internal class ScheduledPickupDraft {
    var date by mutableStateOf(""); private set
    var time by mutableStateOf(""); private set
    var requested by mutableStateOf<ScheduledClockRead?>(null); private set
    var resolution by mutableStateOf<ScheduledLocalTimeOptions?>(null); private set
    var acceptedReadId by mutableStateOf<String?>(null); private set
    var selectedInstant by mutableStateOf<String?>(null); private set
    var selectionRevision by mutableStateOf(0L); private set

    fun editDate(value: String) { val next = normalizeClockDigits(value).trim().take(10); if (next != date) { date = next; invalidate() } }
    fun editTime(value: String) { val next = normalizeClockDigits(value).trim().take(5); if (next != time) { time = next; invalidate() } }
    private fun invalidate() {
        requested = null; resolution = null; acceptedReadId = null; selectedInstant = null; selectionRevision++
    }
    fun beginRead(city: PublicRideCity?, id: String = newScheduledReadId()): ScheduledClockRead? {
        if (city?.bookingAvailable != true || !isScheduledLocalClockInput(date, time) || id.isBlank()) return null
        invalidate()
        return ScheduledClockRead(id, city.id, city.timezone, date, time).also { requested = it }
    }
    fun acceptRead(id: String?, value: ScheduledLocalTimeOptions?, city: PublicRideCity?): Boolean {
        val query = requested ?: return false
        if (id != query.id || value == null || city?.bookingAvailable != true || city.id != query.cityId || city.timezone != query.timezone ||
            date != query.date || time != query.time || !value.matchesRequest(query.cityId, query.timezone, date, time)) return false
        resolution = value; acceptedReadId = id
        selectedInstant = value.options.singleOrNull()?.scheduledFor?.takeIf { city.bookingAvailable && value.bookingAvailable }
        selectionRevision++
        return true
    }
    fun choose(instant: String) {
        val options = resolution ?: return
        if (!options.bookingAvailable || options.options.none { it.scheduledFor == instant } || selectedInstant == instant) return
        selectedInstant = instant; selectionRevision++
    }
    companion object {
        val Saver = listSaver<ScheduledPickupDraft, String>(
            save = { listOf(it.date, it.time) },
            restore = { fields -> ScheduledPickupDraft().apply { editDate(fields[0]); editTime(fields[1]) } },
        )
    }
}
