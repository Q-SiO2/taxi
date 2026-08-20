package org.example.taximobile.feature.passenger

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionCompletion
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.NotificationInboxSection
import org.example.taximobile.feature.app.SupportTicketSection
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.app.formatKilometers
import org.example.taximobile.feature.app.formatMinutes
import org.example.taximobile.feature.app.passengerStatusResource
import org.example.taximobile.feature.app.validCoordinates
import org.example.taximobile.feature.maps.MapLibreTripMap
import org.example.taximobile.feature.ui.components.ConfirmDialog
import org.example.taximobile.feature.ui.components.DriverCard
import org.example.taximobile.feature.ui.components.FareBlock
import org.example.taximobile.feature.ui.components.FareBreakdownRow
import org.example.taximobile.feature.ui.components.MapFab
import org.example.taximobile.feature.ui.components.EmptyState
import org.example.taximobile.feature.ui.components.LocationSelectionField
import org.example.taximobile.feature.ui.components.RatingStars
import org.example.taximobile.feature.ui.components.PaymentMethodCard
import org.example.taximobile.feature.ui.components.StatusPill
import org.example.taximobile.feature.ui.components.SuccessConfirmation
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiSegmentedControl
import org.example.taximobile.feature.ui.components.TaxiSheet
import org.example.taximobile.feature.ui.components.TaxiSheetSnap
import org.example.taximobile.feature.ui.components.TaxiTextField
import org.example.taximobile.feature.ui.components.ToastBanner
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.text.UiMessage
import org.example.taximobile.feature.ui.text.resolve
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

private enum class PassengerSheetPanel { Ride, Account, Inbox }
private enum class MapSelectionTarget { Pickup, Destination }

private class PassengerTripFormState {
    var pickupLatitude by mutableStateOf("")
    var pickupLongitude by mutableStateOf("")
    var destinationLatitude by mutableStateOf("")
    var destinationLongitude by mutableStateOf("")
    var pickupAddress by mutableStateOf<String?>(null)
    var destinationAddress by mutableStateOf<String?>(null)
    var estimatedTrip by mutableStateOf<Pair<Coordinates, Coordinates>?>(null)
    var selectionTarget by mutableStateOf(MapSelectionTarget.Pickup)
    var locationMessage by mutableStateOf<UiMessage?>(null)

    val pickup: Coordinates?
        get() = validCoordinates(pickupLatitude, pickupLongitude)?.copy(address = pickupAddress)
    val destination: Coordinates?
        get() = validCoordinates(destinationLatitude, destinationLongitude)?.copy(address = destinationAddress)
    val trip: Pair<Coordinates, Coordinates>?
        get() = pickup?.let { start -> destination?.let { end -> start to end } }

    fun select(coordinates: Coordinates) {
        if (selectionTarget == MapSelectionTarget.Pickup) {
            pickupLatitude = coordinates.latitude.toString()
            pickupLongitude = coordinates.longitude.toString()
            pickupAddress = coordinates.address
            selectionTarget = MapSelectionTarget.Destination
        } else {
            destinationLatitude = coordinates.latitude.toString()
            destinationLongitude = coordinates.longitude.toString()
            destinationAddress = coordinates.address
        }
    }

    fun selectRecentDestination(coordinates: Coordinates) {
        destinationLatitude = coordinates.latitude.toString()
        destinationLongitude = coordinates.longitude.toString()
        destinationAddress = coordinates.address
        selectionTarget = if (pickup == null) MapSelectionTarget.Pickup else MapSelectionTarget.Destination
    }

    fun updatePickupLatitude(value: String) { pickupLatitude = value; pickupAddress = null }
    fun updatePickupLongitude(value: String) { pickupLongitude = value; pickupAddress = null }
    fun updateDestinationLatitude(value: String) { destinationLatitude = value; destinationAddress = null }
    fun updateDestinationLongitude(value: String) { destinationLongitude = value; destinationAddress = null }
}

