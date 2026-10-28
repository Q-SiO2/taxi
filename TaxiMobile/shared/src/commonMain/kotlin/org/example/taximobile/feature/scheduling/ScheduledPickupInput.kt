package org.example.taximobile.feature.scheduling

import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import kotlin.time.Instant
import kotlinx.datetime.LocalDate
import kotlinx.datetime.TimeZone
import kotlinx.datetime.atStartOfDayIn
import kotlinx.datetime.toLocalDateTime
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.domain.scheduling.ScheduledLocalTimeOptions
import org.example.taximobile.domain.scheduling.isScheduledLocalClockInput
import org.example.taximobile.domain.scheduling.scheduledCityTime
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.feature.ui.theme.TaxiTheme
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
private fun PickupControlIcon(calendar: Boolean) {
    val color = LocalContentColor.current
    Canvas(Modifier.size(20.dp)) {
        val unit = size.width / 20f
        val stroke = Stroke(1.5f * unit)
        fun line(x1: Float, y1: Float, x2: Float, y2: Float) = drawLine(color,
            Offset(x1 * unit, y1 * unit), Offset(x2 * unit, y2 * unit), strokeWidth = stroke.width, cap = StrokeCap.Round)
        if (calendar) {
            drawRoundRect(color, Offset(2 * unit, 4 * unit), Size(16 * unit, 14 * unit), CornerRadius(2 * unit), style = stroke)
            line(2f, 8f, 18f, 8f); line(6f, 2f, 6f, 6f); line(14f, 2f, 14f, 6f)
        } else {
            drawCircle(color, 8 * unit, center = Offset(10 * unit, 10 * unit), style = stroke)
            line(10f, 5f, 10f, 10f); line(10f, 10f, 14f, 12f)
        }
    }
}

