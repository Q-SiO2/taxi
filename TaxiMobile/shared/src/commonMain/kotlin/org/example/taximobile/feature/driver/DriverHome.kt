package org.example.taximobile.feature.driver

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.intl.Locale
import kotlinx.coroutines.delay
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverRideAction
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideCoordinationCode
import org.example.taximobile.domain.rides.RideCoordinationSenderRole
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideSummary
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionCompletion
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.NotificationInboxSection
import org.example.taximobile.feature.app.SafetyReportSection
import org.example.taximobile.feature.app.SupportTicketSection
import org.example.taximobile.feature.app.isPending
import org.example.taximobile.feature.app.confirms
import org.example.taximobile.feature.app.formatKilometers
import org.example.taximobile.feature.app.formatMinutes
import org.example.taximobile.feature.app.passengerStatusResource
import org.example.taximobile.feature.app.driverAccountStatusResource
import org.example.taximobile.feature.app.driverVerificationStatusResource
import org.example.taximobile.feature.app.validCoordinates
import org.example.taximobile.feature.account.AccountSecuritySection
import org.example.taximobile.feature.location.ForegroundDriverLocationPolicy
import org.example.taximobile.feature.rides.RideCoordinationActions
import org.example.taximobile.feature.rides.RideLatestCoordinationMessage
import org.example.taximobile.feature.maps.MapLibreTripMap
import org.example.taximobile.feature.passenger.passengerStatusTone
import org.example.taximobile.feature.ui.components.ConfirmDialog
import org.example.taximobile.feature.ui.components.EmptyState
import org.example.taximobile.feature.ui.components.DriverDocumentCard
import org.example.taximobile.feature.ui.components.FareBlock
import org.example.taximobile.feature.ui.components.FareBreakdownRow
import org.example.taximobile.feature.ui.components.MapFab
import org.example.taximobile.feature.ui.components.OfferCard
import org.example.taximobile.feature.ui.components.StatusPill
import org.example.taximobile.feature.ui.components.SuccessConfirmation
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiButtonStyle
import org.example.taximobile.feature.ui.components.TaxiSheet
import org.example.taximobile.feature.ui.components.TaxiSheetSnap
import org.example.taximobile.feature.ui.components.TaxiTextField
import org.example.taximobile.feature.ui.components.TaxiCard
import org.example.taximobile.feature.ui.components.VehicleAssetFallback
import org.example.taximobile.feature.ui.components.ToastBanner
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.text.UiMessage
import org.example.taximobile.feature.ui.text.resolve
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

private enum class DriverSheetPanel { Operations, Scheduled, Safety, Account, Inbox }

private val PARTICIPANT_COORDINATION_STATUSES = setOf(
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_EN_ROUTE,
    RideStatus.DRIVER_ARRIVED,
    RideStatus.IN_PROGRESS,
)

private class DriverCoordinateDraft {
    var latitude by mutableStateOf("")
    var longitude by mutableStateOf("")
    var message by mutableStateOf<UiMessage?>(null)
    val coordinates: Coordinates?
        get() = validCoordinates(latitude, longitude)

    fun load(coordinates: Coordinates) {
        latitude = coordinates.latitude.toString()
        longitude = coordinates.longitude.toString()
    }
}

