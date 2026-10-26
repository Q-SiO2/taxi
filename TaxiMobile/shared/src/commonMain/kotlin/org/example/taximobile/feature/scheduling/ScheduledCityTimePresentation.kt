package org.example.taximobile.feature.scheduling

import androidx.compose.runtime.Composable
import org.example.taximobile.domain.scheduling.ScheduledCityTime
import org.example.taximobile.domain.scheduling.scheduledCityTime
import org.example.taximobile.domain.scheduling.scheduledCityWindow
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
internal fun scheduledPickupTime(timestamp: String, cityTimezone: String): String =
    scheduledCityTime(timestamp, cityTimezone)?.localizedCityTime()
        ?: stringResource(Res.string.scheduled_time_unavailable)

@Composable
internal fun scheduledProtectedTime(from: String, until: String, cityTimezone: String): String {
    val window = scheduledCityWindow(from, until, cityTimezone)
        ?: return stringResource(Res.string.scheduled_time_unavailable)
    return stringResource(Res.string.scheduled_protected_window, window.from.localizedCityTime(), window.until.localizedCityTime())
}

@Composable
private fun ScheduledCityTime.localizedCityTime(): String = ltrIsolate(
    stringResource(Res.string.scheduled_city_time, date, time, utcOffset),
)