@Composable
internal fun PassengerHome(
    state: AppUiState.PassengerReady,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    mapStyleUrl: String?,
    showManualCoordinateEntry: Boolean,
    onLogout: () -> Unit,
    onRefresh: () -> Unit,
    onRequestCurrentLocation: ((Coordinates?) -> Unit) -> Unit,
    onEstimateRide: (Coordinates, Coordinates) -> Unit,
    onRequestRide: (Coordinates, Coordinates) -> Unit,
    onCancelRide: (String) -> Unit,
    onSelectPassengerRide: (String) -> Unit,
    onUpdatePassengerProfile: (String) -> Unit,
    onSubmitRating: (String, Int, String?) -> Unit,
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit,
    onMarkNotificationRead: (String) -> Unit,
) {
    val form = remember { PassengerTripFormState() }
    var snap by remember { mutableStateOf(TaxiSheetSnap.Peek) }
    var panel by remember { mutableStateOf(PassengerSheetPanel.Ride) }
    var ridePendingCancellation by remember { mutableStateOf<String?>(null) }
    var cameraFocusRequest by remember { mutableIntStateOf(0) }
    var locationRequestInFlight by remember { mutableStateOf(false) }
    var mapUnavailable by remember(mapStyleUrl) { mutableStateOf(false) }

    val trip = form.trip
    val currentEstimate = state.fareEstimate?.takeIf { trip != null && form.estimatedTrip == trip }
    val hasActiveRide = state.activeRide != null
    val mapPickup = if (hasActiveRide) state.pickup else form.pickup
    val mapDestination = if (hasActiveRide) state.destination else form.destination
    val mapRoute = if (hasActiveRide || currentEstimate != null) state.routePlan?.geometry.orEmpty() else emptyList()

    LaunchedEffect(state.activeRide, currentEstimate, panel) {
        snap = when {
            panel != PassengerSheetPanel.Ride -> TaxiSheetSnap.Expanded
            state.activeRide != null || currentEstimate != null -> TaxiSheetSnap.Half
            else -> TaxiSheetSnap.Peek
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(TaxiColors.Surface1)) {
        MapLibreTripMap(
            pickup = mapPickup,
            destination = mapDestination,
            driverLocation = state.lastKnownDriverLocation?.coordinates,
            routeGeometry = mapRoute,
            styleUrl = mapStyleUrl,
            cameraFocusRequest = cameraFocusRequest,
            onMapAvailabilityChanged = { mapUnavailable = !it },
            onCoordinateSelected = { coordinates -> if (!hasActiveRide) form.select(coordinates) },
            modifier = Modifier.fillMaxSize(),
        )
        PassengerToolbar(
            displayName = state.profile?.displayName,
            unreadCount = state.notifications.count { !it.read },
            onAccount = { panel = PassengerSheetPanel.Account },
            onInbox = { panel = PassengerSheetPanel.Inbox },
            modifier = Modifier.align(Alignment.TopCenter).padding(TaxiSpacing.Md),
        )
        if (panel == PassengerSheetPanel.Ride) {
            Column(
                modifier = Modifier.align(Alignment.BottomEnd)
                    .padding(end = TaxiSpacing.Md, bottom = maxHeight * snap.heightFraction + TaxiSpacing.Md),
                horizontalAlignment = Alignment.End,
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
            ) {
                MapFab(
                    label = when {
                        hasActiveRide || mapRoute.isNotEmpty() -> stringResource(Res.string.recenter_trip_route)
                        mapPickup != null || mapDestination != null -> stringResource(Res.string.recenter_selected_places)
                        else -> stringResource(Res.string.recenter_map)
                    },
                    glyph = "⌖",
                    onClick = { cameraFocusRequest += 1 },
                )
                if (hasActiveRide) {
                    MapFab(
                        label = stringResource(Res.string.refresh_ride_and_driver_position),
                        glyph = "↻",
                        onClick = onRefresh,
                    )
                }
                if (!hasActiveRide) {
                    MapFab(
                        label = stringResource(Res.string.use_current_location_pickup),
                        glyph = "◎",
                        enabled = !locationRequestInFlight,
                        loading = locationRequestInFlight,
                        onClick = {
                            if (locationRequestInFlight) return@MapFab
                            locationRequestInFlight = true
                            form.locationMessage = UiMessage(Res.string.requesting_current_location)
                            onRequestCurrentLocation { selected ->
                                locationRequestInFlight = false
                                if (selected == null) {
                                    form.locationMessage = UiMessage(Res.string.passenger_location_unavailable)
                                } else {
                                    form.selectionTarget = MapSelectionTarget.Pickup
                                    form.select(selected)
                                    form.locationMessage = UiMessage(Res.string.passenger_location_selected)
                                    cameraFocusRequest += 1
                                    snap = TaxiSheetSnap.Half
                                }
                            }
                        },
                    )
                }
            }
        }
        TaxiSheet(snap = snap, onSnapChange = { snap = it }) {
            if (mapUnavailable) {
                ToastBanner(stringResource(Res.string.map_detail_unavailable), StatusTone.Warning)
            }
            if (panel != PassengerSheetPanel.Ride) {
                state.activeRide?.let { rideStatus ->
                    StatusPill(
                        stringResource(rideStatus.passengerStatusResource()),
                        rideStatus.passengerStatusTone(),
                    )
                }
            }
            when (panel) {
                PassengerSheetPanel.Ride -> PassengerRideSheet(
                    state = state,
                    pendingAction = pendingAction,
                    form = form,
                    showManualCoordinateEntry = showManualCoordinateEntry || mapUnavailable,
                    currentEstimateAvailable = currentEstimate != null,
                    onEstimateRide = {
                        val selectedTrip = requireNotNull(form.trip)
                        form.estimatedTrip = selectedTrip
                        onEstimateRide(selectedTrip.first, selectedTrip.second)
                    },
                    onRequestRide = {
                        val quotedTrip = requireNotNull(form.estimatedTrip) { "A quote must exist before requesting a ride." }
                        onRequestRide(quotedTrip.first, quotedTrip.second)
                    },
                    onCancelRequested = { state.activeRideId?.let { ridePendingCancellation = it } },
                )
                PassengerSheetPanel.Account -> PassengerAccountSheet(
                    state = state,
                    pendingAction = pendingAction,
                    completedAction = completedAction,
                    onBack = { panel = PassengerSheetPanel.Ride },
                    onLogout = onLogout,
                    onSelectPassengerRide = onSelectPassengerRide,
                    onUpdateProfile = onUpdatePassengerProfile,
                    onSubmitRating = onSubmitRating,
                    onCreateSupportTicket = onCreateSupportTicket,
                )
                PassengerSheetPanel.Inbox -> PassengerInboxSheet(
                    notifications = state.notifications,
                    pendingAction = pendingAction,
                    onBack = { panel = PassengerSheetPanel.Ride },
                    onMarkRead = onMarkNotificationRead,
                )
            }
        }
    }
    ridePendingCancellation?.let { rideId ->
        ConfirmDialog(
            title = stringResource(Res.string.cancel_ride_question),
            body = stringResource(Res.string.cancel_ride_backend_check),
            confirmLabel = stringResource(Res.string.cancel_ride),
            destructive = true,
            onConfirm = {
                ridePendingCancellation = null
                onCancelRide(rideId)
            },
            onCancel = { ridePendingCancellation = null },
        )
    }
}

@Composable
private fun PassengerToolbar(
    displayName: String?,
    unreadCount: Int,
    onAccount: () -> Unit,
    onInbox: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Surface(shape = MaterialTheme.shapes.medium, color = TaxiColors.Surface0, shadowElevation = TaxiSpacing.Xs) {
            TextButton(onClick = onAccount) {
                Text(displayName?.ifBlank { null } ?: stringResource(Res.string.account))
            }
        }
        Surface(shape = MaterialTheme.shapes.medium, color = TaxiColors.Surface0, shadowElevation = TaxiSpacing.Xs) {
            TextButton(onClick = onInbox) {
                Text(
                    if (unreadCount > 0) stringResource(Res.string.inbox_count, unreadCount)
                    else stringResource(Res.string.inbox)
                )
            }
        }
    }
}