@Composable
internal fun DriverHome(
    state: AppUiState.DriverReady,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    mapStyleUrl: String?,
    onLogout: () -> Unit,
    onRequestCurrentLocation: ((Coordinates?) -> Unit) -> Unit,
    onSetDriverOnline: (Boolean, String?, String?) -> Unit,
    onUpdateDriverLocation: (Coordinates) -> Unit,
    onRegisterDriverVehicle: (VehicleRegistration) -> Unit,
    onSelectDriverVehicle: (String) -> Unit,
    onDeactivateDriverVehicle: (String) -> Unit,
    onRespondToOffer: (String, Boolean) -> Unit,
    onSetScheduledOfferPreference: (String, Boolean) -> Unit,
    onRespondToScheduledOffer: (String, Boolean) -> Unit,
    onAdvanceDriverRide: (String, DriverRideAction) -> Unit,
    onCancelDriverRide: (String, String) -> Unit,
    onSendRideCoordination: (String, RideCoordinationCode) -> Unit,
    onCompleteDriverRide: (String, Coordinates) -> Unit,
    onSettleDriverCash: (String) -> Unit,
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit,
    onCreateSafetyReport: (String, SafetyCategory, String) -> Unit,
    onMarkNotificationRead: (String) -> Unit,
    onSelectDriverRide: (String) -> Unit,
    onOfferExpired: () -> Unit,
    onLoadAccountSecurity: () -> Unit,
    onCreateRecoveryCodes: (String) -> Unit,
    onAcknowledgeRecoveryCodes: () -> Unit,
    onRevokeAccountSession: (String) -> Unit,
    onChangeAccountPassword: (String, String) -> Unit,
) {
    val locationDraft = remember { DriverCoordinateDraft() }
    val completionDraft = remember { DriverCoordinateDraft() }
    var panel by remember { mutableStateOf(DriverSheetPanel.Operations) }
    var snap by remember { mutableStateOf(TaxiSheetSnap.Peek) }
    var declineOfferId by remember { mutableStateOf<String?>(null) }
    var cancelRide by remember { mutableStateOf<Pair<String, String>?>(null) }
    var settleCashRideId by remember { mutableStateOf<String?>(null) }
    var cameraFocusRequest by remember { mutableIntStateOf(0) }
    var locationRequestInFlight by remember { mutableStateOf(false) }
    var mapUnavailable by remember(mapStyleUrl) { mutableStateOf(false) }
    val requestCurrentLocation: ((Coordinates?) -> Unit) -> Unit = { onResult ->
        if (!locationRequestInFlight) {
            locationRequestInFlight = true
            onRequestCurrentLocation { selected ->
                locationRequestInFlight = false
                onResult(selected)
            }
        }
    }

    val guidanceDestination = when (state.activeRide) {
        RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE -> state.pickup
        RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS -> state.destination
        else -> null
    }
    LaunchedEffect(
        panel,
        state.activeRide,
        state.offers.size,
        state.pendingCashRideId,
        completedAction?.sequence,
    ) {
        snap = when {
            panel != DriverSheetPanel.Operations -> TaxiSheetSnap.Expanded
            completedAction?.action?.kind == AppActionKind.SETTLE_DRIVER_CASH -> TaxiSheetSnap.Half
            state.activeRide != null || state.offers.isNotEmpty() || state.pendingCashRideId != null -> TaxiSheetSnap.Half
            state.availability == DriverAvailabilityStatus.OFFLINE || state.availability == DriverAvailabilityStatus.PAUSED -> TaxiSheetSnap.Half
            else -> TaxiSheetSnap.Peek
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize().background(TaxiColors.Surface1)) {
        MapLibreTripMap(
            pickup = state.pickup.takeIf {
                state.activeRide in setOf(
                    RideStatus.ACCEPTED,
                    RideStatus.DRIVER_EN_ROUTE,
                    RideStatus.DRIVER_ARRIVED,
                )
            },
            destination = state.destination.takeIf {
                state.activeRide in setOf(RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS)
            },
            driverLocation = state.currentLocation,
            routeGeometry = if (guidanceDestination == null) emptyList() else state.routePlan?.geometry.orEmpty(),
            styleUrl = mapStyleUrl,
            cameraFocusRequest = cameraFocusRequest,
            onMapAvailabilityChanged = { mapUnavailable = !it },
            onCoordinateSelected = {},
            modifier = Modifier.fillMaxSize(),
        )
        DriverToolbar(
            displayName = state.displayName,
            unreadCount = state.notifications.count { !it.read },
            onAccount = { panel = DriverSheetPanel.Account },
            onSafety = { panel = DriverSheetPanel.Safety },
            onInbox = { panel = DriverSheetPanel.Inbox },
            modifier = Modifier.align(Alignment.TopCenter).padding(TaxiSpacing.Md),
        )
        if (panel == DriverSheetPanel.Operations) {
            Column(
                modifier = Modifier.align(Alignment.BottomEnd)
                    .padding(end = TaxiSpacing.Md, bottom = maxHeight * snap.heightFraction + TaxiSpacing.Md),
                horizontalAlignment = Alignment.End,
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
            ) {
                MapFab(
                    label = when {
                        guidanceDestination != null -> stringResource(Res.string.recenter_navigation_route)
                        state.currentLocation != null || state.pickup != null -> stringResource(Res.string.recenter_driver_position)
                        else -> stringResource(Res.string.recenter_map)
                    },
                    glyph = "⌖",
                    onClick = { cameraFocusRequest += 1 },
                )
                MapFab(
                    label = stringResource(Res.string.load_driver_location),
                    glyph = "◎",
                    enabled = !locationRequestInFlight,
                    loading = locationRequestInFlight,
                    onClick = {
                        locationDraft.message = UiMessage(Res.string.requesting_current_location)
                        requestCurrentLocation { selected ->
                            if (selected == null) {
                                locationDraft.message = UiMessage(Res.string.driver_location_unavailable)
                            } else {
                                locationDraft.load(selected)
                                locationDraft.message = UiMessage(Res.string.driver_location_loaded)
                                snap = TaxiSheetSnap.Half
                            }
                        }
                    },
                )
            }
        }
        TaxiSheet(snap = snap, onSnapChange = { snap = it }) {
            if (mapUnavailable) {
                ToastBanner(stringResource(Res.string.map_detail_unavailable), StatusTone.Warning)
            }
            if (panel != DriverSheetPanel.Operations) {
                state.activeRide?.let { rideStatus ->
                    StatusPill(
                        stringResource(rideStatus.passengerStatusResource()),
                        rideStatus.passengerStatusTone(),
                    )
                }
            }
            when (panel) {
                DriverSheetPanel.Operations -> DriverOperationsSheet(
                    state = state,
                    pendingAction = pendingAction,
                    completedAction = completedAction,
                    locationDraft = locationDraft,
                    completionDraft = completionDraft,
                    locationRequestInFlight = locationRequestInFlight,
                    onRequestCurrentLocation = requestCurrentLocation,
                    onSetDriverOnline = onSetDriverOnline,
                    onUpdateDriverLocation = onUpdateDriverLocation,
                    onAcceptOffer = { onRespondToOffer(it, true) },
                    onDeclineOffer = { declineOfferId = it },
                    onAdvanceDriverRide = onAdvanceDriverRide,
                    onCancelRide = { rideId, reason -> cancelRide = rideId to reason },
                    onSendRideCoordination = onSendRideCoordination,
                    onCompleteDriverRide = onCompleteDriverRide,
                    onSettleCash = { settleCashRideId = it },
                    onOfferExpired = onOfferExpired,
                    onOpenScheduled = { panel = DriverSheetPanel.Scheduled },
                )
                DriverSheetPanel.Scheduled -> DriverScheduledSheet(
                    state = state,
                    pendingAction = pendingAction,
                    onBack = { panel = DriverSheetPanel.Operations },
                    onPreference = onSetScheduledOfferPreference,
                    onRespond = onRespondToScheduledOffer,
                )
                DriverSheetPanel.Account -> DriverAccountSheet(
                    state = state,
                    pendingAction = pendingAction,
                    completedAction = completedAction,
                    onBack = { panel = DriverSheetPanel.Operations },
                    onLogout = onLogout,
                    onRegisterVehicle = onRegisterDriverVehicle,
                    onSelectVehicle = onSelectDriverVehicle,
                    onDeactivateVehicle = onDeactivateDriverVehicle,
                    onCreateSupportTicket = onCreateSupportTicket,
                    onSelectRide = onSelectDriverRide,
                    onLoadAccountSecurity = onLoadAccountSecurity,
                    onCreateRecoveryCodes = onCreateRecoveryCodes,
                    onAcknowledgeRecoveryCodes = onAcknowledgeRecoveryCodes,
                    onRevokeAccountSession = onRevokeAccountSession,
                    onChangeAccountPassword = onChangeAccountPassword,
                )
                DriverSheetPanel.Safety -> DriverSafetySheet(
                    state = state,
                    pendingAction = pendingAction,
                    completedAction = completedAction,
                    onBack = { panel = DriverSheetPanel.Operations },
                    onCreateSafetyReport = onCreateSafetyReport,
                )
                DriverSheetPanel.Inbox -> DriverInboxSheet(
                    notifications = state.notifications,
                    pendingAction = pendingAction,
                    onBack = { panel = DriverSheetPanel.Operations },
                    onMarkRead = onMarkNotificationRead,
                )
            }
        }
    }
    declineOfferId?.let { offerId ->
        ConfirmDialog(
            title = stringResource(Res.string.decline_offer_question),
            body = stringResource(Res.string.decline_offer_body),
            confirmLabel = stringResource(Res.string.decline_offer),
            destructive = true,
            onConfirm = {
                declineOfferId = null
                onRespondToOffer(offerId, false)
            },
            onCancel = { declineOfferId = null },
        )
    }
    cancelRide?.let { (rideId, reason) ->
        ConfirmDialog(
            title = stringResource(Res.string.cancel_assigned_ride_question),
            body = stringResource(Res.string.cancel_assigned_ride_body, reason),
            confirmLabel = stringResource(Res.string.cancel_ride),
            destructive = true,
            onConfirm = {
                cancelRide = null
                onCancelDriverRide(rideId, reason)
            },
            onCancel = { cancelRide = null },
        )
    }
    settleCashRideId?.let { rideId ->
        ConfirmDialog(
            title = stringResource(Res.string.confirm_cash_received_question),
            body = stringResource(Res.string.confirm_cash_received_body),
            confirmLabel = stringResource(Res.string.cash_received),
            onConfirm = {
                settleCashRideId = null
                onSettleDriverCash(rideId)
            },
            onCancel = { settleCashRideId = null },
        )
    }
}

@Composable
private fun DriverToolbar(
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
                Text(displayName?.ifBlank { null } ?: stringResource(Res.string.driver_account))
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
private fun DriverOperationsSheet(
    state: AppUiState.DriverReady,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    locationDraft: DriverCoordinateDraft,
    completionDraft: DriverCoordinateDraft,
    locationRequestInFlight: Boolean,
    onRequestCurrentLocation: ((Coordinates?) -> Unit) -> Unit,
    onSetDriverOnline: (Boolean, String?, String?) -> Unit,
    onUpdateDriverLocation: (Coordinates) -> Unit,
    onAcceptOffer: (String) -> Unit,
    onDeclineOffer: (String) -> Unit,
    onAdvanceDriverRide: (String, DriverRideAction) -> Unit,
    onCancelRide: (String, String) -> Unit,
    onSendRideCoordination: (String, RideCoordinationCode) -> Unit,
    onCompleteDriverRide: (String, Coordinates) -> Unit,
    onSettleCash: (String) -> Unit,
    onOfferExpired: () -> Unit,
    onOpenScheduled: () -> Unit,
) {
    Text(stringResource(Res.string.driver_home), style = MaterialTheme.typography.displaySmall)
    StatusPill(
        stringResource(state.availability.driverAvailabilityResource()),
        state.availability.driverAvailabilityTone(),
    )
    val activeVehicle = state.vehicles.firstOrNull { it.id == state.activeVehicleId }
    val vehicleReady = activeVehicle?.status == "ACTIVE" && activeVehicle.verificationStatus == "VERIFIED"
    var selectedCityId by remember(state.onlineCityId, state.authorizedMarkets) {
        mutableStateOf(state.onlineCityId ?: state.authorizedMarkets.firstOrNull()?.cityId)
    }
    val selectedMarket = state.authorizedMarkets.firstOrNull { it.cityId == selectedCityId }
    var selectedServiceType by remember(state.onlineServiceType, selectedCityId) {
        mutableStateOf(
            state.onlineServiceType
                ?.takeIf { it in selectedMarket?.authorization?.serviceTypes.orEmpty() }
                ?: selectedMarket?.authorization?.serviceTypes?.firstOrNull(),
        )
    }
    LaunchedEffect(selectedCityId, selectedMarket?.authorization?.serviceTypes) {
        if (selectedServiceType !in selectedMarket?.authorization?.serviceTypes.orEmpty()) {
            selectedServiceType = selectedMarket?.authorization?.serviceTypes?.firstOrNull()
        }
    }
    val authorizationReady = !state.cityAuthorizationRequired ||
        (selectedMarket != null && selectedServiceType != null && !state.cityAuthorizationLoadFailed)
    if (state.availability == DriverAvailabilityStatus.OFFLINE || state.availability == DriverAvailabilityStatus.PAUSED) {
        Text(stringResource(Res.string.ready_checklist), style = MaterialTheme.typography.titleMedium)
        StatusPill(
            stringResource(
                if (vehicleReady) Res.string.verified_vehicle_selected else Res.string.select_verified_vehicle
            ),
            if (vehicleReady) StatusTone.Success else StatusTone.Warning,
        )
        StatusPill(
            stringResource(
                if (state.currentLocation != null) Res.string.location_submitted else Res.string.location_required
            ),
            if (state.currentLocation != null) StatusTone.Success else StatusTone.Warning,
        )
        if (state.cityAuthorizationRequired) {
            Text(stringResource(Res.string.operating_city), style = MaterialTheme.typography.titleMedium)
            when {
                state.cityAuthorizationLoadFailed -> ToastBanner(
                    stringResource(Res.string.city_authorizations_unavailable),
                    StatusTone.Warning,
                )
                state.authorizedMarkets.isEmpty() -> EmptyState(
                    title = stringResource(Res.string.no_active_city_authorization),
                    body = stringResource(Res.string.no_active_city_authorization_help),
                )
                else -> {
                    state.authorizedMarkets.forEach { market ->
                        TaxiButton(
                            label = market.cityName.forLanguage(Locale.current.language),
                            onClick = { selectedCityId = market.cityId },
                            style = if (market.cityId == selectedCityId) {
                                TaxiButtonStyle.Primary
                            } else {
                                TaxiButtonStyle.Secondary
                            },
                            enabled = pendingAction == null,
                        )
                    }
                    selectedMarket?.let { market ->
                        Text(stringResource(Res.string.operating_service), style = MaterialTheme.typography.titleMedium)
                        market.authorization.serviceTypes.forEach { serviceType ->
                            TaxiButton(
                                label = stringResource(driverServiceTypeResource(serviceType)),
                                onClick = { selectedServiceType = serviceType },
                                style = if (serviceType == selectedServiceType) {
                                    TaxiButtonStyle.Primary
                                } else {
                                    TaxiButtonStyle.Secondary
                                },
                                enabled = pendingAction == null,
                            )
                        }
                    }
                }
            }
        }
        TaxiButton(
            stringResource(Res.string.go_online),
            { onSetDriverOnline(true, selectedCityId, selectedServiceType ?: "ON_DEMAND") },
            modifier = Modifier.testTag("driver-go-online"),
            enabled = vehicleReady && state.currentLocation != null && authorizationReady && pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.SET_DRIVER_AVAILABILITY),
        )
    } else if (state.availability == DriverAvailabilityStatus.AVAILABLE) {
        state.authorizedMarkets.firstOrNull { it.cityId == state.onlineCityId }?.let { market ->
            Text(
                stringResource(
                    Res.string.online_market_summary,
                    market.cityName.forLanguage(Locale.current.language),
                    stringResource(driverServiceTypeResource(state.onlineServiceType ?: "ON_DEMAND")),
                ),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Text(stringResource(Res.string.waiting_for_offers), style = MaterialTheme.typography.bodyLarge)
        TaxiButton(
            stringResource(Res.string.go_offline),
            { onSetDriverOnline(false, null, null) },
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.SET_DRIVER_AVAILABILITY),
            style = TaxiButtonStyle.Secondary,
        )
    }
    state.offers.firstOrNull()?.let { offer ->
        val distanceAndEta = listOfNotNull(
            offer.estimatedPickupDistanceMeters?.let {
                stringResource(Res.string.meters_to_pickup, it)
            },
            offer.estimatedPickupTimeSeconds?.let {
                stringResource(Res.string.about_minutes, formatMinutes(it))
            },
        ).joinToString(" · ").ifBlank { null }
        val fare = if (offer.estimatedFareAmount != null && offer.estimatedFareCurrency != null) {
            stringResource(
                Res.string.estimated_fare_value,
                offer.estimatedFareAmount,
                offer.estimatedFareCurrency,
            )
        } else null
        val economicsDetails = offer.economics?.let { economics ->
            listOf(
                stringResource(
                    Res.string.expected_driver_net_value,
                    economics.expectedDriverNet,
                    offer.estimatedFareCurrency.orEmpty(),
                ),
                stringResource(
                    Res.string.operator_service_fee_value,
                    economics.operatorServiceFee,
                    offer.estimatedFareCurrency.orEmpty(),
                ),
                stringResource(
                    when (economics.operatorFeeFundingMode) {
                        "DRIVER_SETTLEMENT_DEDUCTION" -> Res.string.operator_fee_funding_driver
                        "PASSENGER_SURCHARGE" -> Res.string.operator_fee_funding_passenger
                        else -> Res.string.operator_fee_funding_unknown
                    }
                ),
            )
        }.orEmpty()
        val serviceDetails = buildList {
            add(
                stringResource(
                    when (offer.serviceType) {
                        org.example.taximobile.domain.rides.RideServiceType.FIXED_ROUTE -> Res.string.service_type_fixed_route
                        org.example.taximobile.domain.rides.RideServiceType.SCHEDULED -> Res.string.service_type_scheduled
                        else -> Res.string.service_type_on_demand
                    }
                )
            )
            offer.fixedRoute?.let { route ->
                val language = androidx.compose.ui.text.intl.Locale.current.language
                add("${route.startName.preferred(language)} → ${route.finishName.preferred(language)}")
            }
        }
        TimedOfferCard(
            offer = offer,
            pickupSummary = stringResource(
                Res.string.pickup_coordinates,
                offer.pickup.latitude.toString(),
                offer.pickup.longitude.toString(),
            ),
            distanceAndEta = distanceAndEta,
            fare = fare,
            economicsDetails = serviceDetails + economicsDetails,
            onAccept = { onAcceptOffer(offer.id) },
            onDecline = { onDeclineOffer(offer.id) },
            onExpired = onOfferExpired,
            pendingAction = pendingAction,
            modifier = Modifier.fillMaxWidth(),
        )
    }
    if (state.availability in ForegroundDriverLocationPolicy.OPERATIONAL_LOCATION_STATES) {
        Text(
            stringResource(Res.string.foreground_driver_location_active),
            color = TaxiColors.Ink500,
            style = MaterialTheme.typography.bodySmall,
        )
    }
    TaxiButton(
        stringResource(
            Res.string.scheduled_work_summary,
            state.scheduledOffers.size,
            state.scheduledCommitments.size,
        ),
        onOpenScheduled,
        enabled = pendingAction == null,
        style = TaxiButtonStyle.Secondary,
    )
    state.routePlan?.let { route ->
        Text(
            stringResource(
                Res.string.route_summary,
                formatKilometers(route.distanceMeters),
                formatMinutes(route.durationSeconds),
            )
        )
        route.maneuvers.take(4).forEach { Text(it.instruction, style = MaterialTheme.typography.bodyMedium) }
    }
    if (state.routeUnavailable) ToastBanner(stringResource(Res.string.driver_route_unavailable))
    state.pendingCashRideId?.let {
        TaxiButton(
            stringResource(Res.string.confirm_cash_received),
            { onSettleCash(it) },
            enabled = pendingAction == null,
            loading = pendingAction.isPending(AppActionKind.SETTLE_DRIVER_CASH, it),
        )
    }
    if (completedAction?.action?.kind == AppActionKind.SETTLE_DRIVER_CASH) {
        SuccessConfirmation(
            stringResource(Res.string.cash_received_confirmation),
            completedAction.sequence,
        )
    }
    state.activeRideId?.let { rideId ->
        state.activeFixedRoute?.let { route ->
            val language = androidx.compose.ui.text.intl.Locale.current.language
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
        RideLatestCoordinationMessage(state.latestCoordinationMessage)
        when (state.activeRide) {
            RideStatus.ACCEPTED -> TaxiButton(
                stringResource(Res.string.start_heading_pickup),
                { onAdvanceDriverRide(rideId, DriverRideAction.EN_ROUTE) },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.ADVANCE_DRIVER_RIDE, rideId),
            )
            RideStatus.DRIVER_EN_ROUTE -> TaxiButton(
                stringResource(Res.string.mark_arrived),
                { onAdvanceDriverRide(rideId, DriverRideAction.ARRIVED) },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.ADVANCE_DRIVER_RIDE, rideId),
            )
            RideStatus.DRIVER_ARRIVED -> TaxiButton(
                stringResource(Res.string.start_ride),
                { onAdvanceDriverRide(rideId, DriverRideAction.START) },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.ADVANCE_DRIVER_RIDE, rideId),
            )
            RideStatus.IN_PROGRESS -> DriverCompletionControls(
                rideId,
                completionDraft,
                pendingAction,
                locationRequestInFlight,
                onRequestCurrentLocation,
                onCompleteDriverRide,
            )
            else -> Unit
        }
        if (state.activeRide in setOf(RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE, RideStatus.DRIVER_ARRIVED)) {
            var reason by remember(rideId) { mutableStateOf("") }
            TaxiTextField(reason, { reason = it }, stringResource(Res.string.cancellation_reason))
            TaxiButton(
                stringResource(Res.string.cancel_assigned_ride),
                { onCancelRide(rideId, reason.trim()) },
                enabled = reason.isNotBlank() && pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.CANCEL_DRIVER_RIDE, rideId),
                style = TaxiButtonStyle.Destructive,
            )
        }
        if (state.activeRide in PARTICIPANT_COORDINATION_STATUSES) {
            RideCoordinationActions(
                rideId = rideId,
                senderRole = RideCoordinationSenderRole.DRIVER,
                pendingAction = pendingAction,
                onSend = onSendRideCoordination,
            )
        }
    }
    Text(stringResource(Res.string.driver_location), style = MaterialTheme.typography.titleMedium)
    locationDraft.message?.let { ToastBanner(it.resolve()) }
    TaxiTextField(locationDraft.latitude, { locationDraft.latitude = it }, stringResource(Res.string.current_latitude), keyboardType = KeyboardType.Decimal)
    TaxiTextField(locationDraft.longitude, { locationDraft.longitude = it }, stringResource(Res.string.current_longitude), keyboardType = KeyboardType.Decimal)
    TaxiButton(
        stringResource(Res.string.submit_location),
        { onUpdateDriverLocation(requireNotNull(locationDraft.coordinates)) },
        enabled = locationDraft.coordinates != null && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.UPDATE_DRIVER_LOCATION),
        style = TaxiButtonStyle.Secondary,
    )
}

