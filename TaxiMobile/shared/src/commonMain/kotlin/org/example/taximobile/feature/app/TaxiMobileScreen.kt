package org.example.taximobile.feature.app

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.platform.testTag
import org.example.taximobile.app.AppRole
import org.example.taximobile.domain.drivers.DriverRideAction
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RidePaymentMethod
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.feature.auth.registrationInputValidity
import org.example.taximobile.feature.driver.DriverHome
import org.example.taximobile.feature.driver.onboarding.DriverOnboardingScreen
import org.example.taximobile.feature.passenger.PassengerHome
import org.example.taximobile.feature.ui.components.StatusTone
import org.example.taximobile.feature.ui.components.EmailField
import org.example.taximobile.feature.ui.components.PasswordField
import org.example.taximobile.feature.ui.components.PhoneNumberField
import org.example.taximobile.feature.ui.components.TaxiBrandArtwork
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiSegmentedControl
import org.example.taximobile.feature.ui.components.TaxiTextField
import org.example.taximobile.feature.ui.components.ToastBanner
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.text.resolve
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
fun TaxiMobileScreen(
    appRole: AppRole,
    state: AppUiState,
    pendingAction: AppAction? = null,
    completedAction: AppActionCompletion? = null,
    mapStyleUrl: String? = null,
    showManualCoordinateEntry: Boolean = true,
    onLogin: (String, String) -> Unit = { _, _ -> },
    onRegister: (String, String?, String?, String) -> Unit = { _, _, _, _ -> },
    onRecoverAccount: (String, String, String) -> Unit = { _, _, _ -> },
    onLoadAccountSecurity: () -> Unit = {},
    onCreateRecoveryCodes: (String) -> Unit = {},
    onAcknowledgeRecoveryCodes: () -> Unit = {},
    onRevokeAccountSession: (String) -> Unit = {},
    onChangeAccountPassword: (String, String) -> Unit = { _, _ -> },
    onRetry: () -> Unit = {},
    onRefresh: () -> Unit = {},
    onLogout: () -> Unit = {},
    onRequestCurrentLocation: ((Coordinates?) -> Unit) -> Unit = { result -> result(null) },
    onSetDriverOnline: (Boolean, String?, String?) -> Unit = { _, _, _ -> },
    onUpdateDriverLocation: (Coordinates) -> Unit = {},
    onRegisterDriverVehicle: (VehicleRegistration) -> Unit = {},
    onSelectDriverVehicle: (String) -> Unit = {},
    onDeactivateDriverVehicle: (String) -> Unit = {},
    onSearchPlaces: (String, String) -> Unit = { _, _ -> },
    onReversePlace: (String, Coordinates) -> Unit = { _, _ -> },
    onEstimateRide: (Coordinates, Coordinates) -> Unit = { _, _ -> },
    onRequestRide: (Coordinates, Coordinates, RidePaymentMethod) -> Unit = { _, _, _ -> },
    onLoadFixedRoutes: (String) -> Unit = {},
    onEstimateFixedRoute: (String) -> Unit = {},
    onRequestFixedRoute: (String, RidePaymentMethod) -> Unit = { _, _ -> },
    onEstimateScheduledPointToPoint: (String, String?, Coordinates, Coordinates) -> Unit = { _, _, _, _ -> },
    onEstimateScheduledFixedRoute: (String, String) -> Unit = { _, _ -> },
    onSchedulePointToPoint: (String, String?, Coordinates, Coordinates, String?, ScheduledBookingEstimate) -> Unit = { _, _, _, _, _, _ -> },
    onScheduleFixedRoute: (String, String, String?, ScheduledBookingEstimate) -> Unit = { _, _, _, _ -> },
    onCancelScheduledBooking: (String) -> Unit = {},
    onSubmitManualTransfer: (String, String?) -> Unit = { _, _ -> },
    onCancelRide: (String) -> Unit = {},
    onSendRideCoordination: (String, org.example.taximobile.domain.rides.RideCoordinationCode) -> Unit = { _, _ -> },
    onSelectPassengerRide: (String) -> Unit = {},
    onSelectDriverRide: (String) -> Unit = {},
    onUpdatePassengerProfile: (String) -> Unit = {},
    onSubmitRating: (String, Int, String?) -> Unit = { _, _, _ -> },
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit = { _, _, _, _ -> },
    onCreateSafetyReport: (String, SafetyCategory, String) -> Unit = { _, _, _ -> },
    onRespondToOffer: (String, Boolean) -> Unit = { _, _ -> },
    onSetScheduledOfferPreference: (String, Boolean) -> Unit = { _, _ -> },
    onRespondToScheduledOffer: (String, Boolean) -> Unit = { _, _ -> },
    onAdvanceDriverRide: (String, DriverRideAction) -> Unit = { _, _ -> },
    onCancelDriverRide: (String, String) -> Unit = { _, _ -> },
    onCompleteDriverRide: (String, Coordinates) -> Unit = { _, _ -> },
    onSettleDriverCash: (String) -> Unit = {},
    onApplyToDrive: (String) -> Unit = {},
    onSubmitDriverVerification: () -> Unit = {},
    onCreateDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    onSelectDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    onSaveDriverCityApplication: (
        String,
        Int,
        String,
        List<DriverApplicationAnswerDraft>,
        List<DriverApplicationEvidenceDraft>,
        List<String>,
        List<String>,
    ) -> Unit = { _, _, _, _, _, _, _ -> },
    onSubmitDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    onWithdrawDriverCityApplication: (String, String) -> Unit = { _, _ -> },
    driverDocumentPickerAvailable: Boolean = false,
    onUploadDriverApplicationDocument: (String, String, Int, String) -> Unit = { _, _, _, _ -> },
    onDeleteDriverApplicationDocument: (String, String, Int, String) -> Unit = { _, _, _, _ -> },
    onRegisterApplicantVehicle: (String, VehicleRegistration) -> Unit = { _, _ -> },
    onMarkNotificationRead: (String) -> Unit = {},
) {
    val authenticationForm = remember { AuthenticationFormState() }
    when (state) {
        AppUiState.RestoringSession -> SessionLoadingScreen(stringResource(Res.string.loading_check_session))
        AppUiState.RegisteringAccount -> SessionLoadingScreen(stringResource(Res.string.loading_create_account))
        AppUiState.RecoveringAccount -> SessionLoadingScreen(stringResource(Res.string.loading_recover_account))
        is AppUiState.UpgradeRequired -> UpgradeRequiredScreen(appRole, state, onRetry)
        is AppUiState.Offline -> OfflineScreen(state.message.resolve(), onRetry)
        is AppUiState.SignedOut -> GatePage(appRole) {
            SignedOutContent(
                appRole = appRole,
                state = state,
                form = authenticationForm,
                onLogin = onLogin,
                onRegister = onRegister,
                onRecoverAccount = onRecoverAccount,
            )
        }
        is AppUiState.DriverApplicationRequired -> GatePage(appRole) {
            DriverApplicationRequiredContent(
                state.displayName,
                pendingAction.isPending(AppActionKind.APPLY_TO_DRIVE),
                onApplyToDrive,
            )
        }
        is AppUiState.DriverApplicationPending -> GatePage(appRole) {
            DriverApplicationPendingContent(
                state.verificationStatus,
                pendingAction.isPending(AppActionKind.SUBMIT_DRIVER_VERIFICATION),
                onSubmitDriverVerification,
            )
        }
        is AppUiState.DriverOnboarding -> DriverOnboardingScreen(
            state = state,
            pendingAction = pendingAction,
            onRefresh = onRefresh,
            onLogout = onLogout,
            onCreateApplication = onCreateDriverCityApplication,
            onSelectApplication = onSelectDriverCityApplication,
            onSaveApplication = onSaveDriverCityApplication,
            onSubmitApplication = onSubmitDriverCityApplication,
            onWithdrawApplication = onWithdrawDriverCityApplication,
            documentPickerAvailable = driverDocumentPickerAvailable,
            onUploadDocument = onUploadDriverApplicationDocument,
            onDeleteDocument = onDeleteDriverApplicationDocument,
            onRegisterVehicle = onRegisterApplicantVehicle,
        )
        is AppUiState.PassengerReady -> PassengerHome(
            state,
            pendingAction,
            completedAction,
            mapStyleUrl,
            showManualCoordinateEntry,
            onLogout,
            onRefresh,
            onRequestCurrentLocation,
            onSearchPlaces,
            onReversePlace,
            onEstimateRide,
            onRequestRide,
            onLoadFixedRoutes,
            onEstimateFixedRoute,
            onRequestFixedRoute,
            onEstimateScheduledPointToPoint,
            onEstimateScheduledFixedRoute,
            onSchedulePointToPoint,
            onScheduleFixedRoute,
            onCancelScheduledBooking,
            onSubmitManualTransfer,
            onCancelRide,
            onSendRideCoordination,
            onSelectPassengerRide,
            onUpdatePassengerProfile,
            onSubmitRating,
            onCreateSupportTicket,
            onCreateSafetyReport,
            onMarkNotificationRead,
            onLoadAccountSecurity,
            onCreateRecoveryCodes,
            onAcknowledgeRecoveryCodes,
            onRevokeAccountSession,
            onChangeAccountPassword,
        )
        is AppUiState.DriverReady -> DriverHome(
            state,
            pendingAction,
            completedAction,
            mapStyleUrl,
            onLogout,
            onRequestCurrentLocation,
            onSetDriverOnline,
            onUpdateDriverLocation,
            onRegisterDriverVehicle,
            onSelectDriverVehicle,
            onDeactivateDriverVehicle,
            onRespondToOffer,
            onSetScheduledOfferPreference,
            onRespondToScheduledOffer,
            onAdvanceDriverRide,
            onCancelDriverRide,
            onSendRideCoordination,
            onCompleteDriverRide,
            onSettleDriverCash,
            onCreateSupportTicket,
            onCreateSafetyReport,
            onMarkNotificationRead,
            onSelectDriverRide,
            onRefresh,
            onLoadAccountSecurity,
            onCreateRecoveryCodes,
            onAcknowledgeRecoveryCodes,
            onRevokeAccountSession,
            onChangeAccountPassword,
        )
    }
}

