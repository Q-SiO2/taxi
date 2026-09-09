package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.safety.SafetyReport
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.domain.support.SupportTicket
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiTextField
import org.example.taximobile.feature.ui.components.SuccessConfirmation
import org.example.taximobile.feature.ui.components.ToastBanner
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
internal fun NotificationInboxSection(
    notifications: List<AppNotification>,
    pendingAction: AppAction?,
    onMarkRead: (String) -> Unit,
) {
    if (notifications.isEmpty()) {
        Text(stringResource(Res.string.no_notifications), style = MaterialTheme.typography.bodyLarge)
        return
    }
    notifications.take(10).forEach { notification ->
        val (title, body) = notification.localizedCopy()
        Text(title, style = MaterialTheme.typography.bodyLarge)
        Text(body, style = MaterialTheme.typography.bodyMedium)
        if (!notification.read) {
            TaxiButton(
                label = stringResource(Res.string.mark_read),
                onClick = { onMarkRead(notification.id) },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.MARK_NOTIFICATION_READ, notification.id),
                style = TaxiButtonStyle.Tertiary,
            )
        }
    }
}

@Composable
private fun AppNotification.localizedCopy(): Pair<String, String> {
    val resources = notificationCopyResources(type) ?: return fallbackTitle to fallbackBody
    return stringResource(resources.first) to stringResource(resources.second)
}

internal fun notificationCopyResources(type: String): Pair<StringResource, StringResource>? = when (type) {
    "RIDE_OFFER_AVAILABLE" -> Res.string.notification_ride_offer_title to Res.string.notification_ride_offer_body
    "NO_DRIVER_AVAILABLE" -> Res.string.notification_no_driver_title to Res.string.notification_no_driver_body
    "RIDE_CANCELLED_BY_DRIVER" ->
        Res.string.notification_driver_cancelled_title to Res.string.notification_driver_cancelled_body
    "DRIVER_ASSIGNED" -> Res.string.notification_driver_assigned_title to Res.string.notification_driver_assigned_body
    "DRIVER_CREDENTIAL_EXPIRING" ->
        Res.string.notification_credential_expiring_title to Res.string.notification_credential_expiring_body
    "DRIVER_CREDENTIAL_EXPIRED" ->
        Res.string.notification_credential_expired_title to Res.string.notification_credential_expired_body
    "DRIVER_CITY_AUTHORIZATION_CHANGED" ->
        Res.string.notification_city_authorization_title to Res.string.notification_city_authorization_body
    "SCHEDULED_OFFER" ->
        Res.string.notification_scheduled_title to Res.string.notification_scheduled_offer_body
    "SCHEDULED_DRIVER_COMMITTED" ->
        Res.string.notification_scheduled_title to Res.string.notification_scheduled_driver_committed_body
    "SCHEDULED_DISPATCH_STARTED" ->
        Res.string.notification_scheduled_title to Res.string.notification_scheduled_dispatch_started_body
    "SCHEDULED_FALLBACK_MATCHING" ->
        Res.string.notification_scheduled_title to Res.string.notification_scheduled_fallback_matching_body
    "SCHEDULED_UNFULFILLED" ->
        Res.string.notification_scheduled_title to Res.string.notification_scheduled_unfulfilled_body
    "PASSENGER_AT_PICKUP" ->
        Res.string.notification_ride_update_title to Res.string.notification_passenger_at_pickup_body
    "PASSENGER_NEEDS_MORE_TIME" ->
        Res.string.notification_ride_update_title to Res.string.notification_passenger_needs_more_time_body
    "PASSENGER_CANNOT_FIND_DRIVER" ->
        Res.string.notification_ride_update_title to Res.string.notification_passenger_cannot_find_driver_body
    "DRIVER_ON_MY_WAY" ->
        Res.string.notification_ride_update_title to Res.string.notification_driver_on_my_way_body
    "DRIVER_AT_PICKUP" ->
        Res.string.notification_ride_update_title to Res.string.notification_driver_at_pickup_body
    "DRIVER_CANNOT_FIND_PASSENGER" ->
        Res.string.notification_ride_update_title to Res.string.notification_driver_cannot_find_passenger_body
    else -> null
}

