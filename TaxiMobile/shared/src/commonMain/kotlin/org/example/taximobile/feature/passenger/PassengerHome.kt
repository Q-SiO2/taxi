package org.example.taximobile.feature.passenger

import androidx.compose.foundation.background
import androidx.compose.foundation.text.selection.SelectionContainer
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
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.testTag
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.places.PlaceResult
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RidePaymentMethod
import org.example.taximobile.domain.rides.RideCoordinationCode
import org.example.taximobile.domain.rides.RideCoordinationSenderRole
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideServiceType
import org.example.taximobile.domain.rides.PublishedFixedRouteDirection
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.domain.scheduling.ScheduledCancellationTerms
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.rides.RideCoordinationActions
import org.example.taximobile.feature.rides.RideLatestCoordinationMessage
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionCompletion
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.NotificationInboxSection
import org.example.taximobile.feature.app.SafetyReportSection
import org.example.taximobile.feature.app.SupportTicketSection
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.app.formatKilometers
import org.example.taximobile.feature.app.formatMinutes
import org.example.taximobile.feature.app.passengerStatusResource
import org.example.taximobile.feature.app.validCoordinates
import org.example.taximobile.feature.account.AccountSecuritySection
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

private enum class PassengerSheetPanel { Ride, FixedRoutes, Scheduled, Safety, Account, Inbox }
internal enum class MapSelectionTarget { Pickup, Destination }

internal class PassengerTripFormState {
    var pickupLatitude by mutableStateOf("")
    var pickupLongitude by mutableStateOf("")
    var destinationLatitude by mutableStateOf("")
    var destinationLongitude by mutableStateOf("")
    var pickupAddress by mutableStateOf<String?>(null)
    var destinationAddress by mutableStateOf<String?>(null)
    var estimatedTrip by mutableStateOf<Pair<Coordinates, Coordinates>?>(null)
    var selectedPaymentMethod by mutableStateOf(RidePaymentMethod.CASH)
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

    fun matchesSelectedPoint(target: MapSelectionTarget, coordinate: Coordinates): Boolean {
        val current = if (target == MapSelectionTarget.Pickup) pickup else destination
        return current != null && current.latitude == coordinate.latitude && current.longitude == coordinate.longitude
    }

    /** Reverse lookup labels an existing selection; it must never move the point. */
    fun applyReverseAddress(target: MapSelectionTarget, place: PlaceResult): Boolean {
        if (!matchesSelectedPoint(target, place.coordinate)) return false
        val selected = place.selectedCoordinates()
        if (target == MapSelectionTarget.Pickup) {
            pickupAddress = selected.address
        } else {
            destinationAddress = selected.address
        }
        return true
    }
}

