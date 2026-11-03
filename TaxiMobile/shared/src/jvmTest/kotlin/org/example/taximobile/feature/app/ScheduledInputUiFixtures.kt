package org.example.taximobile.feature.app

import androidx.compose.runtime.MutableState
import androidx.compose.ui.test.*
import org.example.taximobile.domain.rides.LocalizedText
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.domain.scheduling.ScheduledLocalTimeOption
import org.example.taximobile.domain.scheduling.ScheduledLocalTimeOptions
import java.time.LocalDateTime
import java.time.ZoneId

internal fun scheduledTestCity(id: String = "synthetic-city", name: String = "Fès") =
    PublicRideCity(id, "FES", LocalizedText(name, name, "فاس"), "Africa/Casablanca", "ACTIVE", true)
internal fun AppUiState.PassengerReady.withScheduledTestCity() = copy(serviceCities = listOf(scheduledTestCity()))

/** Explicitly simulated server, independently using Java's valid-offset API. */
internal fun scheduledClockFixture(city: String, zone: String, date: String, time: String): ScheduledLocalTimeOptions {
    val local = LocalDateTime.parse("${date}T$time")
    val options = ZoneId.of(zone).rules.getValidOffsets(local).map { offset ->
        ScheduledLocalTimeOption(local.toInstant(offset).toString(), offset.totalSeconds)
    }.sortedBy { java.time.Instant.parse(it.scheduledFor) }
    return ScheduledLocalTimeOptions(city, zone, date, time, true, "synthetic-rules", options)
}
internal fun clockResponder(ui: MutableState<AppUiState.PassengerReady>): (String, String, String, String, String) -> Unit =
    { city, zone, date, time, id -> ui.value = ui.value.copy(scheduledLocalTimeOptions = scheduledClockFixture(city, zone, date, time), scheduledLocalTimeReadId = id) }

@OptIn(ExperimentalTestApi::class)
internal fun ComposeUiTest.chooseScheduledClock(date: String, time: String, language: String = "en") {
    val labels = when (language) {
        "fr" -> listOf("Date", "Heure", "Vérifier l’heure")
        "ar" -> listOf("التاريخ", "الوقت", "تحقق من وقت الانطلاق")
        else -> listOf("Date", "Time", "Check pickup time")
    }
    onNodeWithText(labels[0]).performScrollTo().performTextReplacement(date)
    onNodeWithText(labels[1]).performScrollTo().performTextReplacement(time)
    onNodeWithText(labels[2]).performScrollTo().performClick()
}