@Composable
internal fun SupportTicketSection(
    tickets: List<SupportTicket>,
    activeRideId: String?,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    onCreate: (SupportCategory, String, String, String?) -> Unit,
) {
    var category by remember { mutableStateOf(SupportCategory.RIDE_PROBLEM) }
    var subject by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    LaunchedEffect(completedAction?.sequence) {
        if (completedAction.confirms(AppActionKind.CREATE_SUPPORT_TICKET)) {
            category = SupportCategory.RIDE_PROBLEM
            subject = ""
            description = ""
        }
    }
    Text(stringResource(Res.string.contact_support), style = MaterialTheme.typography.titleMedium)
    if (completedAction.confirms(AppActionKind.CREATE_SUPPORT_TICKET)) {
        SuccessConfirmation(
            stringResource(Res.string.support_request_sent_confirmation),
            requireNotNull(completedAction).sequence,
        )
    }
    if (tickets.isNotEmpty()) {
        Text(stringResource(Res.string.support_requests), style = MaterialTheme.typography.bodyLarge)
        tickets.take(10).forEach { ticket ->
            Text(stringResource(Res.string.support_ticket_summary, supportStatusLabel(ticket.status), ticket.subject))
            ticket.latestPublicMessage?.let {
                Text(stringResource(Res.string.case_latest_response, it), style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
    activeRideId?.let {
        Text(stringResource(Res.string.support_active_ride_notice), style = MaterialTheme.typography.bodyMedium)
    }
    TextButton(onClick = {
        category = SupportCategory.entries[(category.ordinal + 1) % SupportCategory.entries.size]
    }) { Text(stringResource(Res.string.support_category, supportCategoryLabel(category))) }
    TaxiTextField(subject, { subject = it }, stringResource(Res.string.subject))
    OutlinedTextField(
        value = description,
        onValueChange = { description = it },
        modifier = Modifier.fillMaxWidth(),
        label = { Text(stringResource(Res.string.describe_problem)) },
        minLines = 3,
    )
    TaxiButton(
        label = stringResource(Res.string.send_support_request),
        onClick = { onCreate(category, subject.trim(), description.trim(), activeRideId) },
        enabled = subject.isNotBlank() && description.isNotBlank() && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.CREATE_SUPPORT_TICKET),
    )
}

@Composable
internal fun SafetyReportSection(
    reports: List<SafetyReport>,
    rideIds: List<String>,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    onCreate: (String, SafetyCategory, String) -> Unit,
) {
    val reportableRideIds = rideIds.distinct()
    var selectedRideId by remember(reportableRideIds) { mutableStateOf(reportableRideIds.firstOrNull()) }
    var category by remember { mutableStateOf(SafetyCategory.OTHER_SAFETY) }
    var description by remember { mutableStateOf("") }
    LaunchedEffect(completedAction?.sequence) {
        if (completedAction.confirms(AppActionKind.CREATE_SAFETY_REPORT)) {
            category = SafetyCategory.OTHER_SAFETY
            description = ""
        }
    }

    Text(stringResource(Res.string.safety_reports_title), style = MaterialTheme.typography.titleMedium)
    ToastBanner(stringResource(Res.string.safety_not_emergency_warning), StatusTone.Warning)
    if (completedAction.confirms(AppActionKind.CREATE_SAFETY_REPORT)) {
        SuccessConfirmation(
            stringResource(Res.string.safety_report_sent_confirmation),
            requireNotNull(completedAction).sequence,
        )
    }
    if (reports.isNotEmpty()) {
        Text(stringResource(Res.string.safety_reports_history), style = MaterialTheme.typography.bodyLarge)
        reports.take(10).forEach { report ->
            Text(
                stringResource(
                    Res.string.safety_report_summary,
                    safetyStatusLabel(report.status),
                    safetyCategoryLabel(report.category),
                    ltrIsolate(report.rideId.take(8)),
                )
            )
            report.latestPublicMessage?.let {
                Text(stringResource(Res.string.case_latest_response, it), style = MaterialTheme.typography.bodyMedium)
            }
        }
    }

    if (selectedRideId == null) {
        Text(stringResource(Res.string.safety_requires_ride), style = MaterialTheme.typography.bodyMedium)
    } else {
        TextButton(
            onClick = {
                val currentIndex = reportableRideIds.indexOf(selectedRideId)
                selectedRideId = reportableRideIds[(currentIndex + 1) % reportableRideIds.size]
            },
            enabled = reportableRideIds.size > 1 && pendingAction == null,
        ) {
            Text(stringResource(Res.string.safety_linked_ride, ltrIsolate(requireNotNull(selectedRideId).take(8))))
        }
    }
    TextButton(
        onClick = {
            val categories = SafetyCategory.entries.filterNot { it == SafetyCategory.UNKNOWN }
            category = categories[(categories.indexOf(category) + 1) % categories.size]
        },
        enabled = pendingAction == null,
    ) {
        Text(stringResource(Res.string.safety_category, safetyCategoryLabel(category)))
    }
    OutlinedTextField(
        value = description,
        onValueChange = { if (it.length <= 4000) description = it },
        modifier = Modifier.fillMaxWidth(),
        label = { Text(stringResource(Res.string.describe_safety_concern)) },
        minLines = 3,
    )
    TaxiButton(
        label = stringResource(Res.string.send_safety_report),
        onClick = { onCreate(requireNotNull(selectedRideId), category, description.trim()) },
        enabled = selectedRideId != null && description.trim().length >= 3 && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.CREATE_SAFETY_REPORT),
    )
}

@Composable
private fun supportCategoryLabel(category: SupportCategory): String = stringResource(
    when (category) {
        SupportCategory.RIDE_PROBLEM -> Res.string.support_category_ride_problem
        SupportCategory.FARE_DISPUTE -> Res.string.support_category_fare_dispute
        SupportCategory.ACCOUNT_ACCESS -> Res.string.support_category_account_access
        SupportCategory.OTHER -> Res.string.support_category_other
    }
)

@Composable
private fun supportStatusLabel(status: String): String = stringResource(
    when (status) {
        "OPEN" -> Res.string.support_status_open
        "IN_PROGRESS" -> Res.string.support_status_in_progress
        "RESOLVED" -> Res.string.support_status_resolved
        "CLOSED" -> Res.string.support_status_closed
        else -> Res.string.support_status_unknown
    }
)

@Composable
private fun safetyCategoryLabel(category: SafetyCategory): String = stringResource(
    when (category) {
        SafetyCategory.IMMEDIATE_DANGER -> Res.string.safety_category_immediate_danger
        SafetyCategory.HARASSMENT -> Res.string.safety_category_harassment
        SafetyCategory.ASSAULT -> Res.string.safety_category_assault
        SafetyCategory.UNSAFE_DRIVING -> Res.string.safety_category_unsafe_driving
        SafetyCategory.DISCRIMINATION -> Res.string.safety_category_discrimination
        SafetyCategory.VEHICLE_SAFETY -> Res.string.safety_category_vehicle_safety
        SafetyCategory.OTHER_SAFETY -> Res.string.safety_category_other
        SafetyCategory.UNKNOWN -> Res.string.safety_category_unknown
    }
)

@Composable
private fun safetyStatusLabel(status: String): String = stringResource(
    when (status) {
        "SUBMITTED" -> Res.string.safety_status_submitted
        "ACKNOWLEDGED" -> Res.string.safety_status_acknowledged
        "ESCALATED" -> Res.string.safety_status_escalated
        "RESOLVED" -> Res.string.safety_status_resolved
        "CLOSED" -> Res.string.safety_status_closed
        else -> Res.string.safety_status_unknown
    }
)

internal fun validCoordinates(latitude: String, longitude: String): Coordinates? {
    val latitudeValue = latitude.toDoubleOrNull() ?: return null
    val longitudeValue = longitude.toDoubleOrNull() ?: return null
    if (latitudeValue !in -90.0..90.0 || longitudeValue !in -180.0..180.0) return null
    return Coordinates(latitudeValue, longitudeValue)
}

internal fun formatKilometers(distanceMeters: Int): String =
    ((distanceMeters + 50) / 100).let { tenths -> "${tenths / 10}.${tenths % 10}" }

internal fun formatMinutes(durationSeconds: Int): Int = maxOf(1, (durationSeconds + 30) / 60)