private data class PendingReverseSelection(
    val target: MapSelectionTarget,
    val cityId: String,
    val coordinate: Coordinates,
)

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
    onSearchPlaces: (String, String) -> Unit,
    onReversePlace: (String, Coordinates) -> Unit,
    onEstimateRide: (Coordinates, Coordinates) -> Unit,
    onRequestRide: (Coordinates, Coordinates, RidePaymentMethod) -> Unit,
    onLoadFixedRoutes: (String) -> Unit,
    onEstimateFixedRoute: (String) -> Unit,
    onRequestFixedRoute: (String, RidePaymentMethod) -> Unit,
    onEstimateScheduledPointToPoint: (String, String?, Coordinates, Coordinates) -> Unit,
    onEstimateScheduledFixedRoute: (String, String) -> Unit,
    onSchedulePointToPoint: (String, String?, Coordinates, Coordinates, String?, ScheduledBookingEstimate) -> Unit,
    onScheduleFixedRoute: (String, String, String?, ScheduledBookingEstimate) -> Unit,
    onCancelScheduledBooking: (String) -> Unit,
    onSubmitManualTransfer: (String, String?) -> Unit,
    onCancelRide: (String) -> Unit,
    onSendRideCoordination: (String, RideCoordinationCode) -> Unit,
    onSelectPassengerRide: (String) -> Unit,
    onUpdatePassengerProfile: (String) -> Unit,
    onSubmitRating: (String, Int, String?) -> Unit,
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit,
    onCreateSafetyReport: (String, SafetyCategory, String) -> Unit,
    onMarkNotificationRead: (String) -> Unit,
    onLoadAccountSecurity: () -> Unit,
    onCreateRecoveryCodes: (String) -> Unit,
    onAcknowledgeRecoveryCodes: () -> Unit,
    onRevokeAccountSession: (String) -> Unit,
    onChangeAccountPassword: (String, String) -> Unit,
) {
    val form = remember { PassengerTripFormState() }
    var snap by remember { mutableStateOf(TaxiSheetSnap.Peek) }
    var panel by remember { mutableStateOf(PassengerSheetPanel.Ride) }
    var ridePendingCancellation by remember { mutableStateOf<String?>(null) }
    var cameraFocusRequest by remember { mutableIntStateOf(0) }
    var locationRequestInFlight by remember { mutableStateOf(false) }
    var mapUnavailable by remember(mapStyleUrl) { mutableStateOf(false) }
    var selectedPlaceCityId by remember { mutableStateOf<String?>(null) }
    var reverseSelection by remember { mutableStateOf<PendingReverseSelection?>(null) }
    var selectedFixedDirectionId by remember(state.fixedRouteCatalog?.city?.id) {
        mutableStateOf(state.selectedFixedRouteDirectionId)
    }

    val trip = form.trip
    val currentEstimate = state.fareEstimate?.takeIf { trip != null && form.estimatedTrip == trip }
    val hasActiveRide = state.activeRide != null
    val selectedFixedDirection = state.fixedRouteCatalog?.directions?.firstOrNull {
        it.id == selectedFixedDirectionId
    }
    val fixedEstimate = state.fareEstimate?.takeIf {
        it.serviceType == RideServiceType.FIXED_ROUTE &&
            state.selectedFixedRouteDirectionId == selectedFixedDirectionId
    }
    val mapPickup = when {
        hasActiveRide -> state.pickup
        panel == PassengerSheetPanel.FixedRoutes -> selectedFixedDirection?.start
        else -> form.pickup
    }
    val mapDestination = when {
        hasActiveRide -> state.destination
        panel == PassengerSheetPanel.FixedRoutes -> selectedFixedDirection?.finish
        else -> form.destination
    }
    val mapRoute = when {
        hasActiveRide -> state.routePlan?.geometry.orEmpty()
        panel == PassengerSheetPanel.FixedRoutes -> selectedFixedDirection?.geometry.orEmpty()
        currentEstimate != null -> state.routePlan?.geometry.orEmpty()
        else -> emptyList()
    }
    val defaultPlaceCityId = state.serviceCities.firstOrNull { it.bookingAvailable }?.id
    val activePlaceCityId = selectedPlaceCityId?.takeIf { selected ->
        state.serviceCities.any { it.id == selected && it.bookingAvailable }
    } ?: defaultPlaceCityId

    LaunchedEffect(defaultPlaceCityId, state.serviceCities.map { it.id to it.bookingAvailable }) {
        if (selectedPlaceCityId == null || activePlaceCityId != selectedPlaceCityId) {
            selectedPlaceCityId = defaultPlaceCityId
        }
    }

    LaunchedEffect(state.placeDiscovery.revision) {
        val request = reverseSelection ?: return@LaunchedEffect
        val reverse = state.placeDiscovery.reverse ?: return@LaunchedEffect
        reverseSelection = null
        if (
            hasActiveRide || request.cityId != activePlaceCityId ||
            reverse.cityId != request.cityId ||
            !form.matchesSelectedPoint(request.target, request.coordinate)
        ) return@LaunchedEffect
        val target = request.target
        val place = reverse.item
        if (place == null) {
            form.locationMessage = UiMessage(Res.string.address_lookup_no_result)
        } else {
            if (!form.applyReverseAddress(target, place)) return@LaunchedEffect
            form.locationMessage = UiMessage(
                if (target == MapSelectionTarget.Pickup && !place.pickupServiceable) {
                    Res.string.pickup_outside_service_area
                } else {
                    Res.string.address_lookup_completed
                }
            )
        }
    }

    LaunchedEffect(currentEstimate?.paymentMethods) {
        val methods = currentEstimate?.paymentMethods.orEmpty()
        if (methods.isNotEmpty() && form.selectedPaymentMethod !in methods) {
            form.selectedPaymentMethod = methods.first()
        }
    }

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
            onCoordinateSelected = { coordinates ->
                if (!hasActiveRide && panel == PassengerSheetPanel.Ride) form.select(coordinates)
            },
            modifier = Modifier.fillMaxSize(),
        )
        PassengerToolbar(
            displayName = state.profile?.displayName,
            unreadCount = state.notifications.count { !it.read },
            onAccount = { panel = PassengerSheetPanel.Account },
            onSafety = { panel = PassengerSheetPanel.Safety },
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
                    selectedPlaceCityId = activePlaceCityId,
                    currentEstimateAvailable = currentEstimate != null,
                    onSelectPlaceCity = { selectedPlaceCityId = it },
                    onSearchPlaces = onSearchPlaces,
                    onSelectPlaceResult = { result ->
                        if (
                            form.selectionTarget == MapSelectionTarget.Pickup &&
                            !result.pickupServiceable
                        ) {
                            form.locationMessage = UiMessage(Res.string.pickup_outside_service_area)
                        } else {
                            form.select(result.selectedCoordinates())
                            form.locationMessage = null
                            cameraFocusRequest += 1
                        }
                    },
                    onReverseSelected = { target, coordinate ->
                        val cityId = activePlaceCityId
                        if (cityId != null) {
                            reverseSelection = PendingReverseSelection(target, cityId, coordinate)
                            onReversePlace(cityId, coordinate)
                        }
                    },
                    onEstimateRide = {
                        val selectedTrip = requireNotNull(form.trip)
                        form.estimatedTrip = selectedTrip
                        onEstimateRide(selectedTrip.first, selectedTrip.second)
                    },
                    onRequestRide = {
                        val quotedTrip = requireNotNull(form.estimatedTrip) { "A quote must exist before requesting a ride." }
                        onRequestRide(
                            quotedTrip.first,
                            quotedTrip.second,
                            form.selectedPaymentMethod,
                        )
                    },
                    onBrowseFixedRoutes = {
                        panel = PassengerSheetPanel.FixedRoutes
                        snap = TaxiSheetSnap.Expanded
                    },
                    onOpenScheduled = {
                        panel = PassengerSheetPanel.Scheduled
                        snap = TaxiSheetSnap.Expanded
                    },
                    onCancelRequested = { state.activeRideId?.let { ridePendingCancellation = it } },
                    onSendRideCoordination = onSendRideCoordination,
                )
                PassengerSheetPanel.FixedRoutes -> PassengerFixedRoutesSheet(
                    state = state,
                    pendingAction = pendingAction,
                    selectedDirectionId = selectedFixedDirectionId,
                    selectedPaymentMethod = form.selectedPaymentMethod,
                    onBack = { panel = PassengerSheetPanel.Ride },
                    onSelectCity = {
                        selectedFixedDirectionId = null
                        onLoadFixedRoutes(it)
                    },
                    onSelectDirection = {
                        selectedFixedDirectionId = it
                        cameraFocusRequest += 1
                    },
                    onEstimate = onEstimateFixedRoute,
                    onPaymentMethod = { form.selectedPaymentMethod = it },
                    onRequest = { directionId ->
                        onRequestFixedRoute(directionId, form.selectedPaymentMethod)
                    },
                )
                PassengerSheetPanel.Scheduled -> PassengerScheduledSheet(
                    state = state,
                    pendingAction = pendingAction,
                    form = form,
                    selectedFixedDirectionId = selectedFixedDirectionId,
                    onBack = { panel = PassengerSheetPanel.Ride },
                    onEstimatePointToPoint = onEstimateScheduledPointToPoint,
                    onEstimateFixedRoute = onEstimateScheduledFixedRoute,
                    onSchedulePointToPoint = onSchedulePointToPoint,
                    onScheduleFixedRoute = onScheduleFixedRoute,
                    onCancel = onCancelScheduledBooking,
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
                    onSubmitManualTransfer = onSubmitManualTransfer,
                    onCreateSupportTicket = onCreateSupportTicket,
                    onLoadAccountSecurity = onLoadAccountSecurity,
                    onCreateRecoveryCodes = onCreateRecoveryCodes,
                    onAcknowledgeRecoveryCodes = onAcknowledgeRecoveryCodes,
                    onRevokeAccountSession = onRevokeAccountSession,
                    onChangeAccountPassword = onChangeAccountPassword,
                )
                PassengerSheetPanel.Safety -> PassengerSafetySheet(
                    state = state,
                    pendingAction = pendingAction,
                    completedAction = completedAction,
                    onBack = { panel = PassengerSheetPanel.Ride },
                    onCreateSafetyReport = onCreateSafetyReport,
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
    onSafety: () -> Unit,
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
            TextButton(onClick = onSafety) {
                Text(stringResource(Res.string.safety_reports_title))
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
    selectedPlaceCityId: String?,
    currentEstimateAvailable: Boolean,
    onSelectPlaceCity: (String) -> Unit,
    onSearchPlaces: (String, String) -> Unit,
    onSelectPlaceResult: (PlaceResult) -> Unit,
    onReverseSelected: (MapSelectionTarget, Coordinates) -> Unit,
    onEstimateRide: () -> Unit,
    onRequestRide: () -> Unit,
    onBrowseFixedRoutes: () -> Unit,
    onOpenScheduled: () -> Unit,
    onCancelRequested: () -> Unit,
    onSendRideCoordination: (String, RideCoordinationCode) -> Unit,
) {
    var placeSearchExpanded by remember { mutableStateOf(false) }
    val rideStatus = state.activeRide
    if (rideStatus != null) {
        val statusLabel = stringResource(rideStatus.passengerStatusResource())
        Text(statusLabel, style = MaterialTheme.typography.titleLarge)
        StatusPill(statusLabel, rideStatus.passengerStatusTone())
        state.activeFixedRoute?.let { route ->
            val language = Locale.current.language
            Text(stringResource(Res.string.service_type_fixed_route), style = MaterialTheme.typography.labelLarge)
            Text(
                stringResource(
                    Res.string.route_direction_summary,
                    route.startName.preferred(language),
                    route.finishName.preferred(language),
                ),
                style = MaterialTheme.typography.titleMedium,
            )
        }
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
        RideLatestCoordinationMessage(state.latestCoordinationMessage)
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
        state.activeRideId?.let { rideId ->
            if (rideStatus in PARTICIPANT_COORDINATION_STATUSES) {
                RideCoordinationActions(
                    rideId = rideId,
                    senderRole = RideCoordinationSenderRole.PASSENGER,
                    pendingAction = pendingAction,
                    onSend = onSendRideCoordination,
                )
            }
        }
        return
    }

    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(stringResource(Res.string.where_to), style = MaterialTheme.typography.displaySmall)
            Row {
                    TextButton(onClick = onOpenScheduled, enabled = pendingAction == null) {
                        Text(stringResource(Res.string.scheduled_nav))
                }
                TextButton(
                    onClick = onBrowseFixedRoutes,
                    enabled = pendingAction == null,
                ) {
                    Text(stringResource(Res.string.fixed_routes_browse))
                }
            }
        }
        Text(
            stringResource(Res.string.pickup_default_help),
            style = MaterialTheme.typography.bodyMedium,
            color = TaxiColors.Ink500,
        )
    }
    if (state.rideHistory.firstOrNull()?.status == RideStatus.UNMATCHED) {
        ToastBanner(stringResource(Res.string.no_drivers_retry_message), StatusTone.Info)
    }
    TaxiSegmentedControl(
        firstLabel = stringResource(Res.string.pickup),
        secondLabel = stringResource(Res.string.destination),
        firstSelected = form.selectionTarget == MapSelectionTarget.Pickup,
        onFirstSelected = { form.selectionTarget = MapSelectionTarget.Pickup },
        onSecondSelected = { form.selectionTarget = MapSelectionTarget.Destination },
    )
    form.locationMessage?.let { ToastBanner(it.resolve()) }
    SelectionSummary(form, selectedPlaceCityId, pendingAction, onReverseSelected)
    RecentDestinationSection(state.rideHistory) { form.selectRecentDestination(it) }
    TaxiButton(
        label = stringResource(
            if (placeSearchExpanded) Res.string.place_search_close else Res.string.place_search_title
        ),
        onClick = { placeSearchExpanded = !placeSearchExpanded },
        enabled = pendingAction == null,
        style = TaxiButtonStyle.Secondary,
    )
    if (placeSearchExpanded) {
        PlaceDiscoverySection(
            cities = state.serviceCities,
            selectedCityId = selectedPlaceCityId,
            discovery = state.placeDiscovery,
            pickupTarget = form.selectionTarget == MapSelectionTarget.Pickup,
            pendingAction = pendingAction,
            onSelectCity = onSelectPlaceCity,
            onSearch = onSearchPlaces,
            onSelectResult = {
                onSelectPlaceResult(it)
                placeSearchExpanded = false
            },
        )
    }
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
            FareBlock(
                amount = estimate.amount,
                currency = estimate.currency,
                pricingRuleVersion = estimate.pricingRuleVersion,
                finalFare = false,
                breakdown = estimate.economics?.let { economics ->
                    buildList {
                        add(
                            FareBreakdownRow(
                                stringResource(Res.string.fare_component_transport),
                                "${economics.transportFare} ${estimate.currency}",
                            )
                        )
                        if (economics.schedulingSurcharge.hasNonZeroDigit()) {
                            add(
                                FareBreakdownRow(
                                    stringResource(Res.string.fare_component_scheduling_surcharge),
                                    "${economics.schedulingSurcharge} ${estimate.currency}",
                                )
                            )
                        }
                        if (
                            economics.operatorFeeFundingMode == "PASSENGER_SURCHARGE" &&
                            economics.operatorServiceFee.hasNonZeroDigit()
                        ) {
                            add(
                                FareBreakdownRow(
                                    stringResource(Res.string.fare_component_operator_service_fee),
                                    "${economics.operatorServiceFee} ${estimate.currency}",
                                )
                            )
                        }
                    }
                }.orEmpty(),
            )
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
        val methods = state.fareEstimate?.paymentMethods.orEmpty()
            .ifEmpty { listOf(RidePaymentMethod.CASH) }
        methods.forEach { method ->
            PaymentMethodCard(
                label = stringResource(
                    if (method == RidePaymentMethod.CASH) {
                        Res.string.payment_method_cash
                    } else {
                        Res.string.payment_method_manual_transfer
                    }
                ),
                detail = stringResource(
                    if (method == RidePaymentMethod.CASH) {
                        Res.string.cash_payment_detail
                    } else {
                        Res.string.manual_transfer_payment_detail
                    }
                ),
                selected = form.selectedPaymentMethod == method,
                onClick = { form.selectedPaymentMethod = method },
            )
        }
        TaxiButton(
            stringResource(Res.string.request_taxi),
            onRequestRide,
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.REQUEST_RIDE),
        )
    }
}

