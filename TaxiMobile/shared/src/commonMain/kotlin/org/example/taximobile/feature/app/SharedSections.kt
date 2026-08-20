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
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.domain.support.SupportTicket
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiTextField
import org.example.taximobile.feature.ui.components.SuccessConfirmation
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

internal fun validCoordinates(latitude: String, longitude: String): Coordinates? {
    val latitudeValue = latitude.toDoubleOrNull() ?: return null
    val longitudeValue = longitude.toDoubleOrNull() ?: return null
    if (latitudeValue !in -90.0..90.0 || longitudeValue !in -180.0..180.0) return null
    return Coordinates(latitudeValue, longitudeValue)
}

internal fun formatKilometers(distanceMeters: Int): String =
    ((distanceMeters + 50) / 100).let { tenths -> "${tenths / 10}.${tenths % 10}" }

internal fun formatMinutes(durationSeconds: Int): Int = maxOf(1, (durationSeconds + 30) / 60)