@Composable
internal fun ScheduledCityChooser(cities: List<PublicRideCity>, selected: PublicRideCity?, onSelect: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(onClick = { expanded = true }, enabled = cities.any { it.bookingAvailable }, modifier = Modifier.fillMaxWidth()) {
            Text(selected?.name?.preferred(Locale.current.language) ?: stringResource(Res.string.scheduled_city_choose))
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            cities.forEach { city -> DropdownMenuItem(
                text = { Text(city.name.preferred(Locale.current.language)) }, enabled = city.bookingAvailable,
                onClick = { onSelect(city.id); expanded = false },
            ) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ScheduledPickupInput(
    draft: ScheduledPickupDraft,
    city: PublicRideCity?,
    readId: String?,
    read: ScheduledLocalTimeOptions?,
    busy: Boolean,
    checking: Boolean,
    onResolve: (String, String, String, String, String) -> Unit,
) {
    var datePicker by remember { mutableStateOf(false) }
    var timePicker by remember { mutableStateOf(false) }
    val dateDescription = stringResource(Res.string.scheduled_date_choose)
    val timeDescription = stringResource(Res.string.scheduled_time_choose)
    LaunchedEffect(readId, read, draft.requested, city?.id, city?.timezone) { draft.acceptRead(readId, read, city) }
    val dateField: @Composable (Modifier) -> Unit = { modifier -> OutlinedTextField(
        value = draft.date, onValueChange = draft::editDate, modifier = modifier,
        label = { Text(stringResource(Res.string.scheduled_date)) }, placeholder = { Text("YYYY-MM-DD") }, singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii),
        textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
        trailingIcon = { IconButton(onClick = { datePicker = true }, modifier = Modifier.semantics { contentDescription = dateDescription }) { PickupControlIcon(calendar = true) } },
    ) }
    val timeField: @Composable (Modifier) -> Unit = { modifier -> OutlinedTextField(
        value = draft.time, onValueChange = draft::editTime, modifier = modifier,
        label = { Text(stringResource(Res.string.scheduled_time)) }, placeholder = { Text("HH:mm") }, singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Ascii),
        textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
        trailingIcon = { IconButton(onClick = { timePicker = true }, modifier = Modifier.semantics { contentDescription = timeDescription }) { PickupControlIcon(calendar = false) } },
    ) }
    if (LocalDensity.current.fontScale > 1.3f) {
        dateField(Modifier.fillMaxWidth()); timeField(Modifier.fillMaxWidth())
    } else Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        dateField(Modifier.weight(1f)); timeField(Modifier.weight(1f))
    }
    if (city == null || !city.bookingAvailable) Text(stringResource(Res.string.scheduled_city_unavailable), color = TaxiTheme.colors.Warning600)
    val result = draft.resolution
    if (result != null) {
        when {
            !result.bookingAvailable -> Text(stringResource(Res.string.scheduled_city_unavailable), color = TaxiTheme.colors.Warning600)
            result.options.isEmpty() -> Text(stringResource(Res.string.scheduled_time_gap), color = TaxiTheme.colors.Warning600)
            result.options.size == 2 -> {
                Text(stringResource(Res.string.scheduled_time_overlap))
                result.options.forEach { option ->
                    val shown = scheduledCityTime(option.scheduledFor, result.cityTimezone)
                    if (shown != null) Row(Modifier.fillMaxWidth().selectable(selected = draft.selectedInstant == option.scheduledFor,
                        enabled = !busy, role = Role.RadioButton, onClick = { draft.choose(option.scheduledFor) }), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        RadioButton(selected = draft.selectedInstant == option.scheduledFor, onClick = null, enabled = !busy)
                        Text(ltrIsolate("${shown.time} (${shown.utcOffset})"), modifier = Modifier.weight(1f).padding(vertical = 12.dp))
                    }
                }
            }
        }
    }
    TaxiButton(
        label = stringResource(Res.string.scheduled_time_check),
        onClick = { draft.beginRead(city)?.let { onResolve(it.cityId, it.timezone, it.date, it.time, it.id) } },
        enabled = !busy && city?.bookingAvailable == true && isScheduledLocalClockInput(draft.date, draft.time), loading = checking,
    )
    if (datePicker) {
        // UTC is the calendar's date-only representation, never a booking conversion.
        val initial = remember { try { LocalDate.parse(draft.date).takeIf { it.year in 1900..2100 }?.atStartOfDayIn(TimeZone.UTC)?.toEpochMilliseconds() } catch (_: IllegalArgumentException) { null } }
        val picker = rememberDatePickerState(initialSelectedDateMillis = initial)
        DatePickerDialog(onDismissRequest = { datePicker = false }, confirmButton = {
            TextButton(onClick = { picker.selectedDateMillis?.let { draft.editDate(Instant.fromEpochMilliseconds(it).toLocalDateTime(TimeZone.UTC).date.toString()) }; datePicker = false }, enabled = picker.selectedDateMillis != null) { Text(stringResource(Res.string.scheduled_picker_apply)) }
        }, dismissButton = { TextButton(onClick = { datePicker = false }) { Text(stringResource(Res.string.scheduled_picker_cancel)) } }) { DatePicker(picker) }
    }
    if (timePicker) {
        val parts = draft.time.split(':')
        val picker = rememberTimePickerState(initialHour = parts.getOrNull(0)?.toIntOrNull()?.takeIf { it in 0..23 } ?: 0,
            initialMinute = parts.getOrNull(1)?.toIntOrNull()?.takeIf { it in 0..59 } ?: 0, is24Hour = true)
        AlertDialog(onDismissRequest = { timePicker = false }, title = { Text(stringResource(Res.string.scheduled_time_choose)) },
            text = { TimeInput(picker) }, confirmButton = { TextButton(onClick = {
                draft.editTime("${picker.hour.toString().padStart(2, '0')}:${picker.minute.toString().padStart(2, '0')}"); timePicker = false
            }) { Text(stringResource(Res.string.scheduled_picker_apply)) } }, dismissButton = { TextButton(onClick = { timePicker = false }) { Text(stringResource(Res.string.scheduled_picker_cancel)) } })
    }
}