@Composable
private fun PassengerScheduledSheet(
    state: AppUiState.PassengerReady,
    pendingAction: AppAction?,
    form: PassengerTripFormState,
    selectedFixedDirectionId: String?,
    onBack: () -> Unit,
    onEstimatePointToPoint: (String, String?, Coordinates, Coordinates) -> Unit,
    onEstimateFixedRoute: (String, String) -> Unit,
    onSchedulePointToPoint: (String, String?, Coordinates, Coordinates, String?, ScheduledBookingEstimate) -> Unit,
    onScheduleFixedRoute: (String, String, String?, ScheduledBookingEstimate) -> Unit,
    onCancel: (String) -> Unit,
) {
    var scheduledFor by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var useFixedRoute by remember { mutableStateOf(false) }
    var cancelCandidate by remember { mutableStateOf<String?>(null) }
    val selectedRoute = state.fixedRouteCatalog?.directions?.firstOrNull {
        it.id == selectedFixedDirectionId && it.scheduledBookingEnabled
    }
    val requestKey = if (useFixedRoute) {
        "FIXED|${selectedRoute?.id}|${scheduledFor.trim()}"
    } else {
        "POINT|${form.trip}|${scheduledFor.trim()}|${state.serviceCities.firstOrNull()?.id}"
    }
    var reviewedRequestKey by remember { mutableStateOf<String?>(null) }
    val reviewedEstimate = state.scheduledBookingEstimate?.takeIf { reviewedRequestKey == requestKey }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(stringResource(Res.string.scheduled_title), style = MaterialTheme.typography.headlineSmall)
        TextButton(onClick = onBack) { Text(stringResource(Res.string.scheduled_back_to_ride)) }
    }
    Text(
        stringResource(Res.string.scheduled_passenger_disclaimer),
        color = TaxiColors.Ink500,
        style = MaterialTheme.typography.bodyMedium,
    )
    TaxiSegmentedControl(
        firstLabel = stringResource(Res.string.scheduled_point_to_point),
        secondLabel = stringResource(Res.string.scheduled_fixed_route),
        firstSelected = !useFixedRoute,
        onFirstSelected = { useFixedRoute = false },
        onSecondSelected = { useFixedRoute = true },
    )
    OutlinedTextField(
        value = scheduledFor,
        onValueChange = { scheduledFor = it.take(40) },
        modifier = Modifier.fillMaxWidth(),
        label = { Text(stringResource(Res.string.scheduled_pickup_time)) },
        supportingText = { Text(stringResource(Res.string.scheduled_pickup_example)) },
        singleLine = true,
    )
    OutlinedTextField(
        value = note,
        onValueChange = { note = it.take(1000) },
        modifier = Modifier.fillMaxWidth(),
        label = { Text(stringResource(Res.string.scheduled_driver_note)) },
        minLines = 2,
    )
    if (useFixedRoute) {
        Text(
            selectedRoute?.let { route ->
                stringResource(
                    Res.string.scheduled_route_summary,
                    route.startName.preferred(Locale.current.language),
                    route.finishName.preferred(Locale.current.language),
                    route.flatFare,
                    route.currency,
                )
            } ?: stringResource(Res.string.scheduled_choose_fixed_route),
            color = if (selectedRoute == null) TaxiColors.Warning600 else TaxiColors.Ink700,
        )
    } else {
        val trip = form.trip
        Text(
            if (trip == null) stringResource(Res.string.scheduled_choose_points)
            else stringResource(Res.string.scheduled_points_ready),
            color = if (trip == null) TaxiColors.Warning600 else TaxiColors.Ink700,
        )
    }
    Text(stringResource(Res.string.scheduled_cash_notice), color = TaxiColors.Ink500)
    TaxiButton(
        label = stringResource(Res.string.scheduled_review_price),
        onClick = {
            reviewedRequestKey = requestKey
            if (useFixedRoute) {
                selectedRoute?.let { onEstimateFixedRoute(scheduledFor.trim(), it.id) }
            } else {
                form.trip?.let { (pickup, destination) ->
                    onEstimatePointToPoint(
                        scheduledFor.trim(),
                        state.serviceCities.firstOrNull()?.id,
                        pickup,
                        destination,
                    )
                }
            }
        },
        enabled = scheduledFor.hasExplicitTimezone() &&
            (if (useFixedRoute) selectedRoute != null else form.trip != null) && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.ESTIMATE_SCHEDULED_BOOKING),
    )
    reviewedEstimate?.let { estimate ->
        Text(stringResource(Res.string.scheduled_review_title), style = MaterialTheme.typography.titleLarge)
        Text(stringResource(Res.string.scheduled_location_summary, estimate.pickup.address ?: stringResource(Res.string.pickup), estimate.destination.address ?: stringResource(Res.string.destination)))
        FareBlock(
            amount = estimate.economics.passengerTotal,
            currency = estimate.economics.currency,
            pricingRuleVersion = estimate.economics.pricingRuleVersion,
            finalFare = false,
            breakdown = listOf(
                FareBreakdownRow(stringResource(Res.string.fare_component_transport), "${estimate.economics.transportFare} ${estimate.economics.currency}"),
                FareBreakdownRow(stringResource(Res.string.fare_component_scheduling_surcharge), "${estimate.economics.schedulingSurcharge} ${estimate.economics.currency}"),
                FareBreakdownRow(stringResource(Res.string.fare_component_operator_service_fee), "${estimate.economics.operatorServiceFee} ${estimate.economics.currency}"),
            ),
        )
        Text(estimate.cancellationTerms.localizedSummary(), color = TaxiColors.Ink500)
        Text(stringResource(Res.string.scheduled_confirm_notice), color = TaxiColors.Warning600)
        TaxiButton(
            label = stringResource(Res.string.scheduled_confirm),
            onClick = {
                if (useFixedRoute) {
                    selectedRoute?.let { onScheduleFixedRoute(scheduledFor.trim(), it.id, note.ifBlank { null }, estimate) }
                } else {
                    form.trip?.let { (pickup, destination) ->
                        onSchedulePointToPoint(
                            scheduledFor.trim(),
                            state.serviceCities.firstOrNull()?.id,
                            pickup,
                            destination,
                            note.ifBlank { null },
                            estimate,
                        )
                    }
                }
            },
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.CREATE_SCHEDULED_BOOKING),
        )
    }
    Text(stringResource(Res.string.scheduled_upcoming), style = MaterialTheme.typography.titleLarge)
    if (state.scheduledBookings.isEmpty()) {
        EmptyState(stringResource(Res.string.scheduled_empty), stringResource(Res.string.scheduled_empty_help))
    }
    state.scheduledBookings.forEach { booking ->
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = MaterialTheme.shapes.medium,
            color = TaxiColors.Surface0,
            shadowElevation = TaxiSpacing.Xs,
        ) {
            Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(booking.scheduledFor, style = MaterialTheme.typography.titleMedium)
                    StatusPill(booking.status.replace('_', ' '), scheduledStatusTone(booking.status))
                }
                Text(stringResource(Res.string.scheduled_location_summary, booking.pickup.address ?: stringResource(Res.string.pickup), booking.destination.address ?: stringResource(Res.string.destination)))
                FareBlock(
                    amount = booking.economics.passengerTotal,
                    currency = booking.economics.currency,
                    pricingRuleVersion = booking.economics.pricingRuleVersion,
                    finalFare = false,
                    breakdown = listOf(
                        FareBreakdownRow(stringResource(Res.string.fare_component_transport), "${booking.economics.transportFare} ${booking.economics.currency}"),
                        FareBreakdownRow(stringResource(Res.string.fare_component_scheduling_surcharge), "${booking.economics.schedulingSurcharge} ${booking.economics.currency}"),
                        FareBreakdownRow(stringResource(Res.string.fare_component_operator_service_fee), "${booking.economics.operatorServiceFee} ${booking.economics.currency}"),
                    ),
                )
                Text(booking.cancellationTerms.localizedSummary(), color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                Text(
                    if (booking.driverCommitted) stringResource(Res.string.scheduled_driver_committed)
                    else stringResource(Res.string.scheduled_driver_not_committed),
                    color = if (booking.driverCommitted) TaxiColors.Success600 else TaxiColors.Warning600,
                )
                if (booking.status in setOf("SCHEDULED", "OFFERING", "DRIVER_COMMITTED", "DISPATCH_HANDOFF")) {
                    TaxiButton(
                        stringResource(Res.string.scheduled_cancel),
                        { cancelCandidate = booking.id },
                        enabled = pendingAction == null,
                        loading = pendingAction.isPending(AppActionKind.CANCEL_SCHEDULED_BOOKING, booking.id),
                        style = TaxiButtonStyle.Secondary,
                    )
                }
                booking.cancellationFinancialOutcome?.let { Text(stringResource(Res.string.scheduled_cancellation_outcome, it)) }
            }
        }
    }
    cancelCandidate?.let { bookingId ->
        val booking = state.scheduledBookings.firstOrNull { it.id == bookingId }
        ConfirmDialog(
            title = stringResource(Res.string.scheduled_cancel_question),
            body = booking?.cancellationTerms?.localizedSummary() ?: stringResource(Res.string.scheduled_cancel_backend_policy),
            confirmLabel = stringResource(Res.string.scheduled_cancel_confirm),
            destructive = true,
            onConfirm = { cancelCandidate = null; onCancel(bookingId) },
            onCancel = { cancelCandidate = null },
        )
    }
}

