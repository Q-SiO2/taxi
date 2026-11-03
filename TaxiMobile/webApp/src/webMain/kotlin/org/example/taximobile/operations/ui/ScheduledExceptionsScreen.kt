package org.example.taximobile.operations.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

/** Privacy-bounded exception review. The participant API does not expose names or supply data. */
@Composable
internal fun ScheduledExceptionsScreen(state: OperationsUiState) {
    val taxiColors = TaxiTheme.colors
    val page = state.snapshot?.scheduledBookingExceptions
    var expandedId by remember(state.scope.cityId, state.scope.operatorId) {
        mutableStateOf<String?>(null)
    }
    Column(
        Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        SectionHeading(
            stringResource(Res.string.web_booking_exceptions),
            stringResource(Res.string.web_booking_exceptions_help),
        )
        when {
            page == null -> EmptyState(
                stringResource(Res.string.web_booking_unavailable),
                stringResource(Res.string.web_booking_unavailable_help),
            )
            page.items.isEmpty() -> EmptyState(
                stringResource(Res.string.web_booking_empty),
                stringResource(Res.string.web_booking_empty_help),
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
                PageLimitNote(page.items.size, page.total)
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
    val taxiColors = TaxiTheme.colors
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
                        "${recruitmentLabel(booking.serviceType)} · ${ltrIsolate(compactTimestamp(booking.scheduledFor))}",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        stringResource(Res.string.web_booking_reference, ltrIsolate(booking.id), ltrIsolate(booking.cityTimezone)),
                        color = taxiColors.Ink500,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                StatusBadge(booking.status, label = bookingLabel(booking.status))
            }
            val route = "${booking.pickup.address ?: coordinateLabel(booking.pickup.latitude, booking.pickup.longitude)} → " +
                (booking.destination.address ?: coordinateLabel(booking.destination.latitude, booking.destination.longitude))
            Text(ltrIsolate(route), style = recruitmentTextStyle(route), color = taxiColors.Ink700)
            Text(
                stringResource(Res.string.web_booking_economics,
                    ltrIsolate("${booking.economics.passengerTotal} ${booking.economics.currency}"),
                    ltrIsolate("${booking.economics.expectedDriverNet} ${booking.economics.currency}"),
                    ltrIsolate("${booking.economics.operatorAllocation} ${booking.economics.currency}")),
                color = taxiColors.Ink700,
            )
            Text(
                stringResource(if (booking.driverCommitted) Res.string.web_booking_committed else Res.string.web_booking_uncommitted),
                color = if (booking.driverCommitted) taxiColors.Success600 else taxiColors.Warning600,
                style = MaterialTheme.typography.bodySmall,
            )
            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onToggle) { Text(stringResource(if (expanded) Res.string.web_booking_hide else Res.string.web_booking_review)) }
            if (expanded) {
                Text(stringResource(Res.string.web_booking_fare_parts,
                    ltrIsolate("${booking.economics.transportFare} ${booking.economics.currency}"),
                    ltrIsolate("${booking.economics.schedulingSurcharge} ${booking.economics.currency}"),
                    ltrIsolate("${booking.economics.operatorServiceFee} ${booking.economics.currency}")))
                Text(stringResource(Res.string.web_booking_versions, ltrIsolate(booking.economics.pricingRuleVersion), ltrIsolate(booking.economics.operatorFeePolicyVersion), ltrIsolate(booking.economics.schedulingPolicyVersion)))
                val termsResource = bookingRefundCodeResource(booking.cancellationTerms.surchargeRefundMode)
                Text(when {
                    termsResource == null -> stringResource(Res.string.web_booking_terms_unknown)
                    booking.cancellationTerms.surchargeRefundMode == "FULL_BEFORE_CUTOFF" ->
                        stringResource(termsResource, ltrIsolate(booking.cancellationTerms.passengerCancelCutoffMinutes.toString()))
                    else -> stringResource(termsResource)
                })
                booking.cancellationFinancialOutcome?.let { Text(stringResource(Res.string.web_booking_cancellation, bookingLabel(it))) }
                booking.liveRideId?.let { Text(stringResource(Res.string.web_booking_live_ride, ltrIsolate(it))) }
                Text(
                    stringResource(Res.string.web_booking_read_only),
                    color = taxiColors.Ink500,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}

private fun coordinateLabel(latitude: Double, longitude: Double): String =
    "${latitude.toString().take(9)}, ${longitude.toString().take(9)}"