@Composable
private fun PassengerRideSheet(
    state: AppUiState.PassengerReady,
    pendingAction: AppAction?,
    form: PassengerTripFormState,
    showManualCoordinateEntry: Boolean,
    currentEstimateAvailable: Boolean,
    onEstimateRide: () -> Unit,
    onRequestRide: () -> Unit,
    onCancelRequested: () -> Unit,
) {
    val rideStatus = state.activeRide
    if (rideStatus != null) {
        val statusLabel = stringResource(rideStatus.passengerStatusResource())
        Text(statusLabel, style = MaterialTheme.typography.titleLarge)
        StatusPill(statusLabel, rideStatus.passengerStatusTone())
        if (rideStatus == RideStatus.REQUESTED || rideStatus == RideStatus.MATCHING) {
            LinearProgressIndicator(
                modifier = Modifier.fillMaxWidth(),
                color = TaxiColors.Accent500,
                trackColor = TaxiColors.Accent100,
            )
            Text(
                stringResource(Res.string.finding_taxi_help),
                style = MaterialTheme.typography.bodyMedium,
                color = TaxiColors.Ink500,
            )
        }
        state.assignedDriver?.let { driver ->
            DriverCard(
                displayName = driver.displayName,
                vehicleDescription = "${driver.vehicle.color} ${driver.vehicle.make} ${driver.vehicle.model}",
                taxiIdentifier = driver.vehicle.taxiIdentifier,
                statusLabel = statusLabel,
                statusTone = rideStatus.passengerStatusTone(),
                modifier = Modifier.fillMaxWidth(),
            )
        }
        state.lastKnownDriverLocation?.let { location ->
            Text(
                stringResource(
                    Res.string.last_known_driver_location_observed,
                    ltrIsolate(location.observedAt),
                ),
                style = MaterialTheme.typography.bodyMedium,
                color = TaxiColors.Ink500,
            )
        }
        state.routePlan?.let { route ->
            Text(
                stringResource(
                    Res.string.route_summary,
                    formatKilometers(route.distanceMeters),
                    formatMinutes(route.durationSeconds),
                )
            )
            route.maneuvers.take(3).forEach { Text(it.instruction, style = MaterialTheme.typography.bodyMedium) }
        }
        if (state.routeUnavailable) {
            ToastBanner(stringResource(Res.string.passenger_route_unavailable_active))
        }
        if (state.activeRideId != null && rideStatus in PASSENGER_CANCELLABLE) {
            TaxiButton(
                stringResource(Res.string.cancel_request),
                onCancelRequested,
                enabled = pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.CANCEL_RIDE, state.activeRideId),
                style = TaxiButtonStyle.Secondary,
            )
        }
        return
    }

    Text(stringResource(Res.string.where_to), style = MaterialTheme.typography.displaySmall)
    if (state.rideHistory.firstOrNull()?.status == RideStatus.UNMATCHED) {
        ToastBanner(stringResource(Res.string.no_drivers_retry_message), StatusTone.Info)
    }
    Text(stringResource(Res.string.pickup_default_help), style = MaterialTheme.typography.bodyMedium, color = TaxiColors.Ink500)
    TaxiSegmentedControl(
        firstLabel = stringResource(Res.string.pickup),
        secondLabel = stringResource(Res.string.destination),
        firstSelected = form.selectionTarget == MapSelectionTarget.Pickup,
        onFirstSelected = { form.selectionTarget = MapSelectionTarget.Pickup },
        onSecondSelected = { form.selectionTarget = MapSelectionTarget.Destination },
    )
    form.locationMessage?.let { ToastBanner(it.resolve()) }
    SelectionSummary(form)
    RecentDestinationSection(state.rideHistory) { form.selectRecentDestination(it) }
    if (showManualCoordinateEntry) CoordinateFields(form)
    if (!currentEstimateAvailable) {
        TaxiButton(
            stringResource(Res.string.review_fare),
            onEstimateRide,
            enabled = form.trip != null && pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.ESTIMATE_RIDE),
        )
    } else {
        state.fareEstimate?.let { estimate ->
            FareBlock(estimate.amount, estimate.currency, estimate.pricingRuleVersion, finalFare = false)
        }
        state.routePlan?.let { route ->
            Text(
                stringResource(
                    Res.string.route_summary_prefixed,
                    formatKilometers(route.distanceMeters),
                    formatMinutes(route.durationSeconds),
                )
            )
            route.maneuvers.take(3).forEach { Text(it.instruction, style = MaterialTheme.typography.bodyMedium) }
        }
        if (state.routeUnavailable) {
            ToastBanner(stringResource(Res.string.passenger_route_unavailable_quote))
        }
        Text(stringResource(Res.string.payment_method), style = MaterialTheme.typography.titleMedium)
        PaymentMethodCard(
            label = stringResource(Res.string.payment_method_cash),
            detail = stringResource(Res.string.cash_payment_detail),
            selected = true,
        )
        TaxiButton(
            stringResource(Res.string.request_taxi),
            onRequestRide,
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.REQUEST_RIDE),
        )
    }
}