private fun String.hasExplicitTimezone(): Boolean =
    endsWith("Z", ignoreCase = true) || Regex("[+-]\\d{2}:\\d{2}$").containsMatchIn(this)

@Composable
private fun ScheduledCancellationTerms.localizedSummary(): String = when (surchargeRefundMode) {
    "ALWAYS_FULL" -> stringResource(Res.string.scheduled_refund_always_full)
    "FULL_BEFORE_CUTOFF" -> stringResource(
        Res.string.scheduled_refund_before_cutoff,
        passengerCancelCutoffMinutes,
    )
    else -> stringResource(Res.string.scheduled_refund_never)
}

private fun scheduledStatusTone(status: String): StatusTone = when (status) {
    "LIVE_RIDE_CREATED" -> StatusTone.Success
    "CANCELLED", "UNFULFILLED" -> StatusTone.Danger
    "DRIVER_COMMITTED", "DISPATCH_HANDOFF" -> StatusTone.Info
    else -> StatusTone.Warning
}

@Composable
private fun PassengerFixedRoutesSheet(
    state: AppUiState.PassengerReady,
    pendingAction: AppAction?,
    selectedDirectionId: String?,
    selectedPaymentMethod: RidePaymentMethod,
    onBack: () -> Unit,
    onSelectCity: (String) -> Unit,
    onSelectDirection: (String) -> Unit,
    onEstimate: (String) -> Unit,
    onPaymentMethod: (RidePaymentMethod) -> Unit,
    onRequest: (String) -> Unit,
) {
    val language = Locale.current.language
    val catalog = state.fixedRouteCatalog
    val selected = catalog?.directions?.firstOrNull { it.id == selectedDirectionId }
    val estimate = state.fareEstimate?.takeIf {
        it.serviceType == RideServiceType.FIXED_ROUTE &&
            state.selectedFixedRouteDirectionId == selectedDirectionId
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(stringResource(Res.string.fixed_routes_title), style = MaterialTheme.typography.headlineSmall)
        TextButton(onClick = onBack) { Text(stringResource(Res.string.back_to_ride)) }
    }
    Text(
        stringResource(Res.string.fixed_routes_supply_private_help),
        color = TaxiColors.Ink500,
        style = MaterialTheme.typography.bodyMedium,
    )
    if (state.serviceCities.size > 1) {
        Text(stringResource(Res.string.fixed_routes_city), style = MaterialTheme.typography.titleMedium)
        state.serviceCities.forEach { city ->
            TaxiButton(
                city.name.preferred(language),
                { onSelectCity(city.id) },
                enabled = pendingAction == null && city.id != catalog?.city?.id,
                style = TaxiButtonStyle.Tertiary,
            )
        }
    }
    if (state.fixedRouteCatalogUnavailable) {
        ToastBanner(stringResource(Res.string.fixed_routes_unavailable), StatusTone.Warning)
    }
    if (catalog == null || catalog.directions.isEmpty()) {
        EmptyState(
            title = stringResource(Res.string.fixed_routes_empty),
            body = stringResource(Res.string.fixed_routes_empty_help),
        )
        return
    }
    catalog.directions.forEach { direction ->
        FixedRouteDirectionCard(
            direction = direction,
            language = language,
            selected = direction.id == selectedDirectionId,
            onClick = { onSelectDirection(direction.id) },
        )
    }
    selected?.let { direction ->
        if (estimate == null) {
            TaxiButton(
                stringResource(Res.string.fixed_routes_review_fare),
                { onEstimate(direction.id) },
                enabled = direction.immediateBookingEnabled && pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.ESTIMATE_FIXED_ROUTE, direction.id),
            )
            if (!direction.immediateBookingEnabled) {
                ToastBanner(stringResource(Res.string.fixed_routes_booking_unavailable), StatusTone.Info)
            }
        } else {
            FareBlock(
                amount = estimate.amount,
                currency = estimate.currency,
                pricingRuleVersion = estimate.pricingRuleVersion,
                finalFare = false,
            )
            Text(stringResource(Res.string.payment_method), style = MaterialTheme.typography.titleMedium)
            estimate.paymentMethods.forEach { method ->
                PaymentMethodCard(
                    label = stringResource(if (method == RidePaymentMethod.CASH) Res.string.payment_method_cash else Res.string.payment_method_manual_transfer),
                    detail = stringResource(if (method == RidePaymentMethod.CASH) Res.string.cash_payment_detail else Res.string.manual_transfer_payment_detail),
                    selected = selectedPaymentMethod == method,
                    onClick = { onPaymentMethod(method) },
                )
            }
            TaxiButton(
                stringResource(Res.string.fixed_routes_book_now),
                { onRequest(direction.id) },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.REQUEST_FIXED_ROUTE, direction.id),
            )
        }
    }
}

