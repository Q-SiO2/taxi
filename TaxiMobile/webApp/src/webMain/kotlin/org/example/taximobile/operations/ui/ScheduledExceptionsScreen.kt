package org.example.taximobile.operations.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.ScheduledBookingExceptionRecord
import org.example.taximobile.operations.state.OperationsUiState

/** Privacy-bounded exception review. The participant API does not expose names or supply data. */
@Composable
internal fun ScheduledExceptionsScreen(state: OperationsUiState) {
    val page = state.snapshot?.scheduledBookingExceptions
    var expandedId by remember(state.scope.cityId, state.scope.operatorId) {
        mutableStateOf<String?>(null)
    }
    Column(
        Modifier.fillMaxWidth().padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        SectionHeading(
            "Scheduled booking exceptions",
            "Review backend-confirmed offering, handoff, cancellation, and unfulfilled states in the selected authorized scope. Passenger identity and driver supply are intentionally absent.",
        )
        when {
            page == null -> EmptyState(
                "Exception review unavailable",
                "Select an authorized city or refresh the scoped operations snapshot.",
            )
            page.items.isEmpty() -> EmptyState(
                "No scheduled exceptions",
                "There are no offering, handoff, cancelled, or unfulfilled bookings in this scope.",
            )
            else -> {
                page.items.forEach { booking ->
                    ScheduledExceptionCard(
                        booking = booking,
                        expanded = expandedId == booking.id,
                        onToggle = {
                            expandedId = if (expandedId == booking.id) null else booking.id
                        },
                    )
                }
                Text(
                    "Showing ${page.items.size} of ${page.total} backend records.",
                    color = TaxiColors.Ink500,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

@Composable
private fun ScheduledExceptionCard(
    booking: ScheduledBookingExceptionRecord,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    DataCard {
        Column(
            Modifier.fillMaxWidth().padding(TaxiSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "${booking.serviceType.replace('_', ' ')} · ${compactTimestamp(booking.scheduledFor)}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        "${booking.cityTimezone} · booking ${booking.id}",
                        color = TaxiColors.Ink500,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                StatusBadge(booking.status)
            }
            Text(
                "${booking.pickup.address ?: coordinateLabel(booking.pickup.latitude, booking.pickup.longitude)} → " +
                    (booking.destination.address ?: coordinateLabel(booking.destination.latitude, booking.destination.longitude)),
                color = TaxiColors.Ink700,
            )
            Text(
                "Passenger total ${booking.economics.passengerTotal} ${booking.economics.currency} · " +
                    "driver net ${booking.economics.expectedDriverNet} · operator ${booking.economics.operatorAllocation}",
                color = TaxiColors.Ink700,
            )
            Text(
                if (booking.driverCommitted) "A driver commitment is recorded." else "No active driver commitment is represented.",
                color = if (booking.driverCommitted) TaxiColors.Success600 else TaxiColors.Warning600,
                style = MaterialTheme.typography.bodySmall,
            )
            OutlinedButton(onClick = onToggle) { Text(if (expanded) "Hide policy detail" else "Review policy detail") }
            if (expanded) {
                Text("Transport ${booking.economics.transportFare} · scheduling ${booking.economics.schedulingSurcharge} · service fee ${booking.economics.operatorServiceFee}")
                Text("Tariff ${booking.economics.pricingRuleVersion} · fee ${booking.economics.operatorFeePolicyVersion} · schedule ${booking.economics.schedulingPolicyVersion}")
                Text(booking.cancellationTerms.summary)
                booking.cancellationFinancialOutcome?.let { Text("Cancellation outcome: $it") }
                booking.liveRideId?.let { Text("Live ride: $it") }
                Text(
                    "This review is read-only. Lifecycle repair remains a backend/worker responsibility.",
                    color = TaxiColors.Ink500,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

private fun coordinateLabel(latitude: Double, longitude: Double): String =
    "${latitude.toString().take(9)}, ${longitude.toString().take(9)}"
