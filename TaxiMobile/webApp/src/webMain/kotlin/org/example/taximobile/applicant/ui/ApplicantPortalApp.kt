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
import androidx.compose.material3.ButtonDefaults
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
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*
import androidx.compose.ui.text.style.TextDirection
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.applicant.state.ApplicantAuthMode
import org.example.taximobile.applicant.state.ApplicantPortalCoordinator
import org.example.taximobile.applicant.state.ApplicantPortalState
import org.example.taximobile.applicant.state.browserDriverDocumentPickerAvailable
import org.example.taximobile.applicant.state.ApplicantSessionPhase
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.theme.TaxiTheme
import org.example.taximobile.feature.ui.text.resolve
import org.example.taximobile.operations.ui.recruitmentTextStyle

@Composable
fun ApplicantPortalApp(coordinator: ApplicantPortalCoordinator) {
    val state by coordinator.state.collectAsState()
    TaxiTheme {
        val taxiColors = TaxiTheme.colors
        Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            org.example.taximobile.feature.ui.components.TaxiStyleChooser(Modifier.weight(1f))
            org.example.taximobile.feature.ui.components.TaxiLanguageChooser()
        }
        Surface(Modifier.weight(1f).fillMaxWidth(), color = taxiColors.Surface1) {
            if (state.sessionPhase == ApplicantSessionPhase.SIGNED_IN) {
                ApplicantDashboard(state, coordinator)
            } else {
                ApplicantWelcome(state, coordinator)
            }
        }
        }
    }
}

@Composable
private fun ApplicantWelcome(
    state: ApplicantPortalState,
    coordinator: ApplicantPortalCoordinator,
) {
    // This short-lived draft belongs to the welcome flow, above responsive
    // branches. Resizing must not replace the form or persist its password.
    val draft = remember { ApplicantAuthDraft() }
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val wide = maxWidth >= 900.dp
        if (wide) {
            Row(Modifier.fillMaxSize()) {
                WelcomePanel(state, Modifier.weight(1.1f), independentlyScrollable = true)
                AuthenticationPanel(
                    state,
                    coordinator,
                    draft,
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
                    draft,
                    Modifier.fillMaxWidth(),
                    independentlyScrollable = false,
                )
            }
        }
    }
}

private class ApplicantAuthDraft {
    var displayName by mutableStateOf("")
    var email by mutableStateOf("")
    var phone by mutableStateOf("")
    var identifier by mutableStateOf("")
    var password by mutableStateOf("")
}