@Composable
private fun GatePage(appRole: AppRole, content: @Composable () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().background(TaxiColors.Surface1).verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
    ) {
        Text(
            text = stringResource(
                if (appRole == AppRole.PASSENGER) Res.string.app_name else Res.string.app_name_driver
            ),
            modifier = Modifier.semantics { heading() },
            style = MaterialTheme.typography.displaySmall,
        )
        content()
    }
}

@Composable
private fun SessionLoadingScreen(message: String) {
    Box(
        modifier = Modifier.fillMaxSize().background(TaxiColors.Navy950).padding(TaxiSpacing.Xl),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xl),
        ) {
            Text(stringResource(Res.string.app_name), color = Color.White, style = MaterialTheme.typography.displayMedium)
            LinearProgressIndicator(Modifier.fillMaxWidth(), color = TaxiColors.Accent400, trackColor = TaxiColors.Navy800)
            Text(message, color = TaxiColors.Navy200, style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun SignedOutContent(
    appRole: AppRole,
    state: AppUiState.SignedOut,
    form: AuthenticationFormState,
    onLogin: (String, String) -> Unit,
    onRegister: (String, String?, String?, String) -> Unit,
    onRecoverAccount: (String, String, String) -> Unit,
) {
    var authenticationStarted by remember {
        mutableStateOf(
            state.showRegistrationForm || state.showRecoveryForm ||
                state.registrationCompleted || state.recoveryCompleted || state.message != null,
        )
    }
    var recoveringAccount by remember { mutableStateOf(state.showRecoveryForm) }
    LaunchedEffect(
        state.registrationCompleted,
        state.showRegistrationForm,
        state.showRecoveryForm,
        state.recoveryCompleted,
    ) {
        if (state.registrationCompleted) {
            authenticationStarted = true
            recoveringAccount = false
            form.creatingAccount = false
            form.identifier = state.suggestedIdentifier.orEmpty()
            form.phoneLogin = false
            form.password = ""
        } else if (state.recoveryCompleted) {
            authenticationStarted = true
            recoveringAccount = false
            form.creatingAccount = false
            form.password = ""
            form.recoveryCode = ""
            form.newPassword = ""
        } else if (state.showRecoveryForm) {
            authenticationStarted = true
            recoveringAccount = true
        } else if (state.showRegistrationForm) {
            authenticationStarted = true
            recoveringAccount = false
            form.creatingAccount = true
        }
    }
    if (!authenticationStarted) {
        WelcomeContent(
            appRole = appRole,
            onCreateAccount = {
                form.creatingAccount = true
                authenticationStarted = true
            },
            onSignIn = {
                form.creatingAccount = false
                authenticationStarted = true
            },
        )
        return
    }
    if (recoveringAccount) {
        ToastBanner(
            message = state.message?.resolve()
                ?: stringResource(Res.string.account_recovery_help),
            tone = if (state.message == null) StatusTone.Info else StatusTone.Danger,
        )
        Text(stringResource(Res.string.account_recovery_title), style = MaterialTheme.typography.titleLarge)
        TaxiTextField(
            form.identifier,
            { form.identifier = it },
            stringResource(Res.string.account_identifier),
        )
        TaxiTextField(
            form.recoveryCode,
            { form.recoveryCode = it },
            stringResource(Res.string.recovery_code),
        )
        PasswordField(
            form.newPassword,
            { form.newPassword = it },
            stringResource(Res.string.new_password),
            supportingText = stringResource(Res.string.password_minimum),
        )
        TaxiButton(
            label = stringResource(Res.string.reset_password),
            modifier = Modifier.testTag("account-recovery-submit"),
            onClick = {
                onRecoverAccount(
                    form.identifier.trim(),
                    form.recoveryCode.trim(),
                    form.newPassword,
                )
            },
            enabled = form.identifier.isNotBlank() &&
                form.recoveryCode.count(Char::isLetterOrDigit) >= 20 &&
                form.newPassword.length >= 12,
        )
        TaxiButton(
            label = stringResource(Res.string.back_to_sign_in),
            onClick = {
                form.recoveryCode = ""
                form.newPassword = ""
                recoveringAccount = false
            },
            style = org.example.taximobile.feature.ui.components.TaxiButtonStyle.Tertiary,
        )
        return
    }
    val validity = registrationInputValidity(form.displayName, form.email, form.phoneNumber, form.password)
    ToastBanner(
        message = state.message?.resolve() ?: if (appRole == AppRole.PASSENGER) {
            stringResource(Res.string.passenger_sign_in_intro)
        } else {
            stringResource(Res.string.driver_sign_in_intro)
        },
        tone = when {
            state.registrationCompleted -> StatusTone.Success
            state.message != null -> StatusTone.Danger
            else -> StatusTone.Info
        },
    )
    TaxiSegmentedControl(
        stringResource(Res.string.sign_in),
        stringResource(Res.string.create_account),
        firstSelected = !form.creatingAccount,
        onFirstSelected = { form.creatingAccount = false },
        onSecondSelected = { form.creatingAccount = true },
    )
    if (form.creatingAccount) {
        Text(stringResource(Res.string.registration_help))
        TaxiTextField(form.displayName, { form.displayName = it }, stringResource(Res.string.display_name))
        EmailField(
            form.email,
            { form.email = it },
            stringResource(Res.string.email_optional),
            isError = form.email.isNotBlank() && !validity.emailValid,
            supportingText = if (form.email.isNotBlank() && !validity.emailValid) {
                stringResource(Res.string.email_invalid)
            } else null,
        )
        PhoneNumberField(
            form.phoneNumber,
            { form.phoneNumber = it },
            stringResource(Res.string.moroccan_phone_optional),
            isError = form.phoneNumber.isNotBlank() && !validity.phoneNumberValid,
            supportingText = if (form.phoneNumber.isNotBlank() && !validity.phoneNumberValid) {
                stringResource(Res.string.moroccan_phone_invalid)
            } else stringResource(Res.string.moroccan_phone_example),
        )
    } else {
        TaxiSegmentedControl(
            firstLabel = stringResource(Res.string.login_with_phone),
            secondLabel = stringResource(Res.string.login_with_email),
            firstSelected = form.phoneLogin,
            onFirstSelected = {
                form.phoneLogin = true
                form.identifier = ""
            },
            onSecondSelected = {
                form.phoneLogin = false
                form.identifier = ""
            },
        )
        if (form.phoneLogin) {
            PhoneNumberField(
                form.identifier,
                { form.identifier = it },
                stringResource(Res.string.moroccan_phone),
            )
        } else {
            EmailField(
                form.identifier,
                { form.identifier = it },
                stringResource(Res.string.email),
            )
        }
    }
    PasswordField(
        form.password,
        { form.password = it },
        stringResource(Res.string.password),
        supportingText = if (form.creatingAccount) stringResource(Res.string.password_minimum) else null,
    )
    TaxiButton(
        label = stringResource(if (form.creatingAccount) Res.string.create_account else Res.string.sign_in),
        modifier = Modifier.testTag("auth-submit"),
        onClick = {
            if (form.creatingAccount) {
                onRegister(
                    form.displayName.trim(),
                    form.email.trim().ifBlank { null },
                    form.phoneNumber.trim().ifBlank { null },
                    form.password,
                )
            } else {
                onLogin(form.identifier.trim(), form.password)
            }
        },
        enabled = if (form.creatingAccount) validity.canSubmit else form.identifier.isNotBlank() && form.password.isNotEmpty(),
    )
    if (!form.creatingAccount) {
        TaxiButton(
            label = stringResource(Res.string.use_recovery_code),
            onClick = {
                form.password = ""
                recoveringAccount = true
            },
            style = org.example.taximobile.feature.ui.components.TaxiButtonStyle.Tertiary,
        )
    }
}

@Composable
private fun WelcomeContent(
    appRole: AppRole,
    onCreateAccount: () -> Unit,
    onSignIn: () -> Unit,
) {
    TaxiBrandArtwork(
        contentDescriptionText = stringResource(Res.string.welcome_artwork_description),
        modifier = Modifier.padding(vertical = TaxiSpacing.Md),
    )
    Text(
        stringResource(
            if (appRole == AppRole.PASSENGER) Res.string.passenger_welcome_title
            else Res.string.driver_welcome_title,
        ),
        style = MaterialTheme.typography.displayMedium,
        modifier = Modifier.semantics { heading() },
    )
    Text(
        stringResource(
            if (appRole == AppRole.PASSENGER) Res.string.passenger_welcome_body
            else Res.string.driver_welcome_body,
        ),
        style = MaterialTheme.typography.bodyLarge,
        color = TaxiColors.Ink500,
    )
    TaxiButton(stringResource(Res.string.create_account), onCreateAccount)
    TaxiButton(
        stringResource(Res.string.sign_in),
        onSignIn,
        style = org.example.taximobile.feature.ui.components.TaxiButtonStyle.Secondary,
    )
}

private class AuthenticationFormState {
    var creatingAccount by mutableStateOf(false)
    var displayName by mutableStateOf("")
    var email by mutableStateOf("")
    var phoneNumber by mutableStateOf("")
    var identifier by mutableStateOf("")
    var password by mutableStateOf("")
    var recoveryCode by mutableStateOf("")
    var newPassword by mutableStateOf("")
    var phoneLogin by mutableStateOf(true)
}

@Composable
private fun DriverApplicationRequiredContent(
    displayName: String,
    loading: Boolean,
    onApply: (String) -> Unit,
) {
    var name by remember { mutableStateOf(displayName) }
    ToastBanner(stringResource(Res.string.driver_registration_notice))
    TaxiTextField(name, { name = it }, stringResource(Res.string.driver_display_name))
    TaxiButton(
        stringResource(Res.string.apply_to_drive),
        { onApply(name.trim()) },
        enabled = name.isNotBlank(),
        loading = loading,
    )
}

@Composable
private fun DriverApplicationPendingContent(
    status: String,
    loading: Boolean,
    onSubmitVerification: () -> Unit,
) {
    Text(stringResource(Res.string.driver_application_status), style = MaterialTheme.typography.titleMedium)
    ToastBanner(
        stringResource(driverVerificationStatusResource(status)),
        if (status == "VERIFIED" || status == "APPROVED") StatusTone.Success else StatusTone.Info,
    )
    if (status == "NOT_STARTED" || status == "ADDITIONAL_INFORMATION_REQUIRED") {
        Text(stringResource(Res.string.driver_verification_submit_help))
        TaxiButton(
            stringResource(Res.string.submit_for_verification),
            onSubmitVerification,
            loading = loading,
        )
    }
}

@Composable
private fun OfflineScreen(message: String, onRetry: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().background(TaxiColors.Surface1).padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(stringResource(Res.string.connection_unavailable), style = MaterialTheme.typography.displaySmall)
        Text(message, Modifier.padding(vertical = TaxiSpacing.Xl), style = MaterialTheme.typography.bodyLarge)
        TaxiButton(stringResource(Res.string.retry_connection), onRetry)
    }
}

@Composable
private fun UpgradeRequiredScreen(
    appRole: AppRole,
    state: AppUiState.UpgradeRequired,
    onRetry: () -> Unit,
) {
    GatePage(appRole) {
        Text(
            stringResource(Res.string.client_upgrade_required_title),
            modifier = Modifier.semantics { heading() },
            style = MaterialTheme.typography.headlineMedium,
        )
        Text(
            stringResource(
                Res.string.client_upgrade_required_body,
                state.minimumVersion,
            ),
            style = MaterialTheme.typography.bodyLarge,
        )
        Text(
            stringResource(
                Res.string.client_upgrade_policy_reference,
                state.policyRevision,
            ),
            style = MaterialTheme.typography.bodySmall,
        )
        TaxiButton(stringResource(Res.string.retry_connection), onRetry)
    }
}
