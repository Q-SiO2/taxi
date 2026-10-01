package org.example.taximobile

import android.os.Bundle
import android.net.Uri
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.tooling.preview.Preview
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import org.example.taximobile.app.AppRole
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
import org.example.taximobile.domain.drivers.DriverDocumentUpload

private data class PendingDocumentUpload(
    val applicationId: String,
    val requirementItemId: String,
    val expectedVersion: Int,
    val displayName: String,
)

class MainActivity : ComponentActivity() {
    private val currentLocationRequester = AndroidCurrentLocationRequester(this)
    private lateinit var connectivityObserver: AndroidConnectivityObserver

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)

        val role = AppRole.valueOf(BuildConfig.APP_ROLE)
        val dependencies = AndroidAppDependencies(this, role)
        connectivityObserver = AndroidConnectivityObserver(this)
        setContent {
            var presentation by remember {
                mutableStateOf(AppStatePresentation(AppUiState.RestoringSession))
            }
            var connectivityStatus by remember { mutableStateOf(ConnectivityStatus.UNKNOWN) }
            var pendingAction by remember { mutableStateOf<AppAction?>(null) }
            var completedAction by remember { mutableStateOf<AppActionCompletion?>(null) }
            var completionSequence by remember { mutableStateOf(0L) }
            var pendingDocumentUpload by remember { mutableStateOf<PendingDocumentUpload?>(null) }
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
            val documentLauncher = rememberLauncherForActivityResult(
                ActivityResultContracts.OpenDocument(),
            ) { uri ->
                val pending = pendingDocumentUpload
                pendingDocumentUpload = null
                if (uri != null && pending != null) {
                    submitAction(
                        AppAction(
                            AppActionKind.UPLOAD_DRIVER_APPLICATION_DOCUMENT,
                            pending.requirementItemId,
                        ),
                    ) {
                        val selected = withContext(Dispatchers.IO) {
                            readDriverDocument(uri)
                        }
                        dependencies.appCoordinator.uploadDriverCityApplicationDocument(
                            applicationId = pending.applicationId,
                            requirementItemId = pending.requirementItemId,
                            expectedVersion = pending.expectedVersion,
                            displayName = pending.displayName,
                            document = selected,
                        )
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
            LaunchedEffect(dependencies, role, currentLocationRequester) {
                while (true) {
                    val driverState = presentation.state as? AppUiState.DriverReady
                    val shouldRequest = role == AppRole.DRIVER && foregroundDriverLocationPolicy.shouldRequest(
                        nowMillis = System.currentTimeMillis(),
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
                                foregroundDriverLocationPolicy.recordUnavailable(System.currentTimeMillis())
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
                            foregroundDriverLocationPolicy.recordUnavailable(System.currentTimeMillis())
                        }
                    }
                    delay(1_000)
                }
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
                if (presentation.state.hasAuthenticatedSession() && FirebaseApp.getApps(this@MainActivity).isNotEmpty()) {
                    AndroidPushRegistration.retry(dependencies.appCoordinator)
                    // A successful registration is delivered to onRegistered,
                    // including when the current FID has not changed.
                    FirebaseMessaging.getInstance().register()
                }
            }
            LaunchedEffect(presentation.state is AppUiState.PassengerReady || presentation.state is AppUiState.DriverReady) {
                if (presentation.state is AppUiState.PassengerReady || presentation.state is AppUiState.DriverReady) {
                    dependencies.appCoordinator.listenForLiveUpdates {
                        presentation = presentation.accept(dependencies.appCoordinator.restore())
                    }
                }
            }
            App(
                appRole = role,
                state = presentation.state,
                pendingAction = pendingAction,
                completedAction = completedAction,
                connectivityStatus = connectivityStatus,
                connectionIssue = presentation.connectionIssue,
                mapStyleUrl = BuildConfig.MAP_STYLE_URL,
                showManualCoordinateEntry = BuildConfig.DEBUG,
                onLogin = { identifier, password ->
                    scope.launch {
                        presentation = AppStatePresentation(AppUiState.RestoringSession)
                        presentation = presentation.accept(dependencies.appCoordinator.login(
                            identifier = identifier,
                            password = password,
                            deviceLabel = "Android ${role.name.lowercase()} app",
                        ))
                    }
                },
                onRegister = { displayName, email, phoneNumber, password ->
                    scope.launch {
                        presentation = AppStatePresentation(AppUiState.RegisteringAccount)
                        presentation = presentation.accept(
                            dependencies.appCoordinator.register(displayName, email, phoneNumber, password),
                        )
                    }
                },
                onRecoverAccount = { identifier, recoveryCode, newPassword ->
                    scope.launch {
                        presentation = AppStatePresentation(AppUiState.RecoveringAccount)
                        presentation = presentation.accept(
                            dependencies.appCoordinator.recoverAccount(
                                identifier,
                                recoveryCode,
                                newPassword,
                            ),
                        )
                    }
                },
                onLoadAccountSecurity = {
                    submitAction(
                        AppAction(AppActionKind.LOAD_ACCOUNT_SECURITY),
                        recoverFailure = false,
                    ) { dependencies.appCoordinator.loadAccountSecurity() }
                },
                onCreateRecoveryCodes = { currentPassword ->
                    submitAction(
                        AppAction(AppActionKind.CREATE_RECOVERY_CODES),
                        recoverFailure = false,
                    ) { dependencies.appCoordinator.createRecoveryCodes(currentPassword) }
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
                    submitAction(
                        AppAction(AppActionKind.CHANGE_ACCOUNT_PASSWORD),
                        recoverFailure = false,
                    ) {
                        dependencies.appCoordinator.changeAccountPassword(
                            currentPassword,
                            newPassword,
                        )
                    }
                },
                onRetry = {
                    scope.launch {
                        presentation = AppStatePresentation(AppUiState.RestoringSession)
                        presentation = presentation.accept(dependencies.appCoordinator.restore())
                    }
                },
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
                onSetDriverOnline = { online, cityId, serviceType ->
                    submitAction(AppAction(AppActionKind.SET_DRIVER_AVAILABILITY)) {
                        dependencies.appCoordinator.changeDriverAvailability(
                            online = online,
                            cityId = cityId,
                            serviceType = serviceType ?: "ON_DEMAND",
                        )
                    }
                },
                onUpdateDriverLocation = { location ->
                    submitAction(AppAction(AppActionKind.UPDATE_DRIVER_LOCATION)) {
                        dependencies.appCoordinator.updateDriverLocation(location)
                    }
                },
                onRegisterDriverVehicle = { vehicle ->
                    submitAction(AppAction(AppActionKind.REGISTER_DRIVER_VEHICLE)) {
                        dependencies.appCoordinator.registerDriverVehicle(vehicle)
                    }
                },
                onSelectDriverVehicle = { vehicleId ->
                    submitAction(AppAction(AppActionKind.SELECT_DRIVER_VEHICLE, vehicleId)) {
                        dependencies.appCoordinator.selectDriverVehicle(vehicleId)
                    }
                },
                onDeactivateDriverVehicle = { vehicleId ->
                    submitAction(AppAction(AppActionKind.DEACTIVATE_DRIVER_VEHICLE, vehicleId)) {
                        dependencies.appCoordinator.deactivateDriverVehicle(vehicleId)
                    }
                },
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
                onEstimateRide = { pickup, destination ->
                    submitAction(AppAction(AppActionKind.ESTIMATE_RIDE)) {
                        dependencies.appCoordinator.estimateRide(pickup, destination)
                    }
                },
                onRequestRide = { pickup, destination, paymentMethod ->
                    submitAction(AppAction(AppActionKind.REQUEST_RIDE)) {
                        dependencies.appCoordinator.requestRide(pickup, destination, paymentMethod)
                    }
                },
                onLoadFixedRoutes = { cityId ->
                    submitAction(AppAction(AppActionKind.LOAD_FIXED_ROUTES, cityId)) {
                        dependencies.appCoordinator.loadFixedRoutes(cityId)
                    }
                },
                onEstimateFixedRoute = { directionId ->
                    submitAction(AppAction(AppActionKind.ESTIMATE_FIXED_ROUTE, directionId)) {
                        dependencies.appCoordinator.estimateFixedRoute(directionId)
                    }
                },
                onRequestFixedRoute = { directionId, paymentMethod ->
                    submitAction(AppAction(AppActionKind.REQUEST_FIXED_ROUTE, directionId)) {
                        dependencies.appCoordinator.requestFixedRoute(directionId, paymentMethod)
                    }
                },
                onEstimateScheduledPointToPoint = { scheduledFor, cityId, pickup, destination ->
                    submitAction(AppAction(AppActionKind.ESTIMATE_SCHEDULED_BOOKING)) {
                        dependencies.appCoordinator.estimateScheduledPointToPoint(scheduledFor, cityId, pickup, destination)
                    }
                },
                onEstimateScheduledFixedRoute = { scheduledFor, directionId ->
                    submitAction(AppAction(AppActionKind.ESTIMATE_SCHEDULED_BOOKING, directionId)) {
                        dependencies.appCoordinator.estimateScheduledFixedRoute(scheduledFor, directionId)
                    }
                },
                onSchedulePointToPoint = { scheduledFor, cityId, pickup, destination, note, estimate ->
                    submitAction(AppAction(AppActionKind.CREATE_SCHEDULED_BOOKING)) {
                        dependencies.appCoordinator.schedulePointToPoint(scheduledFor, cityId, pickup, destination, note, estimate)
                    }
                },
                onScheduleFixedRoute = { scheduledFor, directionId, note, estimate ->
                    submitAction(AppAction(AppActionKind.CREATE_SCHEDULED_BOOKING)) {
                        dependencies.appCoordinator.scheduleFixedRoute(scheduledFor, directionId, note, estimate)
                    }
                },
                onCancelScheduledBooking = { bookingId ->
                    submitAction(AppAction(AppActionKind.CANCEL_SCHEDULED_BOOKING, bookingId)) {
                        dependencies.appCoordinator.cancelScheduledBooking(bookingId)
                    }
                },
                onSubmitManualTransfer = { rideId, payerReference ->
                    submitAction(AppAction(AppActionKind.SUBMIT_MANUAL_TRANSFER, rideId)) {
                        dependencies.appCoordinator.submitManualTransfer(rideId, payerReference)
                    }
                },
                onCancelRide = { rideId ->
                    submitAction(AppAction(AppActionKind.CANCEL_RIDE, rideId)) {
                        dependencies.appCoordinator.cancelRide(rideId)
                    }
                },
                onSendRideCoordination = { rideId, code ->
                    submitAction(AppAction(AppActionKind.SEND_RIDE_COORDINATION, "$rideId:${code.name}")) {
                        dependencies.appCoordinator.sendRideCoordinationMessage(rideId, code)
                    }
                },
                onSelectPassengerRide = { rideId ->
                    submitAction(AppAction(AppActionKind.LOAD_PASSENGER_RIDE, rideId)) {
                        dependencies.appCoordinator.loadPassengerRideHistoryDetail(rideId)
                    }
                },
                onSelectDriverRide = { rideId ->
                    submitAction(AppAction(AppActionKind.LOAD_DRIVER_RIDE, rideId)) {
                        dependencies.appCoordinator.loadDriverRideHistoryDetail(rideId)
                    }
                },
                onUpdatePassengerProfile = { displayName ->
                    submitAction(AppAction(AppActionKind.UPDATE_PASSENGER_PROFILE)) {
                        dependencies.appCoordinator.updatePassengerProfile(displayName)
                    }
                },
                onSubmitRating = { rideId, score, comment ->
                    submitAction(AppAction(AppActionKind.SUBMIT_RATING, rideId)) {
                        dependencies.appCoordinator.submitRideRating(rideId, score, comment)
                    }
                },
                onCreateSupportTicket = { category, subject, description, rideId ->
                    submitAction(AppAction(AppActionKind.CREATE_SUPPORT_TICKET)) {
                        dependencies.appCoordinator.createSupportTicket(category, subject, description, rideId)
                    }
                },
                onCreateSafetyReport = { rideId, category, description ->
                    submitAction(AppAction(AppActionKind.CREATE_SAFETY_REPORT)) {
                        dependencies.appCoordinator.createSafetyReport(rideId, category, description)
                    }
                },
                onRespondToOffer = { offerId, accept ->
                    val response = if (accept) "accept" else "decline"
                    submitAction(AppAction(AppActionKind.RESPOND_TO_OFFER, "$offerId:$response")) {
                        dependencies.appCoordinator.respondToOffer(offerId, accept)
                    }
                },
                onSetScheduledOfferPreference = { cityId, enabled ->
                    submitAction(AppAction(AppActionKind.SET_SCHEDULED_OFFER_PREFERENCE, cityId)) {
                        dependencies.appCoordinator.setScheduledOfferPreference(cityId, enabled)
                    }
                },
                onRespondToScheduledOffer = { offerId, accept ->
                    submitAction(AppAction(AppActionKind.RESPOND_TO_SCHEDULED_OFFER, offerId)) {
                        dependencies.appCoordinator.respondToScheduledOffer(offerId, accept)
                    }
                },
                onAdvanceDriverRide = { rideId, action ->
                    submitAction(AppAction(AppActionKind.ADVANCE_DRIVER_RIDE, rideId)) {
                        dependencies.appCoordinator.advanceDriverRide(rideId, action)
                    }
                },
                onCancelDriverRide = { rideId, reason ->
                    submitAction(AppAction(AppActionKind.CANCEL_DRIVER_RIDE, rideId)) {
                        dependencies.appCoordinator.cancelDriverRide(rideId, reason)
                    }
                },
                onCompleteDriverRide = { rideId, location ->
                    submitAction(AppAction(AppActionKind.COMPLETE_DRIVER_RIDE, rideId)) {
                        dependencies.appCoordinator.completeDriverRide(rideId, location)
                    }
                },
                onSettleDriverCash = { rideId ->
                    submitAction(AppAction(AppActionKind.SETTLE_DRIVER_CASH, rideId)) {
                        dependencies.appCoordinator.settleDriverCash(rideId)
                    }
                },
                onApplyToDrive = { displayName ->
                    submitAction(AppAction(AppActionKind.APPLY_TO_DRIVE)) {
                        dependencies.appCoordinator.applyToDrive(displayName)
                    }
                },
                onSubmitDriverVerification = {
                    submitAction(AppAction(AppActionKind.SUBMIT_DRIVER_VERIFICATION)) {
                        dependencies.appCoordinator.submitDriverVerification()
                    }
                },
                onCreateDriverCityApplication = { cityId, displayName ->
                    submitAction(AppAction(AppActionKind.CREATE_DRIVER_CITY_APPLICATION, cityId)) {
                        dependencies.appCoordinator.createDriverCityApplication(cityId, displayName)
                    }
                },
                onSelectDriverCityApplication = { applicationId, displayName ->
                    submitAction(AppAction(AppActionKind.SELECT_DRIVER_CITY_APPLICATION, applicationId)) {
                        dependencies.appCoordinator.selectDriverCityApplication(applicationId, displayName)
                    }
                },
                onSaveDriverCityApplication = { applicationId, version, displayName, answers, evidence, removeAnswers, removeEvidence ->
                    submitAction(AppAction(AppActionKind.SAVE_DRIVER_CITY_APPLICATION, applicationId)) {
                        dependencies.appCoordinator.saveDriverCityApplication(
                            applicationId,
                            version,
                            displayName,
                            answers,
                            evidence,
                            removeAnswers,
                            removeEvidence,
                        )
                    }
                },
                onSubmitDriverCityApplication = { applicationId, displayName ->
                    submitAction(AppAction(AppActionKind.SUBMIT_DRIVER_CITY_APPLICATION, applicationId)) {
                        dependencies.appCoordinator.submitDriverCityApplication(applicationId, displayName)
                    }
                },
                onWithdrawDriverCityApplication = { applicationId, displayName ->
                    submitAction(AppAction(AppActionKind.WITHDRAW_DRIVER_CITY_APPLICATION, applicationId)) {
                        dependencies.appCoordinator.withdrawDriverCityApplication(applicationId, displayName)
                    }
                },
                driverDocumentPickerAvailable = true,
                onUploadDriverApplicationDocument = {
                        applicationId, requirementItemId, expectedVersion, displayName ->
                    if (pendingDocumentUpload == null) {
                        pendingDocumentUpload = PendingDocumentUpload(
                            applicationId,
                            requirementItemId,
                            expectedVersion,
                            displayName,
                        )
                        documentLauncher.launch(
                            arrayOf("application/pdf", "image/jpeg", "image/png"),
                        )
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
                onRegisterApplicantVehicle = { displayName, vehicle ->
                    submitAction(AppAction(AppActionKind.REGISTER_APPLICANT_VEHICLE)) {
                        dependencies.appCoordinator.registerApplicantVehicle(displayName, vehicle)
                    }
                },
                onMarkNotificationRead = { notificationId ->
                    submitAction(AppAction(AppActionKind.MARK_NOTIFICATION_READ, notificationId)) {
                        dependencies.appCoordinator.markNotificationRead(notificationId)
                    }
                },
            )
        }
    }

    override fun onDestroy() {
        if (::connectivityObserver.isInitialized) connectivityObserver.close()
        super.onDestroy()
    }

    private fun readDriverDocument(uri: Uri): DriverDocumentUpload {
        val name = contentResolver.query(
            uri,
            arrayOf(OpenableColumns.DISPLAY_NAME),
            null,
            null,
            null,
        )?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        } ?: "driver-document"
        val mediaType = contentResolver.getType(uri) ?: when {
            name.endsWith(".pdf", ignoreCase = true) -> "application/pdf"
            name.endsWith(".jpg", ignoreCase = true) ||
                name.endsWith(".jpeg", ignoreCase = true) -> "image/jpeg"
            name.endsWith(".png", ignoreCase = true) -> "image/png"
            else -> "application/octet-stream"
        }
        val bytes = contentResolver.openInputStream(uri)?.use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(64 * 1024)
            var total = 0
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                total += read
                require(total <= MAX_DRIVER_DOCUMENT_BYTES) {
                    "The selected document exceeds the 10 MB limit."
                }
                output.write(buffer, 0, read)
            }
            output.toByteArray()
        } ?: error("The selected document could not be opened.")
        return DriverDocumentUpload(name, mediaType, bytes)
    }

    private companion object {
        const val MAX_DRIVER_DOCUMENT_BYTES = 10 * 1024 * 1024
    }
}

@Preview
@Composable
fun AppAndroidPreview() {
    App(appRole = AppRole.PASSENGER)
}