@Composable
private fun WelcomePanel(state: ApplicantPortalState, modifier: Modifier, independentlyScrollable: Boolean = false) {
    val taxiColors = TaxiTheme.colors
    val language = Locale.current.language
    val panelModifier = if (independentlyScrollable) {
        modifier.fillMaxHeight().verticalScroll(rememberScrollState())
    } else modifier
    Column(
        panelModifier.background(taxiColors.Navy950).padding(48.dp),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xl),
    ) {
        ApplicantWordmark(dark = true)
        org.example.taximobile.feature.ui.components.TaxiEntryFrame(Modifier.height(
            if (TaxiTheme.style == org.example.taximobile.feature.ui.theme.TaxiStyle.Notepad) 28.dp else 72.dp))
        Text(
            stringResource(Res.string.web_applicant_hero),
            color = Color.White,
            style = MaterialTheme.typography.displaySmall,
            fontWeight = FontWeight.Bold,
        )
        Text(
            stringResource(Res.string.web_applicant_intro),
            color = taxiColors.Navy200,
            style = MaterialTheme.typography.bodyLarge,
        )
        Text(stringResource(Res.string.web_recruiting_now), color = taxiColors.Accent400, style = MaterialTheme.typography.titleMedium)
        if (state.recruitingCities.isEmpty()) {
            Text(stringResource(Res.string.web_no_recruiting_cities), color = taxiColors.Navy200)
        } else {
            state.recruitingCities.forEach { city ->
                Surface(color = taxiColors.Navy900, shape = MaterialTheme.shapes.large) {
                    Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
                        Text(city.name.forLanguage(language), color = Color.White, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        Text(
            stringResource(Res.string.web_document_hint),
            color = taxiColors.Navy200,
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@Composable
private fun AuthenticationPanel(
    state: ApplicantPortalState,
    coordinator: ApplicantPortalCoordinator,
    draft: ApplicantAuthDraft,
    modifier: Modifier,
    independentlyScrollable: Boolean,
) {
    val identifierLabel = stringResource(Res.string.web_identifier)
    val passwordLabel = stringResource(Res.string.password)
    val fullNameLabel = stringResource(Res.string.web_full_name)
    val emailLabel = stringResource(Res.string.web_optional_email)
    val phoneLabel = stringResource(Res.string.web_optional_phone)
    val taxiColors = TaxiTheme.colors
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
        Column(Modifier.widthIn(max = 520.dp).fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Text(
                if (state.authMode == ApplicantAuthMode.SIGN_IN) stringResource(Res.string.web_continue_application) else stringResource(Res.string.web_create_applicant),
                style = MaterialTheme.typography.headlineSmall,
                color = taxiColors.Navy900,
                fontWeight = FontWeight.Bold,
            )
            Text(
                if (state.authMode == ApplicantAuthMode.SIGN_IN) {
                    stringResource(Res.string.web_applicant_sign_in_hint)
                } else {
                    stringResource(Res.string.web_applicant_register_hint)
                },
                color = taxiColors.Ink500,
            )
            state.error?.let { ApplicantMessageBanner(it, error = true, onDismiss = coordinator::dismissError) }
            if (state.catalogUnavailable) {
                OutlinedButton(onClick = coordinator::refresh, enabled = !busy,
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md)) {
                    Text(stringResource(Res.string.web_retry))
                }
            }
            state.notice?.let { ApplicantMessageBanner(it, error = false, onDismiss = coordinator::dismissNotice) }
            if (state.authMode == ApplicantAuthMode.CREATE_ACCOUNT) {
                OutlinedTextField(draft.displayName, { draft.displayName = it.take(120) },
                    Modifier.fillMaxWidth().semantics { contentDescription = fullNameLabel },
                    label = { Text(fullNameLabel) }, singleLine = true, enabled = !busy,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(
                        fontFamily = if (org.example.taximobile.feature.ui.text.hasArabicScript(draft.displayName))
                            org.example.taximobile.feature.ui.theme.taxiArabicFontFamily()
                        else MaterialTheme.typography.bodyLarge.fontFamily,
                    ))
                OutlinedTextField(draft.email, { draft.email = it.take(320) },
                    Modifier.fillMaxWidth().semantics { contentDescription = emailLabel },
                    label = { Text(emailLabel) }, singleLine = true, enabled = !busy,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr))
                OutlinedTextField(draft.phone, { draft.phone = it.take(32) },
                    Modifier.fillMaxWidth().semantics { contentDescription = phoneLabel },
                    label = { Text(phoneLabel) }, singleLine = true, enabled = !busy,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr))
            } else {
                OutlinedTextField(draft.identifier, { draft.identifier = it.take(320) },
                    Modifier.fillMaxWidth().semantics { contentDescription = identifierLabel },
                    label = { Text(identifierLabel) }, singleLine = true, enabled = !busy,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr))
            }
            OutlinedTextField(
                draft.password,
                { draft.password = it.take(256) },
                Modifier.fillMaxWidth().semantics { contentDescription = passwordLabel },
                label = { Text(passwordLabel) },
                textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                singleLine = true,
                enabled = !busy,
                visualTransformation = PasswordVisualTransformation(),
            )
            Button(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                onClick = {
                    if (state.authMode == ApplicantAuthMode.SIGN_IN) coordinator.login(draft.identifier, draft.password)
                    else coordinator.register(draft.displayName, draft.email, draft.phone, draft.password)
                },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth().height(56.dp),
            ) {
                if (busy) {
                    CircularProgressIndicator(Modifier.height(20.dp), strokeWidth = 2.dp)
                    Text(stringResource(Res.string.web_signing_in))
                } else {
                    Text(if (state.authMode == ApplicantAuthMode.SIGN_IN) stringResource(Res.string.sign_in) else stringResource(Res.string.web_create_account))
                }
            }
            OutlinedButton(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                onClick = {
                    coordinator.setAuthMode(
                        if (state.authMode == ApplicantAuthMode.SIGN_IN) ApplicantAuthMode.CREATE_ACCOUNT
                        else ApplicantAuthMode.SIGN_IN,
                    )
                },
                enabled = !busy,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (state.authMode == ApplicantAuthMode.SIGN_IN) stringResource(Res.string.web_create_account) else stringResource(Res.string.back_to_sign_in))
            }
            HorizontalDivider(color = taxiColors.StrokeSubtle)
            Text(stringResource(Res.string.web_session_security), style = MaterialTheme.typography.labelMedium, color = taxiColors.Navy700)
            Text(
                stringResource(Res.string.web_private_browser),
                style = MaterialTheme.typography.bodySmall,
                color = taxiColors.Ink500,
            )
        }
    }
}