@Composable
private fun DriverScheduledSheet(
    state: AppUiState.DriverReady,
    pendingAction: AppAction?,
    onBack: () -> Unit,
    onPreference: (String, Boolean) -> Unit,
    onRespond: (String, Boolean) -> Unit,
) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(stringResource(Res.string.scheduled_work_title), style = MaterialTheme.typography.headlineSmall)
        TextButton(onClick = onBack) { Text(stringResource(Res.string.scheduled_back_to_live)) }
    }
    Text(
        stringResource(Res.string.scheduled_driver_participation),
        color = TaxiColors.Ink500,
    )
    if (state.authorizedMarkets.isEmpty()) {
        EmptyState(
            stringResource(Res.string.scheduled_no_authorized_city),
            stringResource(Res.string.scheduled_no_authorized_city_help),
        )
    } else {
        state.authorizedMarkets.forEach { market ->
            val preference = state.scheduledOfferPreferences.firstOrNull { it.cityId == market.cityId }
            Surface(
                Modifier.fillMaxWidth(),
                shape = MaterialTheme.shapes.medium,
                color = TaxiColors.Surface0,
            ) {
                Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Text(market.cityName.forLanguage(Locale.current.language), style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(Res.string.scheduled_preference_backend), color = TaxiColors.Ink500)
                    Text(
                        stringResource(
                            when (preference?.enabled) {
                                true -> Res.string.scheduled_preference_enabled
                                false -> Res.string.scheduled_preference_disabled
                                null -> Res.string.scheduled_preference_not_set
                            }
                        ),
                        color = if (preference?.enabled == true) TaxiColors.Success600 else TaxiColors.Ink500,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                        TaxiButton(
                            stringResource(Res.string.scheduled_receive_offers),
                            { onPreference(market.cityId, true) },
                            modifier = Modifier.weight(1f),
                            enabled = pendingAction == null,
                            loading = pendingAction.isPending(AppActionKind.SET_SCHEDULED_OFFER_PREFERENCE, market.cityId),
                        )
                        TaxiButton(
                            stringResource(Res.string.scheduled_stop_offers),
                            { onPreference(market.cityId, false) },
                            modifier = Modifier.weight(1f),
                            enabled = pendingAction == null,
                            style = TaxiButtonStyle.Secondary,
                        )
                    }
                }
            }
        }
    }
    Text(stringResource(Res.string.scheduled_future_offers), style = MaterialTheme.typography.titleLarge)
    if (state.scheduledOffers.isEmpty()) {
        EmptyState(
            stringResource(Res.string.scheduled_no_offers),
            stringResource(Res.string.scheduled_no_offers_help),
        )
    }
    state.scheduledOffers.forEach { offer ->
        Surface(Modifier.fillMaxWidth(), shape = MaterialTheme.shapes.medium, color = TaxiColors.Surface0) {
            Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(offer.scheduledFor, style = MaterialTheme.typography.titleMedium)
                    StatusPill(offer.serviceType.replace('_', ' '), StatusTone.Info)
                }
                Text(stringResource(Res.string.scheduled_location_summary, offer.pickup.address ?: stringResource(Res.string.pickup), offer.destination.address ?: stringResource(Res.string.destination)))
                Text(stringResource(Res.string.scheduled_offer_deadline, offer.expiresAt, offer.serverTime), color = TaxiColors.Warning600)
                FareBlock(
                    amount = offer.economics.expectedDriverNet,
                    currency = offer.economics.currency,
                    pricingRuleVersion = offer.economics.pricingRuleVersion,
                    finalFare = false,
                    breakdown = listOf(
                        FareBreakdownRow(stringResource(Res.string.fare_component_transport), "${offer.economics.transportFare} ${offer.economics.currency}"),
                        FareBreakdownRow(stringResource(Res.string.fare_component_scheduling_surcharge), "${offer.economics.schedulingSurcharge} ${offer.economics.currency}"),
                        FareBreakdownRow(stringResource(Res.string.fare_component_operator_service_fee), "${offer.economics.operatorServiceFee} ${offer.economics.currency}"),
                    ),
                )
                Text(
                    when (offer.cancellationTerms.surchargeRefundMode) {
                        "ALWAYS_FULL" -> stringResource(Res.string.scheduled_refund_always_full)
                        "FULL_BEFORE_CUTOFF" -> stringResource(
                            Res.string.scheduled_refund_before_cutoff,
                            offer.cancellationTerms.passengerCancelCutoffMinutes,
                        )
                        else -> stringResource(Res.string.scheduled_refund_never)
                    },
                    color = TaxiColors.Ink500,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    TaxiButton(
                        stringResource(Res.string.scheduled_accept_commitment),
                        { onRespond(offer.id, true) },
                        modifier = Modifier.weight(1f),
                        enabled = pendingAction == null,
                        loading = pendingAction.isPending(AppActionKind.RESPOND_TO_SCHEDULED_OFFER, offer.id),
                    )
                    TaxiButton(
                        stringResource(Res.string.decline),
                        { onRespond(offer.id, false) },
                        modifier = Modifier.weight(1f),
                        enabled = pendingAction == null,
                        style = TaxiButtonStyle.Secondary,
                    )
                }
            }
        }
    }
    Text(stringResource(Res.string.scheduled_upcoming_commitments), style = MaterialTheme.typography.titleLarge)
    if (state.scheduledCommitments.isEmpty()) {
        EmptyState(
            stringResource(Res.string.scheduled_no_commitments),
            stringResource(Res.string.scheduled_no_commitments_help),
        )
    }
    state.scheduledCommitments.forEach { commitment ->
        Surface(Modifier.fillMaxWidth(), shape = MaterialTheme.shapes.medium, color = TaxiColors.Surface0) {
            Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(commitment.scheduledFor, style = MaterialTheme.typography.titleMedium)
                    StatusPill(commitment.status, if (commitment.status == "ACTIVE") StatusTone.Success else StatusTone.Info)
                }
                Text(stringResource(Res.string.scheduled_protected_window, commitment.protectedFrom, commitment.protectedUntil))
                Text(stringResource(Res.string.scheduled_location_summary, commitment.pickup.address ?: stringResource(Res.string.pickup), commitment.destination.address ?: stringResource(Res.string.destination)))
                Text(stringResource(Res.string.scheduled_expected_driver_net, commitment.economics.expectedDriverNet, commitment.economics.currency))
                Text(stringResource(Res.string.scheduled_commitment_warning), color = TaxiColors.Warning600)
            }
        }
    }
}