@Composable
private fun FixedRouteDirectionCard(
    direction: PublishedFixedRouteDirection,
    language: String,
    selected: Boolean,
    onClick: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = if (selected) TaxiColors.Accent100 else TaxiColors.Surface0,
        shape = androidx.compose.foundation.shape.RoundedCornerShape(org.example.taximobile.feature.ui.theme.TaxiRadii.Lg),
        border = androidx.compose.foundation.BorderStroke(
            1.dp,
            if (selected) TaxiColors.Accent500 else TaxiColors.StrokeSubtle,
        ),
        onClick = onClick,
    ) {
        Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            Text(direction.routeName.preferred(language), style = MaterialTheme.typography.titleMedium)
            Text(
                stringResource(
                    Res.string.route_direction_summary,
                    direction.startName.preferred(language),
                    direction.finishName.preferred(language),
                ),
                fontWeight = androidx.compose.ui.text.font.FontWeight.Bold,
            )
            Text(
                stringResource(
                    Res.string.fixed_route_fare_direction_summary,
                    direction.flatFare,
                    direction.currency,
                    direction.directionCode.replace('_', ' '),
                ),
                color = TaxiColors.Ink700,
            )
            if (direction.stops.isNotEmpty()) {
                Text(stringResource(Res.string.fixed_routes_stops_count, direction.stops.size), color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun SelectionSummary(
    form: PassengerTripFormState,
    selectedPlaceCityId: String?,
    pendingAction: AppAction?,
    onReverseSelected: (MapSelectionTarget, Coordinates) -> Unit,
) {
    LocationSelectionField(
        label = stringResource(Res.string.pickup),
        value = form.pickup?.address?.takeIf { it.isNotBlank() } ?: stringResource(
            if (form.pickup == null) Res.string.pickup_select_on_map else Res.string.pickup_selected_on_map,
        ),
        selected = form.selectionTarget == MapSelectionTarget.Pickup,
        onClick = { form.selectionTarget = MapSelectionTarget.Pickup },
        modifier = Modifier.testTag("passenger-pickup-selection"),
    )
    LocationSelectionField(
        label = stringResource(Res.string.destination),
        value = form.destination?.address?.takeIf { it.isNotBlank() } ?: stringResource(
            if (form.destination == null) Res.string.destination_select_on_map else Res.string.destination_selected_on_map,
        ),
        selected = form.selectionTarget == MapSelectionTarget.Destination,
        onClick = { form.selectionTarget = MapSelectionTarget.Destination },
        modifier = Modifier.testTag("passenger-destination-selection"),
    )
    val selectedTarget = form.selectionTarget
    val selectedCoordinate = if (selectedTarget == MapSelectionTarget.Pickup) form.pickup else form.destination
    if (selectedCoordinate != null && selectedPlaceCityId != null) {
        TaxiButton(
            label = stringResource(Res.string.lookup_selected_address),
            onClick = { onReverseSelected(selectedTarget, selectedCoordinate) },
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.REVERSE_PLACE, selectedPlaceCityId),
            style = TaxiButtonStyle.Tertiary,
        )
    }
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
    onSubmitManualTransfer: (String, String?) -> Unit,
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit,
    onLoadAccountSecurity: () -> Unit,
    onCreateRecoveryCodes: (String) -> Unit,
    onAcknowledgeRecoveryCodes: () -> Unit,
    onRevokeAccountSession: (String) -> Unit,
    onChangeAccountPassword: (String, String) -> Unit,
) {
    TaxiButton(stringResource(Res.string.back_to_ride), onBack, style = TaxiButtonStyle.Tertiary)
    Text(stringResource(Res.string.account), style = MaterialTheme.typography.displaySmall)
    state.profile?.let { PassengerProfileSection(it.displayName, pendingAction, onUpdateProfile) }
    state.selectedHistoryRide?.let { ride ->
        PassengerRideHistoryDetail(
            ride,
            state.selectedHistoryReceipt,
            pendingAction,
            onSubmitManualTransfer,
        )
    } ?: state.latestCompletedReceipt?.let { receipt ->
        PassengerReceipt(receipt, pendingAction, onSubmitManualTransfer)
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
    AccountSecuritySection(
        state = state.accountSecurity,
        pendingAction = pendingAction,
        onLoad = onLoadAccountSecurity,
        onCreateRecoveryCodes = onCreateRecoveryCodes,
        onAcknowledgeRecoveryCodes = onAcknowledgeRecoveryCodes,
        onRevokeSession = onRevokeAccountSession,
        onChangePassword = onChangeAccountPassword,
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
private fun PassengerSafetySheet(
    state: AppUiState.PassengerReady,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    onBack: () -> Unit,
    onCreateSafetyReport: (String, SafetyCategory, String) -> Unit,
) {
    TaxiButton(stringResource(Res.string.back_to_ride), onBack, style = TaxiButtonStyle.Tertiary)
    SafetyReportSection(
        reports = state.safetyReports,
        rideIds = listOfNotNull(state.activeRideId, state.selectedHistoryRide?.id) +
            state.rideHistory.map { it.id },
        pendingAction = pendingAction,
        completedAction = completedAction,
        onCreate = onCreateSafetyReport,
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
    pendingAction: AppAction?,
    onSubmitManualTransfer: (String, String?) -> Unit,
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
    receipt?.let { PassengerReceipt(it, pendingAction, onSubmitManualTransfer) }
}

@Composable
private fun PassengerReceipt(
    receipt: org.example.taximobile.domain.rides.RideReceipt,
    pendingAction: AppAction?,
    onSubmitManualTransfer: (String, String?) -> Unit,
) {
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
        tone = when (receipt.paymentStatus) {
            "COMPLETED" -> StatusTone.Success
            "REFUNDED" -> StatusTone.Info
            else -> StatusTone.Warning
        },
    )
    if (receipt.paymentMethod == "CASH" && receipt.paymentStatus == "PENDING") {
        Text(stringResource(Res.string.cash_settlement_pending))
    }
    if (receipt.paymentMethod == "MANUAL_TRANSFER") {
        ManualTransferReceipt(
            receipt = receipt,
            pendingAction = pendingAction,
            onSubmit = onSubmitManualTransfer,
        )
    }
    receipt.refunds?.takeIf { it.items.isNotEmpty() }?.let { refunds ->
        RefundReceiptSummary(refunds)
    }
}

@Composable
private fun RefundReceiptSummary(
    refunds: org.example.taximobile.domain.rides.RideRefundSummary,
) {
    Text(stringResource(Res.string.refunds_title), style = MaterialTheme.typography.titleMedium)
    Text(
        stringResource(
            Res.string.refunded_total,
            refunds.refundedAmount,
            refunds.currency,
        )
    )
    Text(
        stringResource(
            Res.string.net_paid_after_refunds,
            refunds.netPaidAmount,
            refunds.currency,
        )
    )
    refunds.items.forEach { refund ->
        Text(
            stringResource(
                Res.string.refund_item,
                refundReasonLabel(refund.reason),
                refund.amount,
                refund.currency,
            ),
            style = MaterialTheme.typography.bodyMedium,
            color = TaxiColors.Ink500,
        )
    }
}

@Composable
private fun ManualTransferReceipt(
    receipt: org.example.taximobile.domain.rides.RideReceipt,
    pendingAction: AppAction?,
    onSubmit: (String, String?) -> Unit,
) {
    val instructions = receipt.manualTransfer
    if (instructions == null) {
        ToastBanner(stringResource(Res.string.manual_transfer_instructions_unavailable), StatusTone.Warning)
        return
    }
    var payerReference by remember(receipt.rideId) { mutableStateOf("") }
    Text(stringResource(Res.string.manual_transfer_title), style = MaterialTheme.typography.titleMedium)
    SelectionContainer {
        Column {
            Text(stringResource(Res.string.manual_transfer_recipient, instructions.recipientName))
            instructions.bankAccount?.let {
                Text(stringResource(Res.string.manual_transfer_bank_account, ltrIsolate(it)))
            }
            instructions.walletId?.let {
                Text(stringResource(Res.string.manual_transfer_wallet_id, ltrIsolate(it)))
            }
            Text(
                stringResource(
                    Res.string.manual_transfer_payment_reference,
                    ltrIsolate(instructions.paymentReference),
                )
            )
        }
    }
    Text(
        stringResource(Res.string.manual_transfer_reference_warning),
        style = MaterialTheme.typography.bodyMedium,
        color = TaxiColors.Ink500,
    )
    when (receipt.paymentStatus) {
        "PENDING" -> {
            val payerReferenceInvalid = payerReference.isNotEmpty() && payerReference.length < 3
            if (instructions.latestClaimStatus == "REJECTED") {
                ToastBanner(
                    stringResource(Res.string.manual_transfer_rejected_retry),
                    StatusTone.Warning,
                )
            }
            TaxiTextField(
                payerReference,
                { value ->
                    payerReference = value.filter {
                        it in 'A'..'Z' || it in 'a'..'z' || it in '0'..'9' || it in "._/-"
                    }.take(80)
                },
                stringResource(Res.string.manual_transfer_payer_reference_optional),
                isError = payerReferenceInvalid,
                supportingText = if (payerReferenceInvalid) {
                    stringResource(Res.string.manual_transfer_payer_reference_error)
                } else {
                    null
                },
            )
            TaxiButton(
                stringResource(Res.string.manual_transfer_submit_for_review),
                onClick = {
                    onSubmit(receipt.rideId, payerReference.trim().ifEmpty { null })
                },
                enabled = pendingAction == null && !payerReferenceInvalid,
                loading = pendingAction.isPending(
                    AppActionKind.SUBMIT_MANUAL_TRANSFER,
                    receipt.rideId,
                ),
            )
        }
        "PROCESSING" -> ToastBanner(
            stringResource(Res.string.manual_transfer_review_pending),
            StatusTone.Info,
        )
        "COMPLETED", "REFUNDED" -> Text(stringResource(Res.string.manual_transfer_verified))
        else -> ToastBanner(
            stringResource(Res.string.manual_transfer_needs_attention),
            StatusTone.Warning,
        )
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
    when (code) {
        "BASE_FARE" -> Res.string.fare_component_base
        "TRANSPORT_FARE" -> Res.string.fare_component_transport
        "SCHEDULING_SURCHARGE" -> Res.string.fare_component_scheduling_surcharge
        "OPERATOR_SERVICE_FEE" -> Res.string.fare_component_operator_service_fee
        else -> Res.string.fare_component_other
    }
)

/** Used only to suppress zero-value rows; it never derives or changes money. */
private fun String.hasNonZeroDigit(): Boolean = any { it in '1'..'9' }

@Composable
private fun paymentMethodLabel(method: String): String = stringResource(
    when (method) {
        "CASH" -> Res.string.payment_method_cash
        "CARD" -> Res.string.payment_method_card
        "MOBILE_PAYMENT" -> Res.string.payment_method_mobile
        "MANUAL_TRANSFER" -> Res.string.payment_method_manual_transfer
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
        "REFUNDED" -> Res.string.payment_status_refunded
        else -> Res.string.payment_status_unknown
    }
)

@Composable
private fun refundReasonLabel(reason: String): String = stringResource(
    when (reason) {
        "FARE_CORRECTION" -> Res.string.refund_reason_fare_correction
        "DUPLICATE_PAYMENT" -> Res.string.refund_reason_duplicate_payment
        "SERVICE_RECOVERY" -> Res.string.refund_reason_service_recovery
        "OTHER_APPROVED" -> Res.string.refund_reason_other_approved
        else -> Res.string.refund_reason_unknown
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

private val PARTICIPANT_COORDINATION_STATUSES = setOf(
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_EN_ROUTE,
    RideStatus.DRIVER_ARRIVED,
    RideStatus.IN_PROGRESS,
)