@Composable
private fun ApplicantDashboard(
    state: ApplicantPortalState,
    coordinator: ApplicantPortalCoordinator,
) {
    val taxiColors = TaxiTheme.colors
    val language = Locale.current.language
    Column(org.example.taximobile.feature.ui.components.taxiTaskSurface(Modifier.fillMaxSize())) {
        Surface(color = taxiColors.Navy950) {
            Row(
                Modifier.fillMaxWidth().padding(horizontal = TaxiSpacing.Xl, vertical = TaxiSpacing.Md),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                ApplicantWordmark(dark = true)
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = coordinator::refresh,
                        enabled = !state.interactionLocked,
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White,
                            disabledContentColor = Color.White.copy(alpha = 0.38f)),
                    ) { Text(stringResource(Res.string.web_refresh)) }
                    Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = coordinator::logout, enabled = !state.interactionLocked) { Text(stringResource(Res.string.sign_out)) }
                }
            }
        }
        Column(
            Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
        ) {
            val welcome = stringResource(Res.string.web_app_welcome, state.account?.displayName.orEmpty())
            Text(welcome, style = MaterialTheme.typography.headlineMedium.copy(
                fontFamily = recruitmentTextStyle(welcome).fontFamily, textDirection = TextDirection.Content),
                color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text(stringResource(Res.string.web_app_scope_notice), color = taxiColors.Ink500)
            state.busyLabel?.let {
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm), verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.height(20.dp), strokeWidth = 2.dp)
                    Text(it.resolve(), color = taxiColors.Navy700)
                }
            }
            state.error?.let { ApplicantMessageBanner(it, error = true, onDismiss = coordinator::dismissError) }
            state.notice?.let { ApplicantMessageBanner(it, error = false, onDismiss = coordinator::dismissNotice) }

            Text(stringResource(Res.string.driver_city_applications), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            if (state.applications.isEmpty()) {
                ApplicantCard { Text(stringResource(Res.string.web_app_none), color = taxiColors.Ink500) }
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
                        Text(stringResource(Res.string.web_app_version_revision, ltrIsolate(application.requirementVersion), application.optimisticVersion),
                            color = taxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                        application.latestApplicantMessage?.let { Text(it, color = taxiColors.Navy700, style = recruitmentTextStyle(it)) }
                    }
                }
            }

            Text(stringResource(Res.string.recruiting_cities), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            if (state.recruitingCities.isEmpty()) {
                Text(stringResource(Res.string.no_recruiting_cities), color = taxiColors.Ink500)
            }
            state.recruitingCities.forEach { city ->
                val existing = state.applications.firstOrNull { it.cityId == city.id && it.status in OPEN_STATUSES }
                ApplicantCard {
                    Text(city.name.forLanguage(language), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(stringResource(Res.string.requirement_version_value, ltrIsolate(city.requirementVersion)), color = taxiColors.Ink500)
                    ApplicantPrimaryButton(
                        label = stringResource(if (existing == null) Res.string.start_city_application else Res.string.continue_application),
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
