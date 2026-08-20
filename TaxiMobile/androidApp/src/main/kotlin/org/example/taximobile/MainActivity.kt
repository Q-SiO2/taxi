package org.example.taximobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.tooling.preview.Preview
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import kotlinx.coroutines.launch
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import org.example.taximobile.app.AppRole
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionGate
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.AppActionCompletion
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.app.hasAuthenticatedSession
import org.example.taximobile.feature.connectivity.AppStatePresentation
import org.example.taximobile.feature.connectivity.ConnectivityRecoveryPolicy
import org.example.taximobile.feature.connectivity.ConnectivityStatus
import org.example.taximobile.feature.connectivity.ForegroundRecoveryPolicy
import org.example.taximobile.feature.notifications.PushRefreshSignals

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
            val recoveryPolicy = remember { ConnectivityRecoveryPolicy() }
            val foregroundRecoveryPolicy = remember { ForegroundRecoveryPolicy() }
            val actionGate = remember { AppActionGate() }
            val scope = rememberCoroutineScope()
            fun submitAction(
                key: AppAction,
                recoverFailure: Boolean = true,
                action: suspend () -> AppUiState,
            ) {
                if (!actionGate.tryStart(key)) return
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
                foregroundRecoveryPolicy.onBackground()
            }
            LifecycleEventEffect(Lifecycle.Event.ON_START) {
                if (
                    foregroundRecoveryPolicy.shouldRefreshOnForeground() &&
                    presentation.state.hasAuthenticatedSession()
                ) {
                    scope.launch {
                        presentation = presentation.accept(dependencies.appCoordinator.restore())
                    }
                }
            }
            LaunchedEffect(dependencies) {
                presentation = presentation.accept(dependencies.appCoordinator.restore())
            }
            LaunchedEffect(connectivityObserver) {
                connectivityObserver.status.collect { observedStatus ->
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
                onSetDriverOnline = { online ->
                    submitAction(AppAction(AppActionKind.SET_DRIVER_AVAILABILITY)) {
                        dependencies.appCoordinator.changeDriverAvailability(online)
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
                onEstimateRide = { pickup, destination ->
                    submitAction(AppAction(AppActionKind.ESTIMATE_RIDE)) {
                        dependencies.appCoordinator.estimateRide(pickup, destination)
                    }
                },
                onRequestRide = { pickup, destination ->
                    submitAction(AppAction(AppActionKind.REQUEST_RIDE)) {
                        dependencies.appCoordinator.requestRide(pickup, destination)
                    }
                },
                onCancelRide = { rideId ->
                    submitAction(AppAction(AppActionKind.CANCEL_RIDE, rideId)) {
                        dependencies.appCoordinator.cancelRide(rideId)
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
                onRespondToOffer = { offerId, accept ->
                    val response = if (accept) "accept" else "decline"
                    submitAction(AppAction(AppActionKind.RESPOND_TO_OFFER, "$offerId:$response")) {
                        dependencies.appCoordinator.respondToOffer(offerId, accept)
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
}

@Preview
@Composable
fun AppAndroidPreview() {
    App(appRole = AppRole.PASSENGER)
}
