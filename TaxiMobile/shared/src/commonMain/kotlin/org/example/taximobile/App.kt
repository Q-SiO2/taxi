package org.example.taximobile

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.unit.LayoutDirection
import org.example.taximobile.app.AppRole
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionCompletion
import org.example.taximobile.feature.app.TaxiMobileScreen
import org.example.taximobile.feature.connectivity.ConnectivityStatus
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.ToastBanner
import org.example.taximobile.feature.ui.theme.TaxiTheme
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.text.UiMessage
import org.example.taximobile.feature.ui.text.resolve
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_network_unavailable

@Composable
fun App(
    appRole: AppRole = AppRole.PASSENGER,
    state: AppUiState = AppUiState.SignedOut(),
    pendingAction: AppAction? = null,
    completedAction: AppActionCompletion? = null,
    connectivityStatus: ConnectivityStatus = ConnectivityStatus.UNKNOWN,
    connectionIssue: UiMessage? = null,
    mapStyleUrl: String? = null,
    showManualCoordinateEntry: Boolean = true,
    onLogin: (identifier: String, password: String) -> Unit = { _, _ -> },
    onRegister: (displayName: String, email: String?, phoneNumber: String?, password: String) -> Unit = { _, _, _, _ -> },
    onRecoverAccount: (identifier: String, recoveryCode: String, newPassword: String) -> Unit = { _, _, _ -> },
    onLoadAccountSecurity: () -> Unit = {},
    onCreateRecoveryCodes: (String) -> Unit = {},
    onAcknowledgeRecoveryCodes: () -> Unit = {},
    onRevokeAccountSession: (String) -> Unit = {},
    onChangeAccountPassword: (String, String) -> Unit = { _, _ -> },
    onRetry: () -> Unit = {},
    onRefresh: () -> Unit = {},
    onLogout: () -> Unit = {},
    onRequestCurrentLocation: ((org.example.taximobile.domain.rides.Coordinates?) -> Unit) -> Unit = { result -> result(null) },
    onSetDriverOnline: (Boolean, String?, String?) -> Unit = { _, _, _ -> },
    onUpdateDriverLocation: (org.example.taximobile.domain.rides.Coordinates) -> Unit = {},
    onRegisterDriverVehicle: (org.example.taximobile.domain.drivers.VehicleRegistration) -> Unit = {},
    onSelectDriverVehicle: (String) -> Unit = {},
    onDeactivateDriverVehicle: (String) -> Unit = {},
    onSearchPlaces: (String, String) -> Unit = { _, _ -> },
    onReversePlace: (String, org.example.taximobile.domain.rides.Coordinates) -> Unit = { _, _ -> },
    onEstimateRide: (org.example.taximobile.domain.rides.Coordinates, org.example.taximobile.domain.rides.Coordinates) -> Unit = { _, _ -> },
    onRequestRide: (org.example.taximobile.domain.rides.Coordinates, org.example.taximobile.domain.rides.Coordinates, org.example.taximobile.domain.rides.RidePaymentMethod) -> Unit = { _, _, _ -> },
    onLoadFixedRoutes: (String) -> Unit = {},
    onEstimateFixedRoute: (String) -> Unit = {},
    onRequestFixedRoute: (String, org.example.taximobile.domain.rides.RidePaymentMethod) -> Unit = { _, _ -> },
    onEstimateScheduledPointToPoint: (String, String?, org.example.taximobile.domain.rides.Coordinates, org.example.taximobile.domain.rides.Coordinates) -> Unit = { _, _, _, _ -> },
    onEstimateScheduledFixedRoute: (String, String) -> Unit = { _, _ -> },
    onSchedulePointToPoint: (String, String?, org.example.taximobile.domain.rides.Coordinates, org.example.taximobile.domain.rides.Coordinates, String?, org.example.taximobile.domain.scheduling.ScheduledBookingEstimate) -> Unit = { _, _, _, _, _, _ -> },
    onScheduleFixedRoute: (String, String, String?, org.example.taximobile.domain.scheduling.ScheduledBookingEstimate) -> Unit = { _, _, _, _ -> },
    onCancelScheduledBooking: (String) -> Unit = {},
    onSubmitManualTransfer: (String, String?) -> Unit = { _, _ -> },
    onCancelRide: (String) -> Unit = {},
    onSendRideCoordination: (String, org.example.taximobile.domain.rides.RideCoordinationCode) -> Unit = { _, _ -> },
    onSelectPassengerRide: (String) -> Unit = {},
    onSelectDriverRide: (String) -> Unit = {},
    onUpdatePassengerProfile: (String) -> Unit = {},
    onSubmitRating: (String, Int, String?) -> Unit = { _, _, _ -> },
    onCreateSupportTicket: (org.example.taximobile.domain.support.SupportCategory, String, String, String?) -> Unit = { _, _, _, _ -> },
    onCreateSafetyReport: (String, org.example.taximobile.domain.safety.SafetyCategory, String) -> Unit = { _, _, _ -> },
    onRespondToOffer: (String, Boolean) -> Unit = { _, _ -> },
    onSetScheduledOfferPreference: (String, Boolean) -> Unit = { _, _ -> },
    onRespondToScheduledOffer: (String, Boolean) -> Unit = { _, _ -> },
    onAdvanceDriverRide: (String, org.example.taximobile.domain.drivers.DriverRideAction) -> Unit = { _, _ -> },
    onCancelDriverRide: (String, String) -> Unit = { _, _ -> },
    onCompleteDriverRide: (String, org.example.taximobile.domain.rides.Coordinates) -> Unit = { _, _ -> },
    onSettleDriverCash: (String) -> Unit = {},
    onApplyToDrive: (String) -> Unit = {},
    onSubmitDriverVerification: () -> Unit = {},
    onCreateDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    onSelectDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    onSaveDriverCityApplication: (
        String,
        Int,
        String,
        List<org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft>,
        List<org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft>,
        List<String>,
        List<String>,
    ) -> Unit = { _, _, _, _, _, _, _ -> },
    onSubmitDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    onWithdrawDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    driverDocumentPickerAvailable: Boolean = false,
    onUploadDriverApplicationDocument: (String, String, Int, String) -> Unit = { _, _, _, _ -> },
    onDeleteDriverApplicationDocument: (String, String, Int, String) -> Unit = { _, _, _, _ -> },
    onRegisterApplicantVehicle: (String, org.example.taximobile.domain.drivers.VehicleRegistration) -> Unit = { _, _ -> },
    onMarkNotificationRead: (String) -> Unit = {},
) {
    val layoutDirection = if (Locale.current.language in RTL_LANGUAGES) {
        LayoutDirection.Rtl
    } else {
        LayoutDirection.Ltr
    }
    CompositionLocalProvider(LocalLayoutDirection provides layoutDirection) {
        TaxiTheme {
            Surface(modifier = Modifier.fillMaxSize()) {
                Box(Modifier.fillMaxSize()) {
                    TaxiMobileScreen(
                        appRole = appRole,
                        state = state,
                        pendingAction = pendingAction,
                        completedAction = completedAction,
                        mapStyleUrl = mapStyleUrl,
                        showManualCoordinateEntry = showManualCoordinateEntry,
                        onLogin = onLogin,
                        onRegister = onRegister,
                        onRecoverAccount = onRecoverAccount,
                        onLoadAccountSecurity = onLoadAccountSecurity,
                        onCreateRecoveryCodes = onCreateRecoveryCodes,
                        onAcknowledgeRecoveryCodes = onAcknowledgeRecoveryCodes,
                        onRevokeAccountSession = onRevokeAccountSession,
                        onChangeAccountPassword = onChangeAccountPassword,
                        onRetry = onRetry,
                        onRefresh = onRefresh,
                        onLogout = onLogout,
                        onRequestCurrentLocation = onRequestCurrentLocation,
                        onSetDriverOnline = onSetDriverOnline,
                        onUpdateDriverLocation = onUpdateDriverLocation,
                        onRegisterDriverVehicle = onRegisterDriverVehicle,
                        onSelectDriverVehicle = onSelectDriverVehicle,
                        onDeactivateDriverVehicle = onDeactivateDriverVehicle,
                        onSearchPlaces = onSearchPlaces,
                        onReversePlace = onReversePlace,
                        onEstimateRide = onEstimateRide,
                        onRequestRide = onRequestRide,
                        onLoadFixedRoutes = onLoadFixedRoutes,
                        onEstimateFixedRoute = onEstimateFixedRoute,
                        onRequestFixedRoute = onRequestFixedRoute,
                        onEstimateScheduledPointToPoint = onEstimateScheduledPointToPoint,
                        onEstimateScheduledFixedRoute = onEstimateScheduledFixedRoute,
                        onSchedulePointToPoint = onSchedulePointToPoint,
                        onScheduleFixedRoute = onScheduleFixedRoute,
                        onCancelScheduledBooking = onCancelScheduledBooking,
                        onSubmitManualTransfer = onSubmitManualTransfer,
                        onCancelRide = onCancelRide,
                        onSendRideCoordination = onSendRideCoordination,
                        onSelectPassengerRide = onSelectPassengerRide,
                        onSelectDriverRide = onSelectDriverRide,
                        onUpdatePassengerProfile = onUpdatePassengerProfile,
                        onSubmitRating = onSubmitRating,
                        onCreateSupportTicket = onCreateSupportTicket,
                        onCreateSafetyReport = onCreateSafetyReport,
                        onRespondToOffer = onRespondToOffer,
                        onSetScheduledOfferPreference = onSetScheduledOfferPreference,
                        onRespondToScheduledOffer = onRespondToScheduledOffer,
                        onAdvanceDriverRide = onAdvanceDriverRide,
                        onCancelDriverRide = onCancelDriverRide,
                        onCompleteDriverRide = onCompleteDriverRide,
                        onSettleDriverCash = onSettleDriverCash,
                        onApplyToDrive = onApplyToDrive,
                        onSubmitDriverVerification = onSubmitDriverVerification,
                        onCreateDriverCityApplication = onCreateDriverCityApplication,
                        onSelectDriverCityApplication = onSelectDriverCityApplication,
                        onSaveDriverCityApplication = onSaveDriverCityApplication,
                        onSubmitDriverCityApplication = onSubmitDriverCityApplication,
                        onWithdrawDriverCityApplication = onWithdrawDriverCityApplication,
                        driverDocumentPickerAvailable = driverDocumentPickerAvailable,
                        onUploadDriverApplicationDocument = onUploadDriverApplicationDocument,
                        onDeleteDriverApplicationDocument = onDeleteDriverApplicationDocument,
                        onRegisterApplicantVehicle = onRegisterApplicantVehicle,
                        onMarkNotificationRead = onMarkNotificationRead,
                    )
                    val notice = connectionIssue?.resolve() ?: if (
                        connectivityStatus == ConnectivityStatus.UNAVAILABLE && state !is AppUiState.Offline
                    ) {
                        stringResource(Res.string.message_network_unavailable)
                    } else {
                        null
                    }
                    notice?.let {
                        ToastBanner(
                            message = it,
                            tone = StatusTone.Danger,
                            modifier = Modifier
                                .align(Alignment.TopCenter)
                                .statusBarsPadding()
                                .padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm),
                        )
                    }
                }
            }
        }
    }
}

private val RTL_LANGUAGES = setOf("ar", "fa", "he", "ur")
