package org.example.taximobile.applicant.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.unit.dp
import org.example.taximobile.applicant.state.ApplicantAuthMode
import org.example.taximobile.applicant.state.ApplicantPortalCoordinator
import org.example.taximobile.applicant.state.ApplicantPortalState
import org.example.taximobile.applicant.state.browserDriverDocumentPickerAvailable
import org.example.taximobile.applicant.state.ApplicantSessionPhase
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.theme.TaxiTheme

@Composable
fun ApplicantPortalApp(coordinator: ApplicantPortalCoordinator) {
    val state by coordinator.state.collectAsState()
    TaxiTheme {
        Surface(Modifier.fillMaxSize(), color = TaxiColors.Surface1) {
            if (state.sessionPhase == ApplicantSessionPhase.SIGNED_IN) {
                ApplicantDashboard(state, coordinator)
            } else {
                ApplicantWelcome(state, coordinator)
            }
        }
    }
}

@Composable
private fun ApplicantWelcome(
    state: ApplicantPortalState,
    coordinator: ApplicantPortalCoordinator,
) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 900.dp
        if (wide) {
            Row(Modifier.fillMaxSize()) {
                WelcomePanel(state, Modifier.weight(1.1f))
                AuthenticationPanel(
                    state,
                    coordinator,
                    Modifier.weight(0.9f),
                    independentlyScrollable = true,
                )
            }
        } else {
            Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
                WelcomePanel(state, Modifier.fillMaxWidth())
                AuthenticationPanel(
                    state,
                    coordinator,
                    Modifier.fillMaxWidth(),
                    independentlyScrollable = false,
                )
            }
        }
    }
}

