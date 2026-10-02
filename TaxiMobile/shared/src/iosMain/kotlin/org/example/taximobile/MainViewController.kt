package org.example.taximobile

import androidx.compose.ui.window.ComposeUIViewController
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import org.example.taximobile.feature.realtime.canListenForLiveUpdates
import kotlin.io.encoding.Base64
import org.example.taximobile.app.AppRole
import org.example.taximobile.domain.drivers.DriverDocumentUpload
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionGate
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.AppActionCompletion
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.app.hasAuthenticatedSession
import org.example.taximobile.feature.app.clearVisibleRecoveryCodes
import org.example.taximobile.feature.connectivity.AppStatePresentation
import org.example.taximobile.feature.connectivity.ConnectivityRecoveryPolicy
import org.example.taximobile.feature.connectivity.ConnectivityStatus
import org.example.taximobile.feature.connectivity.ForegroundRecoveryPolicy
import org.example.taximobile.feature.notifications.PushRefreshSignals
import org.example.taximobile.feature.location.ForegroundDriverLocationPolicy
import org.example.taximobile.feature.location.ForegroundDriverLocationResultGuard
import org.example.taximobile.feature.location.foregroundDriverLocationUnavailableMessage

fun MainViewController(
    apiBaseUrl: String = "https://api.taximobile.invalid",
    mapStyleUrl: String = "https://maps.taximobile.invalid/style.json",
    appRole: AppRole = AppRole.PASSENGER,
    appVersion: String = "1.0.0",
    appBuild: String = "1",
    showManualCoordinateEntry: Boolean = false,
    requestDriverDocument: (((String?, String?, String?) -> Unit) -> Unit)? = null,
) = ComposeUIViewController {
    val dependencies = remember {
        IosAppDependencies(apiBaseUrl, appRole, appVersion, appBuild)
    }
    val currentLocationRequester = remember { IosCurrentLocationRequester() }
    val connectivityObserver = remember { IosConnectivityObserver() }
    IosPushRegistration.attach(dependencies.appCoordinator)
    var presentation by remember { mutableStateOf(AppStatePresentation(AppUiState.RestoringSession)) }
    var connectivityStatus by remember { mutableStateOf(ConnectivityStatus.UNKNOWN) }
    var pendingAction by remember { mutableStateOf<AppAction?>(null) }
    var completedAction by remember { mutableStateOf<AppActionCompletion?>(null) }
    var completionSequence by remember { mutableStateOf(0L) }
    var appInForeground by remember { mutableStateOf(true) }
    var automaticLocationRequestInFlight by remember { mutableStateOf(false) }
    val recoveryPolicy = remember { ConnectivityRecoveryPolicy() }
    val foregroundRecoveryPolicy = remember { ForegroundRecoveryPolicy() }
    val foregroundDriverLocationPolicy = remember { ForegroundDriverLocationPolicy() }
    val foregroundDriverLocationResultGuard = remember { ForegroundDriverLocationResultGuard() }
    val actionGate = remember { AppActionGate() }
    val scope = rememberCoroutineScope()
    DisposableEffect(foregroundDriverLocationResultGuard) {
        onDispose { foregroundDriverLocationResultGuard.invalidate() }
    }
    fun submitAction(
        key: AppAction,
        recoverFailure: Boolean = true,
        action: suspend () -> AppUiState,
    ) {
        if (!actionGate.tryStart(key)) return
        foregroundDriverLocationResultGuard.invalidate()
        completedAction = null
        pendingAction = key
        scope.launch {
            try {
                presentation = if (recoverFailure) {
                    presentation.performAuthenticatedAction(
                        action = action,
                        restore = dependencies.appCoordinator::restore,
                        onBackendConfirmed = {
                            completionSequence += 1
                            completedAction = AppActionCompletion(completionSequence, key)
                        },
                    )
                } else {
                    presentation.accept(action())
                }
            } finally {
                actionGate.finish(key)
                pendingAction = actionGate.current
            }
        }
    }
    LifecycleEventEffect(Lifecycle.Event.ON_STOP) {
        foregroundDriverLocationResultGuard.invalidate()
        appInForeground = false
        foregroundRecoveryPolicy.onBackground()
    }
    LifecycleEventEffect(Lifecycle.Event.ON_START) {
        appInForeground = true
        if (
            foregroundRecoveryPolicy.shouldRefreshOnForeground() &&
            presentation.state.hasAuthenticatedSession()
        ) {
            scope.launch {
                presentation = presentation.accept(dependencies.appCoordinator.restore())
            }
        }
    }
    LaunchedEffect(dependencies, appRole, currentLocationRequester) {
        while (true) {
            val driverState = presentation.state as? AppUiState.DriverReady
            val shouldRequest = appRole == AppRole.DRIVER && foregroundDriverLocationPolicy.shouldRequest(
                nowMillis = kotlin.time.Clock.System.now().toEpochMilliseconds(),
                availability = driverState?.availability,
                appInForeground = appInForeground,
                networkUsable = connectivityStatus != ConnectivityStatus.UNAVAILABLE,
                platformRequestInFlight = automaticLocationRequestInFlight,
                appActionInFlight = pendingAction != null,
            )
            if (shouldRequest) {
                val request = foregroundDriverLocationResultGuard.capture(checkNotNull(driverState))
                automaticLocationRequestInFlight = true
                val started = currentLocationRequester.requestAuthorized { location ->
                    automaticLocationRequestInFlight = false
                    if (!foregroundDriverLocationResultGuard.canApply(
                            request, presentation.state, appInForeground,
                            connectivityStatus != ConnectivityStatus.UNAVAILABLE,
                            pendingAction != null,
                        )) return@requestAuthorized
                    if (location == null) {
                        foregroundDriverLocationPolicy.recordUnavailable(
                            kotlin.time.Clock.System.now().toEpochMilliseconds()
                        )
                        presentation = presentation.copy(
                            connectionIssue = foregroundDriverLocationUnavailableMessage()
                        )
                    } else {
                        submitAction(AppAction(AppActionKind.UPDATE_DRIVER_LOCATION)) {
                            dependencies.appCoordinator.updateDriverLocation(location)
                        }
                    }
                }
                if (!started) {
                    automaticLocationRequestInFlight = false
                    foregroundDriverLocationPolicy.recordUnavailable(
                        kotlin.time.Clock.System.now().toEpochMilliseconds()
                    )
                }
            }
            delay(1_000)
        }
    }
    DisposableEffect(connectivityObserver) {
        onDispose { connectivityObserver.close() }
    }
    LaunchedEffect(dependencies) {
        presentation = presentation.accept(dependencies.appCoordinator.restore())
    }
    LaunchedEffect(connectivityObserver) {
        connectivityObserver.status.collect { observedStatus ->
            if (observedStatus != connectivityStatus) foregroundDriverLocationResultGuard.invalidate()
            connectivityStatus = observedStatus
            if (recoveryPolicy.shouldRefresh(observedStatus)) {
                presentation = presentation.accept(dependencies.appCoordinator.restore())
            }
        }
    }
    LaunchedEffect(dependencies) {
        PushRefreshSignals.hints.collect {
            if (presentation.state.hasAuthenticatedSession()) {
                presentation = presentation.accept(dependencies.appCoordinator.restore())
            }
        }
    }
    LaunchedEffect(presentation.state.hasAuthenticatedSession()) {
        if (presentation.state.hasAuthenticatedSession()) IosPushRegistration.retry()
    }
    val liveUpdatesEnabled = canListenForLiveUpdates(
        presentation.state, appInForeground, connectivityStatus, pendingAction,
    )
    LaunchedEffect(dependencies, liveUpdatesEnabled) {
        if (liveUpdatesEnabled) {
            dependencies.appCoordinator.listenForLiveUpdates {
                if (!canListenForLiveUpdates(
                        presentation.state, appInForeground, connectivityStatus, pendingAction,
                    )) return@listenForLiveUpdates
                val owner = dependencies.appCoordinator.liveSessionLifetime.value
                val restored = dependencies.appCoordinator.restore()
                currentCoroutineContext().ensureActive()
                if (owner == dependencies.appCoordinator.liveSessionLifetime.value &&
                    canListenForLiveUpdates(
                        presentation.state, appInForeground, connectivityStatus, pendingAction,
                    )) {
                    presentation = presentation.accept(restored)
                }
            }
        }
    }
    App(
        appRole = appRole,
        state = presentation.state,
        pendingAction = pendingAction,
        completedAction = completedAction,
        connectivityStatus = connectivityStatus,
        connectionIssue = presentation.connectionIssue,
        mapStyleUrl = mapStyleUrl,
        showManualCoordinateEntry = showManualCoordinateEntry,
        onLogin = { identifier, password -> scope.launch {
            presentation = AppStatePresentation(AppUiState.RestoringSession)
            presentation = presentation.accept(
                dependencies.appCoordinator.login(identifier, password, "iOS ${appRole.name.lowercase()} app"),
            )
        } },
        onRegister = { displayName, email, phoneNumber, password -> scope.launch {
            presentation = AppStatePresentation(AppUiState.RegisteringAccount)
            presentation = presentation.accept(
                dependencies.appCoordinator.register(displayName, email, phoneNumber, password),
            )
        } },
        onRecoverAccount = { identifier, recoveryCode, newPassword -> scope.launch {
            presentation = AppStatePresentation(AppUiState.RecoveringAccount)
            presentation = presentation.accept(
                dependencies.appCoordinator.recoverAccount(identifier, recoveryCode, newPassword),
            )
        } },
        onLoadAccountSecurity = {
            submitAction(AppAction(AppActionKind.LOAD_ACCOUNT_SECURITY), recoverFailure = false) {
                dependencies.appCoordinator.loadAccountSecurity()
            }
        },
        onCreateRecoveryCodes = { currentPassword ->
            submitAction(AppAction(AppActionKind.CREATE_RECOVERY_CODES), recoverFailure = false) {
                dependencies.appCoordinator.createRecoveryCodes(currentPassword)
            }
        },
        onAcknowledgeRecoveryCodes = {
            presentation = presentation.copy(
                state = presentation.state.clearVisibleRecoveryCodes(),
            )
        },
        onRevokeAccountSession = { sessionId ->
            submitAction(
                AppAction(AppActionKind.REVOKE_ACCOUNT_SESSION, sessionId),
                recoverFailure = false,
            ) { dependencies.appCoordinator.revokeAccountSession(sessionId) }
        },
        onChangeAccountPassword = { currentPassword, newPassword ->
            submitAction(AppAction(AppActionKind.CHANGE_ACCOUNT_PASSWORD), recoverFailure = false) {
                dependencies.appCoordinator.changeAccountPassword(currentPassword, newPassword)
            }
        },
        onRetry = { scope.launch {
            presentation = AppStatePresentation(AppUiState.RestoringSession)
            presentation = presentation.accept(dependencies.appCoordinator.restore())
        } },
        onRefresh = {
            submitAction(AppAction(AppActionKind.REFRESH), recoverFailure = false) {
                dependencies.appCoordinator.restore()
            }
        },
        onLogout = {
            submitAction(AppAction(AppActionKind.LOGOUT), recoverFailure = false) {
                dependencies.appCoordinator.logout()
            }
        },
        onRequestCurrentLocation = currentLocationRequester::request,
        onSetDriverOnline = { online, cityId, serviceType -> submitAction(AppAction(AppActionKind.SET_DRIVER_AVAILABILITY)) {
            dependencies.appCoordinator.changeDriverAvailability(
                online = online,
                cityId = cityId,
                serviceType = serviceType ?: "ON_DEMAND",
            )
        } },
        onUpdateDriverLocation = { location -> submitAction(AppAction(AppActionKind.UPDATE_DRIVER_LOCATION)) { dependencies.appCoordinator.updateDriverLocation(location) } },
        onRegisterDriverVehicle = { vehicle -> submitAction(AppAction(AppActionKind.REGISTER_DRIVER_VEHICLE)) { dependencies.appCoordinator.registerDriverVehicle(vehicle) } },
        onSelectDriverVehicle = { vehicleId -> submitAction(AppAction(AppActionKind.SELECT_DRIVER_VEHICLE, vehicleId)) { dependencies.appCoordinator.selectDriverVehicle(vehicleId) } },
        onDeactivateDriverVehicle = { vehicleId -> submitAction(AppAction(AppActionKind.DEACTIVATE_DRIVER_VEHICLE, vehicleId)) { dependencies.appCoordinator.deactivateDriverVehicle(vehicleId) } },
        onSearchPlaces = { cityId, query ->
            submitAction(
                AppAction(AppActionKind.SEARCH_PLACES, cityId),
                recoverFailure = false,
            ) { dependencies.appCoordinator.searchPlaces(cityId, query) }
        },
        onReversePlace = { cityId, coordinate ->
            submitAction(
                AppAction(AppActionKind.REVERSE_PLACE, cityId),
                recoverFailure = false,
            ) { dependencies.appCoordinator.reversePlace(cityId, coordinate) }
        },
        onEstimateRide = { pickup, destination -> submitAction(AppAction(AppActionKind.ESTIMATE_RIDE)) { dependencies.appCoordinator.estimateRide(pickup, destination) } },
        onRequestRide = { pickup, destination, paymentMethod -> submitAction(AppAction(AppActionKind.REQUEST_RIDE)) { dependencies.appCoordinator.requestRide(pickup, destination, paymentMethod) } },
        onLoadFixedRoutes = { cityId -> submitAction(AppAction(AppActionKind.LOAD_FIXED_ROUTES, cityId)) { dependencies.appCoordinator.loadFixedRoutes(cityId) } },
        onEstimateFixedRoute = { directionId -> submitAction(AppAction(AppActionKind.ESTIMATE_FIXED_ROUTE, directionId)) { dependencies.appCoordinator.estimateFixedRoute(directionId) } },
        onRequestFixedRoute = { directionId, paymentMethod -> submitAction(AppAction(AppActionKind.REQUEST_FIXED_ROUTE, directionId)) { dependencies.appCoordinator.requestFixedRoute(directionId, paymentMethod) } },
        onEstimateScheduledPointToPoint = { scheduledFor, cityId, pickup, destination -> submitAction(AppAction(AppActionKind.ESTIMATE_SCHEDULED_BOOKING)) { dependencies.appCoordinator.estimateScheduledPointToPoint(scheduledFor, cityId, pickup, destination) } },
        onEstimateScheduledFixedRoute = { scheduledFor, directionId -> submitAction(AppAction(AppActionKind.ESTIMATE_SCHEDULED_BOOKING, directionId)) { dependencies.appCoordinator.estimateScheduledFixedRoute(scheduledFor, directionId) } },
        onSchedulePointToPoint = { scheduledFor, cityId, pickup, destination, note, estimate -> submitAction(AppAction(AppActionKind.CREATE_SCHEDULED_BOOKING)) { dependencies.appCoordinator.schedulePointToPoint(scheduledFor, cityId, pickup, destination, note, estimate) } },
        onScheduleFixedRoute = { scheduledFor, directionId, note, estimate -> submitAction(AppAction(AppActionKind.CREATE_SCHEDULED_BOOKING)) { dependencies.appCoordinator.scheduleFixedRoute(scheduledFor, directionId, note, estimate) } },
        onCancelScheduledBooking = { bookingId -> submitAction(AppAction(AppActionKind.CANCEL_SCHEDULED_BOOKING, bookingId)) { dependencies.appCoordinator.cancelScheduledBooking(bookingId) } },
        onSubmitManualTransfer = { rideId, payerReference -> submitAction(AppAction(AppActionKind.SUBMIT_MANUAL_TRANSFER, rideId)) { dependencies.appCoordinator.submitManualTransfer(rideId, payerReference) } },
        onCancelRide = { rideId -> submitAction(AppAction(AppActionKind.CANCEL_RIDE, rideId)) { dependencies.appCoordinator.cancelRide(rideId) } },
        onSendRideCoordination = { rideId, code -> submitAction(AppAction(AppActionKind.SEND_RIDE_COORDINATION, "$rideId:${code.name}")) { dependencies.appCoordinator.sendRideCoordinationMessage(rideId, code) } },
        onSelectPassengerRide = { rideId -> submitAction(AppAction(AppActionKind.LOAD_PASSENGER_RIDE, rideId)) { dependencies.appCoordinator.loadPassengerRideHistoryDetail(rideId) } },
        onSelectDriverRide = { rideId -> submitAction(AppAction(AppActionKind.LOAD_DRIVER_RIDE, rideId)) { dependencies.appCoordinator.loadDriverRideHistoryDetail(rideId) } },
        onUpdatePassengerProfile = { displayName -> submitAction(AppAction(AppActionKind.UPDATE_PASSENGER_PROFILE)) { dependencies.appCoordinator.updatePassengerProfile(displayName) } },
        onSubmitRating = { rideId, score, comment -> submitAction(AppAction(AppActionKind.SUBMIT_RATING, rideId)) { dependencies.appCoordinator.submitRideRating(rideId, score, comment) } },
        onCreateSupportTicket = { category, subject, description, rideId -> submitAction(AppAction(AppActionKind.CREATE_SUPPORT_TICKET)) { dependencies.appCoordinator.createSupportTicket(category, subject, description, rideId) } },
        onCreateSafetyReport = { rideId, category, description -> submitAction(AppAction(AppActionKind.CREATE_SAFETY_REPORT)) { dependencies.appCoordinator.createSafetyReport(rideId, category, description) } },
        onRespondToOffer = { offerId, accept ->
            val response = if (accept) "accept" else "decline"
            submitAction(AppAction(AppActionKind.RESPOND_TO_OFFER, "$offerId:$response")) {
                dependencies.appCoordinator.respondToOffer(offerId, accept)
            }
        },
        onSetScheduledOfferPreference = { cityId, enabled -> submitAction(AppAction(AppActionKind.SET_SCHEDULED_OFFER_PREFERENCE, cityId)) { dependencies.appCoordinator.setScheduledOfferPreference(cityId, enabled) } },
        onRespondToScheduledOffer = { offerId, accept -> submitAction(AppAction(AppActionKind.RESPOND_TO_SCHEDULED_OFFER, offerId)) { dependencies.appCoordinator.respondToScheduledOffer(offerId, accept) } },
        onAdvanceDriverRide = { rideId, action -> submitAction(AppAction(AppActionKind.ADVANCE_DRIVER_RIDE, rideId)) { dependencies.appCoordinator.advanceDriverRide(rideId, action) } },
        onCancelDriverRide = { rideId, reason -> submitAction(AppAction(AppActionKind.CANCEL_DRIVER_RIDE, rideId)) { dependencies.appCoordinator.cancelDriverRide(rideId, reason) } },
        onCompleteDriverRide = { rideId, location -> submitAction(AppAction(AppActionKind.COMPLETE_DRIVER_RIDE, rideId)) { dependencies.appCoordinator.completeDriverRide(rideId, location) } },
        onSettleDriverCash = { rideId -> submitAction(AppAction(AppActionKind.SETTLE_DRIVER_CASH, rideId)) { dependencies.appCoordinator.settleDriverCash(rideId) } },
        onApplyToDrive = { displayName -> submitAction(AppAction(AppActionKind.APPLY_TO_DRIVE)) { dependencies.appCoordinator.applyToDrive(displayName) } },
        onSubmitDriverVerification = { submitAction(AppAction(AppActionKind.SUBMIT_DRIVER_VERIFICATION)) { dependencies.appCoordinator.submitDriverVerification() } },
        onCreateDriverCityApplication = { cityId, displayName -> submitAction(AppAction(AppActionKind.CREATE_DRIVER_CITY_APPLICATION, cityId)) { dependencies.appCoordinator.createDriverCityApplication(cityId, displayName) } },
        onSelectDriverCityApplication = { applicationId, displayName -> submitAction(AppAction(AppActionKind.SELECT_DRIVER_CITY_APPLICATION, applicationId)) { dependencies.appCoordinator.selectDriverCityApplication(applicationId, displayName) } },
        onSaveDriverCityApplication = { applicationId, version, displayName, answers, evidence, removeAnswers, removeEvidence -> submitAction(AppAction(AppActionKind.SAVE_DRIVER_CITY_APPLICATION, applicationId)) {
            dependencies.appCoordinator.saveDriverCityApplication(applicationId, version, displayName, answers, evidence, removeAnswers, removeEvidence)
        } },
        onSubmitDriverCityApplication = { applicationId, displayName -> submitAction(AppAction(AppActionKind.SUBMIT_DRIVER_CITY_APPLICATION, applicationId)) { dependencies.appCoordinator.submitDriverCityApplication(applicationId, displayName) } },
        onWithdrawDriverCityApplication = { applicationId, displayName -> submitAction(AppAction(AppActionKind.WITHDRAW_DRIVER_CITY_APPLICATION, applicationId)) { dependencies.appCoordinator.withdrawDriverCityApplication(applicationId, displayName) } },
        driverDocumentPickerAvailable = requestDriverDocument != null,
        onUploadDriverApplicationDocument = {
                applicationId, requirementItemId, expectedVersion, displayName ->
            requestDriverDocument?.invoke selected@ { fileName, mediaType, base64Content ->
                if (
                    fileName == null ||
                    mediaType == null ||
                    mediaType !in IOS_DRIVER_DOCUMENT_MEDIA_TYPES ||
                    base64Content == null
                ) return@selected
                val bytes = runCatching { Base64.decode(base64Content) }.getOrNull()
                    ?.takeIf { it.isNotEmpty() && it.size <= IOS_DRIVER_DOCUMENT_MAX_BYTES }
                    ?: return@selected
                submitAction(
                    AppAction(
                        AppActionKind.UPLOAD_DRIVER_APPLICATION_DOCUMENT,
                        requirementItemId,
                    ),
                ) {
                    dependencies.appCoordinator.uploadDriverCityApplicationDocument(
                        applicationId = applicationId,
                        requirementItemId = requirementItemId,
                        expectedVersion = expectedVersion,
                        displayName = displayName,
                        document = DriverDocumentUpload(
                            fileName = fileName.take(160),
                            mediaType = mediaType,
                            bytes = bytes,
                        ),
                    )
                }
            }
        },
        onDeleteDriverApplicationDocument = {
                applicationId, documentId, expectedVersion, displayName ->
            submitAction(
                AppAction(AppActionKind.DELETE_DRIVER_APPLICATION_DOCUMENT, documentId),
            ) {
                dependencies.appCoordinator.deleteDriverCityApplicationDocument(
                    applicationId,
                    documentId,
                    expectedVersion,
                    displayName,
                )
            }
        },
        onRegisterApplicantVehicle = { displayName, vehicle -> submitAction(AppAction(AppActionKind.REGISTER_APPLICANT_VEHICLE)) { dependencies.appCoordinator.registerApplicantVehicle(displayName, vehicle) } },
        onMarkNotificationRead = { notificationId -> submitAction(AppAction(AppActionKind.MARK_NOTIFICATION_READ, notificationId)) { dependencies.appCoordinator.markNotificationRead(notificationId) } },
    )
}

private const val IOS_DRIVER_DOCUMENT_MAX_BYTES = 10 * 1024 * 1024
private val IOS_DRIVER_DOCUMENT_MEDIA_TYPES = setOf("application/pdf", "image/jpeg", "image/png")