@Composable
private fun SelectionSummary(form: PassengerTripFormState) {
    LocationSelectionField(
        label = stringResource(Res.string.pickup),
        value = stringResource(
            if (form.pickup == null) Res.string.pickup_select_on_map
            else Res.string.pickup_selected_on_map,
        ),
        selected = form.selectionTarget == MapSelectionTarget.Pickup,
        onClick = { form.selectionTarget = MapSelectionTarget.Pickup },
    )
    LocationSelectionField(
        label = stringResource(Res.string.destination),
        value = stringResource(
            if (form.destination == null) Res.string.destination_select_on_map
            else Res.string.destination_selected_on_map,
        ),
        selected = form.selectionTarget == MapSelectionTarget.Destination,
        onClick = { form.selectionTarget = MapSelectionTarget.Destination },
    )
}

@Composable
private fun CoordinateFields(form: PassengerTripFormState) {
    TaxiTextField(form.pickupLatitude, form::updatePickupLatitude, stringResource(Res.string.pickup_latitude), keyboardType = KeyboardType.Decimal)
    TaxiTextField(form.pickupLongitude, form::updatePickupLongitude, stringResource(Res.string.pickup_longitude), keyboardType = KeyboardType.Decimal)
    TaxiTextField(form.destinationLatitude, form::updateDestinationLatitude, stringResource(Res.string.destination_latitude), keyboardType = KeyboardType.Decimal)
    TaxiTextField(form.destinationLongitude, form::updateDestinationLongitude, stringResource(Res.string.destination_longitude), keyboardType = KeyboardType.Decimal)
}