@Composable
private fun WelcomePanel(state: ApplicantPortalState, modifier: Modifier) {
    val language = Locale.current.language
    Column(
        modifier.background(TaxiColors.Navy950).padding(48.dp),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xl),
    ) {
        ApplicantWordmark(dark = true)
        Spacer(Modifier.height(TaxiSpacing.Lg))
        Text(
            "Drive in a city that is recruiting.",
            color = Color.White,
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold,
        )
        Text(
            "Create one account, choose a city, complete that city's current requirements, and follow a clear review status. Approval is city-scoped—not national.",
            color = TaxiColors.Navy200,
            style = MaterialTheme.typography.bodyLarge,
        )
        Text("Recruiting now", color = TaxiColors.Accent400, style = MaterialTheme.typography.titleMedium)
        if (state.recruitingCities.isEmpty()) {
            Text("No recruiting city is currently published. Refresh later.", color = TaxiColors.Navy200)
        } else {
            state.recruitingCities.forEach { city ->
                Surface(color = TaxiColors.Navy900, shape = MaterialTheme.shapes.large) {
                    Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
                        Text(city.name.forLanguage(language), color = Color.White, fontWeight = FontWeight.Bold)
                        Text("Requirements version ${city.requirementVersion}", color = TaxiColors.Navy200,
                            style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
        Text(
            "Documents are accepted only when protected storage is available. The portal never claims that an unavailable upload succeeded.",
            color = TaxiColors.Navy200,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun AuthenticationPanel(
    state: ApplicantPortalState,
    coordinator: ApplicantPortalCoordinator,
    modifier: Modifier,
    independentlyScrollable: Boolean,
) {
    var displayName by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var identifier by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val busy = state.sessionPhase == ApplicantSessionPhase.SIGNING_IN || state.busyLabel != null
    val panelModifier = if (independentlyScrollable) {
        modifier.fillMaxHeight().verticalScroll(rememberScrollState())
    } else {
        modifier
    }
    Column(
        panelModifier.padding(48.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Column(Modifier.fillMaxWidth().widthIn(max = 520.dp), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Text(
                if (state.authMode == ApplicantAuthMode.SIGN_IN) "Continue your application" else "Create a driver applicant account",
                style = MaterialTheme.typography.headlineSmall,
                color = TaxiColors.Navy900,
                fontWeight = FontWeight.Bold,
            )
            Text(
                if (state.authMode == ApplicantAuthMode.SIGN_IN) {
                    "Sign in to view only the city applications owned by this account."
                } else {
                    "Use an email address or Moroccan phone number. A password must contain at least 12 characters."
                },
                color = TaxiColors.Ink500,
            )
            state.error?.let { ApplicantMessageBanner(it, error = true, onDismiss = coordinator::dismissError) }
            state.notice?.let { ApplicantMessageBanner(it, error = false, onDismiss = coordinator::dismissNotice) }
            if (state.authMode == ApplicantAuthMode.CREATE_ACCOUNT) {
                OutlinedTextField(displayName, { displayName = it.take(120) }, Modifier.fillMaxWidth(),
                    label = { Text("Full name") }, singleLine = true, enabled = !busy)
                OutlinedTextField(email, { email = it.take(320) }, Modifier.fillMaxWidth(),
                    label = { Text("Email (optional if phone is provided)") }, singleLine = true, enabled = !busy)
                OutlinedTextField(phone, { phone = it.take(32) }, Modifier.fillMaxWidth(),
                    label = { Text("Moroccan phone (optional if email is provided)") }, singleLine = true, enabled = !busy)
            } else {
                OutlinedTextField(identifier, { identifier = it.take(320) }, Modifier.fillMaxWidth(),
                    label = { Text("Email or phone") }, singleLine = true, enabled = !busy)
            }
            OutlinedTextField(
                password,
                { password = it.take(256) },
                Modifier.fillMaxWidth(),
                label = { Text("Password") },
                singleLine = true,
                enabled = !busy,
                visualTransformation = PasswordVisualTransformation(),
            )
            Button(
                onClick = {
                    if (state.authMode == ApplicantAuthMode.SIGN_IN) coordinator.login(identifier, password)
                    else coordinator.register(displayName, email, phone, password)
                },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                if (busy) {
                    CircularProgressIndicator(Modifier.height(20.dp), strokeWidth = 2.dp)
                    Text("  ${state.busyLabel ?: "Signing in"}…")
                } else {
                    Text(if (state.authMode == ApplicantAuthMode.SIGN_IN) "Sign in" else "Create account")
                }
            }
            OutlinedButton(
                onClick = {
                    coordinator.setAuthMode(
                        if (state.authMode == ApplicantAuthMode.SIGN_IN) ApplicantAuthMode.CREATE_ACCOUNT
                        else ApplicantAuthMode.SIGN_IN,
                    )
                },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (state.authMode == ApplicantAuthMode.SIGN_IN) "Create an account" else "Back to sign in")
            }
            HorizontalDivider(color = TaxiColors.StrokeSubtle)
            Text("Session security", style = MaterialTheme.typography.labelMedium, color = TaxiColors.Navy700)
            Text(
                "Credentials stay in memory for this tab and are cleared on sign out or page refresh. Do not use a shared browser.",
                style = MaterialTheme.typography.bodySmall,
                color = TaxiColors.Ink500,
            )
            Text("API: ${state.apiBaseUrl}", style = MaterialTheme.typography.bodySmall, color = TaxiColors.Ink500)
        }
    }
}

@Composable
private fun ApplicantDashboard(
    state: ApplicantPortalState,
    coordinator: ApplicantPortalCoordinator,
) {
    val language = Locale.current.language
    Column(Modifier.fillMaxSize()) {
        Surface(color = TaxiColors.Navy950) {
            Row(
                Modifier.fillMaxWidth().padding(horizontal = TaxiSpacing.Xl, vertical = TaxiSpacing.Md),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                ApplicantWordmark(dark = true)
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    OutlinedButton(onClick = coordinator::refresh, enabled = !state.interactionLocked) { Text("Refresh") }
                    Button(onClick = coordinator::logout, enabled = !state.interactionLocked) { Text("Sign out") }
                }
            }
        }
        Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
        ) {
            Text("Welcome, ${state.account?.displayName.orEmpty()}", style = MaterialTheme.typography.headlineMedium,
                color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text("Each application and approval below is scoped to its named city.", color = TaxiColors.Ink500)
            state.busyLabel?.let {
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm), verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.height(20.dp), strokeWidth = 2.dp)
                    Text("$it…", color = TaxiColors.Navy700)
                }
            }
            state.error?.let { ApplicantMessageBanner(it, error = true, onDismiss = coordinator::dismissError) }
            state.notice?.let { ApplicantMessageBanner(it, error = false, onDismiss = coordinator::dismissNotice) }

            Text("Your city applications", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            if (state.applications.isEmpty()) {
                ApplicantCard { Text("You have not started a city application yet.", color = TaxiColors.Ink500) }
            } else {
                state.applications.forEach { application ->
                    ApplicantCard(
                        selected = application.id == state.selectedApplication?.id,
                        modifier = Modifier.clickable(enabled = !state.interactionLocked) {
                            coordinator.selectApplication(application.id)
                        },
                    ) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically) {
                            Text(application.cityName.forLanguage(language), style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold)
                            ApplicantStatus(application.status)
                        }
                        Text("Requirements version ${application.requirementVersion} · record version ${application.optimisticVersion}",
                            color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                        application.latestApplicantMessage?.let { Text(it, color = TaxiColors.Navy700) }
                    }
                }
            }

            Text("Recruiting cities", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            state.recruitingCities.forEach { city ->
                val existing = state.applications.firstOrNull { it.cityId == city.id && it.status in OPEN_STATUSES }
                ApplicantCard {
                    Text(city.name.forLanguage(language), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("Current requirements: version ${city.requirementVersion}", color = TaxiColors.Ink500)
                    ApplicantPrimaryButton(
                        label = if (existing == null) "Start city application" else "Continue application",
                        onClick = {
                            if (existing == null) coordinator.createApplication(city.id)
                            else coordinator.selectApplication(existing.id)
                        },
                        enabled = !state.interactionLocked,
                    )
                }
            }

            state.selectedApplication?.let { application ->
                ApplicantApplicationEditor(
                    application = application,
                    vehicles = state.vehicles,
                    credentials = state.credentials,
                    locked = state.interactionLocked,
                    onSave = coordinator::saveApplication,
                    onSubmit = coordinator::submitApplication,
                    onWithdraw = coordinator::withdrawApplication,
                    documentPickerAvailable = browserDriverDocumentPickerAvailable,
                    onUploadDocument = coordinator::uploadDocument,
                    onDeleteDocument = coordinator::deleteDocument,
                    onRegisterVehicle = coordinator::registerVehicle,
                )
            }
            Spacer(Modifier.height(TaxiSpacing.Xxl))
        }
    }
}

private val OPEN_STATUSES = setOf("NOT_STARTED", "SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED")
