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
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.feature.auth.registrationInputValidity
import org.example.taximobile.feature.driver.DriverHome
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
    onRetry: () -> Unit = {},
    onRefresh: () -> Unit = {},
    onLogout: () -> Unit = {},
    onRequestCurrentLocation: ((Coordinates?) -> Unit) -> Unit = { result -> result(null) },
    onSetDriverOnline: (Boolean) -> Unit = {},
    onUpdateDriverLocation: (Coordinates) -> Unit = {},
    onRegisterDriverVehicle: (VehicleRegistration) -> Unit = {},
    onSelectDriverVehicle: (String) -> Unit = {},
    onDeactivateDriverVehicle: (String) -> Unit = {},
    onEstimateRide: (Coordinates, Coordinates) -> Unit = { _, _ -> },
    onRequestRide: (Coordinates, Coordinates) -> Unit = { _, _ -> },
    onCancelRide: (String) -> Unit = {},
    onSelectPassengerRide: (String) -> Unit = {},
    onSelectDriverRide: (String) -> Unit = {},
    onUpdatePassengerProfile: (String) -> Unit = {},
    onSubmitRating: (String, Int, String?) -> Unit = { _, _, _ -> },
    onCreateSupportTicket: (SupportCategory, String, String, String?) -> Unit = { _, _, _, _ -> },
    onRespondToOffer: (String, Boolean) -> Unit = { _, _ -> },
    onAdvanceDriverRide: (String, DriverRideAction) -> Unit = { _, _ -> },
    onCancelDriverRide: (String, String) -> Unit = { _, _ -> },
    onCompleteDriverRide: (String, Coordinates) -> Unit = { _, _ -> },
    onSettleDriverCash: (String) -> Unit = {},
    onApplyToDrive: (String) -> Unit = {},
    onSubmitDriverVerification: () -> Unit = {},
    onMarkNotificationRead: (String) -> Unit = {},
) {
    val authenticationForm = remember { AuthenticationFormState() }
    when (state) {
        AppUiState.RestoringSession -> SessionLoadingScreen(stringResource(Res.string.loading_check_session))
        AppUiState.RegisteringAccount -> SessionLoadingScreen(stringResource(Res.string.loading_create_account))
        is AppUiState.Offline -> OfflineScreen(state.message.resolve(), onRetry)
        is AppUiState.SignedOut -> GatePage(appRole) {
            SignedOutContent(
                appRole = appRole,
                state = state,
                form = authenticationForm,
                onLogin = onLogin,
                onRegister = onRegister,
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
        is AppUiState.PassengerReady -> PassengerHome(
            state,
            pendingAction,
            completedAction,
            mapStyleUrl,
            showManualCoordinateEntry,
            onLogout,
            onRefresh,
            onRequestCurrentLocation,
            onEstimateRide,
            onRequestRide,
            onCancelRide,
            onSelectPassengerRide,
            onUpdatePassengerProfile,
            onSubmitRating,
            onCreateSupportTicket,
            onMarkNotificationRead,
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
            onAdvanceDriverRide,
            onCancelDriverRide,
            onCompleteDriverRide,
            onSettleDriverCash,
            onCreateSupportTicket,
            onMarkNotificationRead,
            onSelectDriverRide,
            onRefresh,
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
) {
    var authenticationStarted by remember {
        mutableStateOf(state.showRegistrationForm || state.registrationCompleted || state.message != null)
    }
    LaunchedEffect(state.registrationCompleted, state.showRegistrationForm) {
        if (state.registrationCompleted) {
            authenticationStarted = true
            form.creatingAccount = false
            form.identifier = state.suggestedIdentifier.orEmpty()
            form.phoneLogin = false
            form.password = ""
        } else if (state.showRegistrationForm) {
            authenticationStarted = true
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