@Composable
private fun RecentDestinationSection(
    rides: List<org.example.taximobile.domain.rides.RideSummary>,
    onSelect: (Coordinates) -> Unit,
) {
    val destinations = recentPassengerDestinations(rides)
    if (destinations.isEmpty()) return
    Text(stringResource(Res.string.recent_destinations), style = MaterialTheme.typography.titleMedium)
    destinations.forEach { destination ->
        val fallback = ltrIsolate("${destination.latitude}, ${destination.longitude}")
        TaxiButton(
            label = destination.address?.trim()?.takeIf(String::isNotEmpty) ?: fallback,
            onClick = { onSelect(destination) },
            style = TaxiButtonStyle.Secondary,
        )
    }
}

@Composable
private fun PassengerAccountSheet(
    state: AppUiState.PassengerReady,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    onBack: () -> Unit,
    onLogout: () -> Unit,
    onSelectPassengerRide: (String) -> Unit,
    onUpdateProfile: (String) -> Unit,
    onSubmitRating: (String, Int, String?) -> Unit,
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit,
) {
    TaxiButton(stringResource(Res.string.back_to_ride), onBack, style = TaxiButtonStyle.Tertiary)
    Text(stringResource(Res.string.account), style = MaterialTheme.typography.displaySmall)
    state.profile?.let { PassengerProfileSection(it.displayName, pendingAction, onUpdateProfile) }
    state.selectedHistoryRide?.let { ride ->
        PassengerRideHistoryDetail(ride, state.selectedHistoryReceipt)
    } ?: state.latestCompletedReceipt?.let { receipt ->
        PassengerReceipt(receipt)
    }
    if (completedAction?.action?.kind == AppActionKind.SUBMIT_RATING) {
        SuccessConfirmation(
            stringResource(Res.string.rating_submitted_confirmation),
            completedAction.sequence,
        )
    }
    state.rateableRideId?.let { RideRatingSection(it, pendingAction, onSubmitRating) }
    PassengerHistorySection(state, pendingAction, onSelectPassengerRide)
    SupportTicketSection(
        state.supportTickets,
        state.activeRideId,
        pendingAction,
        completedAction,
        onCreateSupportTicket,
    )
    TaxiButton(
        stringResource(Res.string.sign_out),
        onLogout,
        enabled = pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.LOGOUT),
        style = TaxiButtonStyle.Tertiary,
    )
}