@Composable
private fun TimedOfferCard(
    offer: org.example.taximobile.domain.drivers.DriverRideOffer,
    pickupSummary: String,
    distanceAndEta: String?,
    fare: String?,
    economicsDetails: List<String>,
    onAccept: () -> Unit,
    onDecline: () -> Unit,
    onExpired: () -> Unit,
    pendingAction: AppAction?,
    modifier: Modifier = Modifier,
) {
    var elapsedSeconds by remember(offer.id, offer.serverTimeAtFetch) { mutableIntStateOf(0) }
    val countdown = offerCountdown(offer, elapsedSeconds)
    val hapticFeedback = LocalHapticFeedback.current
    LaunchedEffect(offer.id) {
        // Use the platform action-oriented effect so device capability and the
        // user's haptic-feedback preference remain authoritative.
        hapticFeedback.performHapticFeedback(HapticFeedbackType.LongPress)
    }
    LaunchedEffect(offer.id, offer.serverTimeAtFetch) {
        while (true) {
            val current = offerCountdown(offer, elapsedSeconds)
            if (current == null) {
                onExpired()
                break
            }
            if (current.expired) {
                onExpired()
                break
            }
            delay(1_000)
            elapsedSeconds += 1
        }
    }
    OfferCard(
        pickupSummary = pickupSummary,
        distanceAndEta = distanceAndEta,
        fare = fare,
        details = economicsDetails,
        expiryLabel = when {
            countdown == null -> stringResource(Res.string.offer_timing_unavailable_refreshing)
            countdown.expired -> stringResource(Res.string.offer_expired_refreshing)
            else -> stringResource(Res.string.seconds_remaining, countdown.remainingSeconds)
        },
        expiryFraction = countdown?.remainingFraction,
        acceptEnabled = countdown?.expired == false && pendingAction == null,
        declineEnabled = pendingAction == null,
        acceptLoading = pendingAction.isPending(AppActionKind.RESPOND_TO_OFFER, "${offer.id}:accept"),
        declineLoading = pendingAction.isPending(AppActionKind.RESPOND_TO_OFFER, "${offer.id}:decline"),
        onAccept = onAccept,
        onDecline = onDecline,
        modifier = modifier,
    )
}