@Composable
private fun PassengerProfileSection(
    displayName: String,
    pendingAction: AppAction?,
    onUpdate: (String) -> Unit,
) {
    var editedName by remember(displayName) { mutableStateOf(displayName) }
    Text(stringResource(Res.string.profile), style = MaterialTheme.typography.titleMedium)
    TaxiTextField(editedName, { editedName = it }, stringResource(Res.string.display_name))
    TaxiButton(
        stringResource(Res.string.save_profile),
        onClick = { onUpdate(editedName.trim()) },
        enabled = editedName.trim().isNotBlank() && editedName.trim() != displayName && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.UPDATE_PASSENGER_PROFILE),
        style = TaxiButtonStyle.Secondary,
    )
}

@Composable
private fun PassengerHistorySection(
    state: AppUiState.PassengerReady,
    pendingAction: AppAction?,
    onSelect: (String) -> Unit,
) {
    Text(stringResource(Res.string.ride_history), style = MaterialTheme.typography.titleMedium)
    if (state.rideHistory.isEmpty()) {
        EmptyState(
            title = stringResource(Res.string.no_trips_title),
            body = stringResource(Res.string.no_passenger_trips_body),
        )
        return
    }
    state.rideHistory.take(10).forEach { ride ->
        TaxiButton(
            label = stringResource(
                Res.string.ride_history_item,
                stringResource(ride.status.passengerStatusResource()),
                ltrIsolate(ride.id.take(8)),
            ),
            onClick = { onSelect(ride.id) },
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.LOAD_PASSENGER_RIDE, ride.id),
            style = TaxiButtonStyle.Tertiary,
        )
    }
}

@Composable
private fun PassengerRideHistoryDetail(
    ride: org.example.taximobile.domain.rides.RideSummary,
    receipt: org.example.taximobile.domain.rides.RideReceipt?,
) {
    Text(stringResource(Res.string.ride_details), style = MaterialTheme.typography.titleMedium)
    StatusPill(
        stringResource(ride.status.passengerStatusResource()),
        ride.status.passengerStatusTone(),
    )
    Text(stringResource(Res.string.ride_identifier, ltrIsolate(ride.id)))
    ride.pickup?.let {
        Text(stringResource(Res.string.ride_location_line, stringResource(Res.string.pickup), historyLocationLabel(it)))
    }
    ride.destination?.let {
        Text(stringResource(Res.string.ride_location_line, stringResource(Res.string.destination), historyLocationLabel(it)))
    }
    receipt?.let { PassengerReceipt(it) }
}

@Composable
private fun PassengerReceipt(receipt: org.example.taximobile.domain.rides.RideReceipt) {
    Text(stringResource(Res.string.receipt), style = MaterialTheme.typography.titleMedium)
    FareBlock(
        amount = receipt.fare.amount,
        currency = receipt.fare.currency,
        pricingRuleVersion = receipt.fare.pricingRuleVersion,
        finalFare = true,
        breakdown = receipt.fare.components.map {
            FareBreakdownRow(fareComponentLabel(it.code), "${it.amount} ${receipt.fare.currency}")
        },
    )
    StatusPill(
        label = stringResource(
            Res.string.support_ticket_summary,
            paymentMethodLabel(receipt.paymentMethod),
            paymentStatusLabel(receipt.paymentStatus),
        ),
        tone = if (receipt.paymentStatus == "COMPLETED") StatusTone.Success else StatusTone.Warning,
    )
    if (receipt.paymentMethod == "CASH" && receipt.paymentStatus == "PENDING") {
        Text(stringResource(Res.string.cash_settlement_pending))
    }
}

private fun historyLocationLabel(location: Coordinates): String =
    location.address?.trim()?.takeIf(String::isNotEmpty)
        ?: ltrIsolate("${location.latitude}, ${location.longitude}")

@Composable
private fun RideRatingSection(
    rideId: String,
    pendingAction: AppAction?,
    onSubmit: (String, Int, String?) -> Unit,
) {
    var score by remember { mutableIntStateOf(5) }
    var comment by remember { mutableStateOf("") }
    Text(stringResource(Res.string.completed_ride_rating_question), style = MaterialTheme.typography.titleMedium)
    RatingStars(
        value = score,
        onValueChange = { score = it },
        scoreDescriptions = (1..5).map { stringResource(Res.string.rating_star_value, it) },
        enabled = pendingAction == null,
    )
    OutlinedTextField(
        comment,
        { comment = it },
        Modifier.fillMaxWidth(),
        label = { Text(stringResource(Res.string.comment_optional)) },
    )
    TaxiButton(
        stringResource(Res.string.submit_rating),
        onClick = { onSubmit(rideId, score, comment.ifBlank { null }) },
        enabled = pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.SUBMIT_RATING, rideId),
    )
}

@Composable
private fun PassengerInboxSheet(
    notifications: List<AppNotification>,
    pendingAction: AppAction?,
    onBack: () -> Unit,
    onMarkRead: (String) -> Unit,
) {
    TaxiButton(stringResource(Res.string.back_to_ride), onBack, style = TaxiButtonStyle.Tertiary)
    Text(stringResource(Res.string.inbox), style = MaterialTheme.typography.displaySmall)
    NotificationInboxSection(notifications, pendingAction, onMarkRead)
}

@Composable
private fun fareComponentLabel(code: String): String = stringResource(
    if (code == "BASE_FARE") Res.string.fare_component_base else Res.string.fare_component_other
)

@Composable
private fun paymentMethodLabel(method: String): String = stringResource(
    when (method) {
        "CASH" -> Res.string.payment_method_cash
        "CARD" -> Res.string.payment_method_card
        "MOBILE_PAYMENT" -> Res.string.payment_method_mobile
        else -> Res.string.payment_method_unknown
    }
)

@Composable
private fun paymentStatusLabel(status: String): String = stringResource(
    when (status) {
        "PENDING" -> Res.string.payment_status_pending
        "PROCESSING" -> Res.string.payment_status_processing
        "COMPLETED" -> Res.string.payment_status_completed
        "FAILED" -> Res.string.payment_status_failed
        "CANCELLED" -> Res.string.payment_status_cancelled
        "DISPUTED" -> Res.string.payment_status_disputed
        else -> Res.string.payment_status_unknown
    }
)

internal fun RideStatus.passengerStatusTone(): StatusTone = when (this) {
    RideStatus.REQUESTED, RideStatus.MATCHING -> StatusTone.Accent
    RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS -> StatusTone.Info
    RideStatus.COMPLETED -> StatusTone.Success
    RideStatus.CANCELLED -> StatusTone.Neutral
    RideStatus.UNMATCHED -> StatusTone.Info
}

private val PASSENGER_CANCELLABLE = setOf(
    RideStatus.REQUESTED,
    RideStatus.MATCHING,
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_EN_ROUTE,
    RideStatus.DRIVER_ARRIVED,
)