@Composable
private fun DriverCompletionControls(
    rideId: String,
    draft: DriverCoordinateDraft,
    pendingAction: AppAction?,
    locationRequestInFlight: Boolean,
    onRequestCurrentLocation: ((Coordinates?) -> Unit) -> Unit,
    onComplete: (String, Coordinates) -> Unit,
) {
    TaxiButton(
        stringResource(Res.string.load_completion_location),
        onClick = {
            draft.message = UiMessage(Res.string.completion_location_requesting)
            onRequestCurrentLocation { selected ->
                if (selected == null) {
                    draft.message = UiMessage(Res.string.completion_location_unavailable)
                } else {
                    draft.load(selected)
                    draft.message = UiMessage(Res.string.completion_location_loaded)
                }
            }
        },
        enabled = !locationRequestInFlight,
        loading = locationRequestInFlight,
        style = TaxiButtonStyle.Secondary,
    )
    draft.message?.let { ToastBanner(it.resolve()) }
    TaxiTextField(draft.latitude, { draft.latitude = it }, stringResource(Res.string.completion_latitude), keyboardType = KeyboardType.Decimal)
    TaxiTextField(draft.longitude, { draft.longitude = it }, stringResource(Res.string.completion_longitude), keyboardType = KeyboardType.Decimal)
    TaxiButton(
        stringResource(Res.string.complete_ride),
        { onComplete(rideId, requireNotNull(draft.coordinates)) },
        enabled = draft.coordinates != null && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.COMPLETE_DRIVER_RIDE, rideId),
    )
}

@Composable
private fun DriverAccountSheet(
    state: AppUiState.DriverReady,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    onBack: () -> Unit,
    onLogout: () -> Unit,
    onRegisterVehicle: (VehicleRegistration) -> Unit,
    onSelectVehicle: (String) -> Unit,
    onDeactivateVehicle: (String) -> Unit,
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit,
    onSelectRide: (String) -> Unit,
    onLoadAccountSecurity: () -> Unit,
    onCreateRecoveryCodes: (String) -> Unit,
    onAcknowledgeRecoveryCodes: () -> Unit,
    onRevokeAccountSession: (String) -> Unit,
    onChangeAccountPassword: (String, String) -> Unit,
) {
    TaxiButton(stringResource(Res.string.back_to_operations), onBack, style = TaxiButtonStyle.Tertiary)
    Text(stringResource(Res.string.driver_account), style = MaterialTheme.typography.displaySmall)
    state.displayName?.takeIf { it.isNotBlank() }?.let {
        Text(it, style = MaterialTheme.typography.titleMedium)
    }
    state.verificationStatus?.let {
        Text(
            stringResource(
                Res.string.driver_verification_value,
                stringResource(driverVerificationStatusResource(it)),
            )
        )
    }
    state.accountStatus?.let {
        Text(
            stringResource(
                Res.string.driver_account_status_value,
                stringResource(driverAccountStatusResource(it)),
            )
        )
    }
    state.earnings?.let { earnings ->
        Text(stringResource(Res.string.earnings), style = MaterialTheme.typography.titleMedium)
        FareBlock(earnings.net, earnings.currency, null, true, breakdown = listOf(
            FareBreakdownRow(stringResource(Res.string.fare_component_transport), "${earnings.transportFare} ${earnings.currency}"),
            FareBreakdownRow(stringResource(Res.string.fare_component_scheduling_surcharge), "${earnings.schedulingSurcharge} ${earnings.currency}"),
            FareBreakdownRow(stringResource(Res.string.fare_component_operator_service_fee), "${earnings.operatorServiceFee} ${earnings.currency}"),
            FareBreakdownRow(stringResource(Res.string.operator_allocation), "${earnings.operatorAllocation} ${earnings.currency}"),
            FareBreakdownRow(stringResource(Res.string.gross), "${earnings.gross} ${earnings.currency}"),
            FareBreakdownRow(stringResource(Res.string.fees), "${earnings.fees} ${earnings.currency}"),
            FareBreakdownRow(stringResource(Res.string.adjustments), "${earnings.adjustments} ${earnings.currency}"),
        ))
        Text(stringResource(Res.string.settled_ride_count, earnings.count))
        earnings.settledThrough?.let {
            Text(stringResource(Res.string.settled_through_value, ltrIsolate(it)))
        }
        earnings.items.forEach { earning -> DriverEarningCard(earning) }
    }
    state.cooperativeMembership?.let { membership ->
        Text(stringResource(Res.string.cooperative_membership), style = MaterialTheme.typography.titleMedium)
        Text(membership.cooperativeName, style = MaterialTheme.typography.bodyLarge)
        Text(stringResource(Res.string.membership_status_value, membership.status))
        membership.membershipNumber?.let {
            Text(stringResource(Res.string.membership_number_value, ltrIsolate(it)))
        }
        membership.joinedAt?.let {
            Text(stringResource(Res.string.membership_joined_value, ltrIsolate(it)))
        }
    }
    if (state.credentials.isNotEmpty()) {
        Text(stringResource(Res.string.professional_credentials), style = MaterialTheme.typography.titleMedium)
        state.credentials.forEach { credential ->
            val title = stringResource(
                    Res.string.credential_summary,
                    ltrIsolate(credential.type),
                    ltrIsolate(credential.status),
            )
            val detail = credential.expiresAt?.let {
                stringResource(Res.string.credential_expires_value, ltrIsolate(it))
            } ?: credential.issuedAt?.let {
                stringResource(Res.string.credential_issued_value, ltrIsolate(it))
            }
            DriverDocumentCard(
                title = title,
                status = stringResource(driverCredentialStatusResource(credential.status)),
                detail = detail,
            )
        }
    }
    DriverVehicleSection(
        state.vehicles,
        state.activeVehicleId,
        pendingAction,
        completedAction,
        onRegisterVehicle,
        onSelectVehicle,
        onDeactivateVehicle,
    )
    state.selectedHistoryRide?.let {
        DriverRideHistoryDetail(it, state.selectedHistoryRating)
    }
    if (state.rideHistory.isNotEmpty()) {
        Text(stringResource(Res.string.recent_rides), style = MaterialTheme.typography.titleMedium)
        state.rideHistory.take(10).forEach { ride ->
            TaxiButton(
                label = stringResource(
                    Res.string.ride_history_item,
                    stringResource(ride.status.passengerStatusResource()),
                    ltrIsolate(ride.id.take(8)),
                ),
                onClick = { onSelectRide(ride.id) },
                enabled = pendingAction == null,
                loading = pendingAction.isPending(AppActionKind.LOAD_DRIVER_RIDE, ride.id),
                modifier = Modifier.testTag("driver-history-${ride.id}"),
                style = TaxiButtonStyle.Tertiary,
            )
        }
    }
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
private fun DriverSafetySheet(
    state: AppUiState.DriverReady,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    onBack: () -> Unit,
    onCreateSafetyReport: (String, SafetyCategory, String) -> Unit,
) {
    TaxiButton(stringResource(Res.string.back_to_operations), onBack, style = TaxiButtonStyle.Tertiary)
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
private fun DriverRideHistoryDetail(ride: RideSummary, rating: RideRating?) {
    Text(stringResource(Res.string.ride_details), style = MaterialTheme.typography.titleMedium)
    StatusPill(
        stringResource(ride.status.passengerStatusResource()),
        ride.status.passengerStatusTone(),
    )
    Text(stringResource(Res.string.ride_identifier, ltrIsolate(ride.id)))
    ride.pickup?.let {
        Text(stringResource(Res.string.ride_location_line, stringResource(Res.string.pickup), driverHistoryLocationLabel(it)))
    }
    ride.destination?.let {
        Text(stringResource(Res.string.ride_location_line, stringResource(Res.string.destination), driverHistoryLocationLabel(it)))
    }
    rating?.let {
        Text(stringResource(Res.string.passenger_feedback), style = MaterialTheme.typography.titleMedium)
        Text(stringResource(Res.string.passenger_rating_value, it.score))
        it.comment?.trim()?.takeIf(String::isNotEmpty)?.let { comment ->
            Text(stringResource(Res.string.rating_comment_value, comment))
        }
    }
}

private fun driverHistoryLocationLabel(location: Coordinates): String =
    location.address?.trim()?.takeIf(String::isNotEmpty)
        ?: ltrIsolate("${location.latitude}, ${location.longitude}")

@Composable
private fun DriverEarningCard(earning: org.example.taximobile.domain.drivers.DriverEarningItem) {
    TaxiCard {
        Text(
            stringResource(
                Res.string.earning_row,
                ltrIsolate(earning.rideId.take(8)),
                earning.net,
                earning.currency,
                ltrIsolate(earning.settledAt),
            ),
            style = MaterialTheme.typography.titleSmall,
        )
        Text(
            stringResource(
                Res.string.earning_transport_value,
                earning.transportFare,
                earning.currency,
            ),
            style = MaterialTheme.typography.bodyMedium,
        )
        if (earning.schedulingSurcharge.any { it in '1'..'9' }) {
            Text(
                stringResource(
                    Res.string.earning_scheduling_value,
                    earning.schedulingSurcharge,
                    earning.currency,
                ),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        Text(
            stringResource(
                Res.string.earning_operator_fee_value,
                earning.operatorServiceFee,
                earning.currency,
            ),
            style = MaterialTheme.typography.bodyMedium,
        )
        earning.operatorFeeFundingMode?.let { mode ->
            Text(
                stringResource(
                    when (mode) {
                        "DRIVER_SETTLEMENT_DEDUCTION" -> Res.string.operator_fee_funding_driver
                        "PASSENGER_SURCHARGE" -> Res.string.operator_fee_funding_passenger
                        else -> Res.string.operator_fee_funding_unknown
                    }
                ),
                style = MaterialTheme.typography.bodySmall,
                color = TaxiColors.Ink500,
            )
        }
    }
}

@Composable
private fun DriverVehicleSection(
    vehicles: List<DriverVehicle>,
    activeVehicleId: String?,
    pendingAction: AppAction?,
    completedAction: AppActionCompletion?,
    onRegister: (VehicleRegistration) -> Unit,
    onSelect: (String) -> Unit,
    onDeactivate: (String) -> Unit,
) {
    var make by remember { mutableStateOf("") }
    var model by remember { mutableStateOf("") }
    var year by remember { mutableStateOf("") }
    var color by remember { mutableStateOf("") }
    var registrationNumber by remember { mutableStateOf("") }
    var taxiIdentifier by remember { mutableStateOf("") }
    var passengerCapacity by remember { mutableStateOf("") }
    LaunchedEffect(completedAction?.sequence) {
        if (completedAction.confirms(AppActionKind.REGISTER_DRIVER_VEHICLE)) {
            make = ""
            model = ""
            year = ""
            color = ""
            registrationNumber = ""
            taxiIdentifier = ""
            passengerCapacity = ""
        }
    }
    Text(stringResource(Res.string.vehicles), style = MaterialTheme.typography.titleMedium)
    if (completedAction.confirms(AppActionKind.REGISTER_DRIVER_VEHICLE)) {
        SuccessConfirmation(
            stringResource(Res.string.vehicle_registration_sent_confirmation),
            requireNotNull(completedAction).sequence,
        )
    }
    if (vehicles.isEmpty()) {
        EmptyState(
            title = stringResource(Res.string.no_vehicles_title),
            body = stringResource(Res.string.register_vehicle_help),
        )
    }
    vehicles.forEach { vehicle ->
        TaxiCard(selected = vehicle.id == activeVehicleId) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                VehicleAssetFallback("${vehicle.make} ${vehicle.model}")
                Text(
                    stringResource(
                        Res.string.vehicle_summary,
                        vehicle.make,
                        vehicle.model,
                        vehicle.color,
                        vehicleVerificationLabel(vehicle.verificationStatus),
                    ),
                    modifier = Modifier.weight(1f),
                )
            }
            if (vehicle.id == activeVehicleId) {
                StatusPill(stringResource(Res.string.selected_for_dispatch), StatusTone.Success)
            } else if (vehicle.status == "ACTIVE" && vehicle.verificationStatus == "VERIFIED") {
                TaxiButton(
                    stringResource(Res.string.select_vehicle),
                    { onSelect(vehicle.id) },
                    enabled = pendingAction == null,
                    loading = pendingAction.isPending(AppActionKind.SELECT_DRIVER_VEHICLE, vehicle.id),
                    style = TaxiButtonStyle.Secondary,
                )
            }
            if (vehicle.status == "ACTIVE") {
                TaxiButton(
                    stringResource(Res.string.deactivate_vehicle),
                    { onDeactivate(vehicle.id) },
                    enabled = pendingAction == null,
                    loading = pendingAction.isPending(AppActionKind.DEACTIVATE_DRIVER_VEHICLE, vehicle.id),
                    style = TaxiButtonStyle.Tertiary,
                )
            }
        }
    }
    TaxiTextField(make, { make = it }, stringResource(Res.string.vehicle_make))
    TaxiTextField(model, { model = it }, stringResource(Res.string.vehicle_model))
    TaxiTextField(year, { year = it.filter(Char::isDigit).take(4) }, stringResource(Res.string.vehicle_year), keyboardType = KeyboardType.Number)
    TaxiTextField(color, { color = it }, stringResource(Res.string.vehicle_color))
    TaxiTextField(registrationNumber, { registrationNumber = it }, stringResource(Res.string.registration_number))
    TaxiTextField(taxiIdentifier, { taxiIdentifier = it.take(64) }, stringResource(Res.string.taxi_identifier_optional))
    TaxiTextField(
        passengerCapacity,
        { passengerCapacity = it.filter(Char::isDigit).take(2) },
        stringResource(Res.string.passenger_capacity_optional),
        keyboardType = KeyboardType.Number,
    )
    val validYear = year.toIntOrNull()?.takeIf { it in 1900..2100 }
    val validCapacity = passengerCapacity.toIntOrNull()?.takeIf { it in 1..12 }
    TaxiButton(
        stringResource(Res.string.register_vehicle),
        onClick = {
            onRegister(
                VehicleRegistration(
                    make = make.trim(),
                    model = model.trim(),
                    year = requireNotNull(validYear),
                    color = color.trim(),
                    registrationNumber = registrationNumber.trim(),
                    taxiIdentifier = taxiIdentifier.trim().ifBlank { null },
                    passengerCapacity = validCapacity,
                ),
            )
        },
        enabled = make.isNotBlank() && model.isNotBlank() && validYear != null && color.isNotBlank() &&
            registrationNumber.isNotBlank() &&
            (passengerCapacity.isBlank() || validCapacity != null) && pendingAction == null,
        loading = pendingAction.isPending(AppActionKind.REGISTER_DRIVER_VEHICLE),
    )
}

@Composable
private fun DriverInboxSheet(
    notifications: List<AppNotification>,
    pendingAction: AppAction?,
    onBack: () -> Unit,
    onMarkRead: (String) -> Unit,
) {
    TaxiButton(stringResource(Res.string.back_to_operations), onBack, style = TaxiButtonStyle.Tertiary)
    Text(stringResource(Res.string.inbox), style = MaterialTheme.typography.displaySmall)
    NotificationInboxSection(notifications, pendingAction, onMarkRead)
}

@Composable
private fun vehicleVerificationLabel(status: String): String = stringResource(
    when (status) {
        "PENDING" -> Res.string.vehicle_verification_pending
        "VERIFIED" -> Res.string.vehicle_verification_verified
        "REJECTED" -> Res.string.vehicle_verification_rejected
        else -> Res.string.vehicle_verification_unknown
    }
)

private fun driverCredentialStatusResource(status: String): StringResource = when (status) {
    "VERIFIED" -> Res.string.verification_verified
    "REJECTED" -> Res.string.verification_rejected
    "PENDING", "SUBMITTED", "UNDER_REVIEW" -> Res.string.verification_under_review
    else -> Res.string.verification_unknown
}

private fun driverServiceTypeResource(serviceType: String): StringResource = when (serviceType) {
    "FIXED_ROUTE" -> Res.string.service_type_fixed_route
    "SCHEDULED" -> Res.string.service_type_scheduled
    else -> Res.string.service_type_on_demand
}

internal fun DriverAvailabilityStatus.driverAvailabilityResource(): StringResource = when (this) {
    DriverAvailabilityStatus.OFFLINE -> Res.string.driver_status_offline
    DriverAvailabilityStatus.AVAILABLE -> Res.string.driver_status_available
    DriverAvailabilityStatus.PAUSED -> Res.string.driver_status_paused
    DriverAvailabilityStatus.OFFERED_RIDE -> Res.string.driver_status_offered_ride
    DriverAvailabilityStatus.EN_ROUTE -> Res.string.driver_status_en_route
    DriverAvailabilityStatus.AT_PICKUP -> Res.string.driver_status_at_pickup
    DriverAvailabilityStatus.ON_RIDE -> Res.string.driver_status_on_ride
}

internal fun DriverAvailabilityStatus.driverAvailabilityTone(): StatusTone = when (this) {
    DriverAvailabilityStatus.AVAILABLE -> StatusTone.Success
    DriverAvailabilityStatus.OFFERED_RIDE -> StatusTone.Warning
    DriverAvailabilityStatus.EN_ROUTE, DriverAvailabilityStatus.AT_PICKUP, DriverAvailabilityStatus.ON_RIDE -> StatusTone.Info
    DriverAvailabilityStatus.OFFLINE, DriverAvailabilityStatus.PAUSED -> StatusTone.Neutral
}
