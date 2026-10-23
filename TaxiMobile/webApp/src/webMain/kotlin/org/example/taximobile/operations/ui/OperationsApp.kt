package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.theme.TaxiTheme
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.text.style.TextDirection
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.operations.model.OperationsDestination
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsSessionPhase
import org.example.taximobile.operations.state.OperationsUiState

@Composable
fun OperationsApp(coordinator: OperationsCoordinator) {
    val state by coordinator.state.collectAsState()
    TaxiTheme {
        val taxiColors = TaxiTheme.colors
        Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            org.example.taximobile.feature.ui.components.TaxiStyleChooser(Modifier.weight(1f))
            org.example.taximobile.feature.ui.components.TaxiLanguageChooser()
        }
        Surface(modifier = Modifier.weight(1f).fillMaxWidth(), color = taxiColors.Surface1) {
            when (state.sessionPhase) {
                OperationsSessionPhase.SIGNED_OUT,
                OperationsSessionPhase.SIGNING_IN,
                -> OperationsLogin(
                    state = state,
                    onLogin = coordinator::login,
                    onDismissError = coordinator::dismissError,
                )

                OperationsSessionPhase.MFA_REQUIRED,
                OperationsSessionPhase.VERIFYING_MFA,
                -> OperationsMfaVerification(
                    state = state,
                    onVerify = coordinator::verifyMfa,
                    onCancel = coordinator::cancelMfa,
                    onDismissError = coordinator::dismissError,
                )

                OperationsSessionPhase.SIGNED_IN -> OperationsShell(
                    state = state,
                    coordinator = coordinator,
                )
            }
        }
        }
    }
}

@Composable
private fun OperationsLogin(
    state: OperationsUiState,
    onLogin: (String, String) -> Unit,
    onDismissError: () -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    var identifier by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val busy = state.sessionPhase == OperationsSessionPhase.SIGNING_IN
    BoxWithConstraints(Modifier.fillMaxSize().background(taxiColors.Navy950)) {
        val wide = maxWidth >= 860.dp
        if (wide) {
            Row(Modifier.fillMaxSize()) {
                LoginBrandPanel(Modifier.weight(1f))
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .background(taxiColors.Surface1)
                        .verticalScroll(rememberScrollState())
                        .padding(vertical = TaxiSpacing.Xl),
                    contentAlignment = Alignment.Center,
                ) {
                    LoginCard(
                        state = state,
                        identifier = identifier,
                        password = password,
                        busy = busy,
                        onIdentifier = { identifier = it },
                        onPassword = { password = it },
                        onLogin = onLogin,
                        onDismissError = onDismissError,
                    )
                }
            }
        } else {
            Column(
                Modifier
                    .fillMaxSize()
                    .background(taxiColors.Surface1)
                    .verticalScroll(rememberScrollState())
                    .padding(TaxiSpacing.Xl),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Surface(
                    color = taxiColors.Navy950,
                    shape = RoundedCornerShape(taxiRadii.Lg),
                    modifier = Modifier.widthIn(max = 520.dp).fillMaxWidth(),
                ) {
                    Row(Modifier.padding(TaxiSpacing.Lg), verticalAlignment = Alignment.CenterVertically) {
                        OperationsWordmark()
                    }
                }
                Spacer(Modifier.height(TaxiSpacing.Md))
                LoginCard(
                    state = state,
                    identifier = identifier,
                    password = password,
                    busy = busy,
                    onIdentifier = { identifier = it },
                    onPassword = { password = it },
                    onLogin = onLogin,
                    onDismissError = onDismissError,
                )
            }
        }
    }
}

@Composable
private fun LoginBrandPanel(modifier: Modifier = Modifier) {
    val taxiColors = TaxiTheme.colors
    Column(
        modifier = modifier.fillMaxHeight().padding(64.dp),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        OperationsWordmark()
        Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg)) {
            org.example.taximobile.feature.ui.components.TaxiEntryFrame()
            Text(
                stringResource(Res.string.web_ops_hero),
                color = Color.White,
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                stringResource(Res.string.web_ops_intro),
                color = taxiColors.Navy200,
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.widthIn(max = 520.dp),
            )
        }
        Text(
            stringResource(Res.string.web_ops_footer),
            color = taxiColors.Accent400,
            style = MaterialTheme.typography.labelMedium,
        )
    }
}

@Composable
private fun LoginCard(
    state: OperationsUiState,
    identifier: String,
    password: String,
    busy: Boolean,
    onIdentifier: (String) -> Unit,
    onPassword: (String) -> Unit,
    onLogin: (String, String) -> Unit,
    onDismissError: () -> Unit,
) {
    val identifierLabel = stringResource(Res.string.web_identifier)
    val passwordLabel = stringResource(Res.string.password)
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = Modifier.widthIn(max = 480.dp).fillMaxWidth(),
        color = taxiColors.Surface0,
        shape = RoundedCornerShape(taxiRadii.Xl),
        border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
        shadowElevation = if (TaxiTheme.style == org.example.taximobile.feature.ui.theme.TaxiStyle.Notepad) 0.dp else 4.dp,
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Xxl),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
        ) {
            Text(stringResource(Res.string.web_ops_sign_in), style = MaterialTheme.typography.headlineSmall, color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text(
                stringResource(Res.string.web_ops_access_hint),
                style = MaterialTheme.typography.bodyMedium,
                color = taxiColors.Ink500,
            )
            Surface(
                color = taxiColors.Warning100,
                shape = RoundedCornerShape(taxiRadii.Md),
                border = BorderStroke(1.dp, taxiColors.Warning600.copy(alpha = 0.25f)),
            ) {
                Text(
                    stringResource(Res.string.web_ops_factor_hint),
                    modifier = Modifier.padding(TaxiSpacing.Md),
                    color = taxiColors.Warning600,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            state.error?.let {
                MessageBanner(it, error = true, onDismiss = onDismissError)
            }
            OutlinedTextField(
                value = identifier,
                onValueChange = { if (it.length <= 320) onIdentifier(it) },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = identifierLabel },
                label = { Text(stringResource(Res.string.web_identifier)) },
                textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                singleLine = true,
                enabled = !busy,
            )
            OutlinedTextField(
                value = password,
                onValueChange = { if (it.length <= 256) onPassword(it) },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = passwordLabel },
                label = { Text(stringResource(Res.string.password)) },
                textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                singleLine = true,
                enabled = !busy,
                visualTransformation = PasswordVisualTransformation(),
            )
            Button(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                onClick = { onLogin(identifier, password) },
                enabled = !busy && identifier.isNotBlank() && password.length >= 8,
                modifier = Modifier.fillMaxWidth().height(56.dp),
            ) {
                if (busy) {
                    CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                    Spacer(Modifier.width(TaxiSpacing.Sm))
                    Text(stringResource(Res.string.web_signing_in))
                } else {
                    Text(stringResource(Res.string.sign_in))
                }
            }
            if (state.isLocalDevelopment) {
                HorizontalDivider(color = taxiColors.StrokeSubtle)
                Text("API", style = MaterialTheme.typography.labelSmall, color = taxiColors.Ink500)
                Text(ltrIsolate(state.apiBaseUrl), color = taxiColors.Navy700,
                    style = MaterialTheme.typography.bodySmall, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
        }
    }
}

@Composable
private fun OperationsMfaVerification(
    state: OperationsUiState,
    onVerify: (String) -> Unit,
    onCancel: () -> Unit,
    onDismissError: () -> Unit,
) {
    val codeLabel = stringResource(Res.string.web_mfa_code)
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    var code by remember { mutableStateOf("") }
    val busy = state.sessionPhase == OperationsSessionPhase.VERIFYING_MFA
    Box(
        Modifier.fillMaxSize().background(taxiColors.Navy950)
            .verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            modifier = Modifier.widthIn(max = 480.dp).fillMaxWidth(),
            color = taxiColors.Surface0,
            shape = RoundedCornerShape(taxiRadii.Xl),
            border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
            shadowElevation = if (TaxiTheme.style == org.example.taximobile.feature.ui.theme.TaxiStyle.Notepad) 0.dp else 4.dp,
        ) {
            Column(
                Modifier.padding(TaxiSpacing.Xxl),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Text(stringResource(Res.string.web_mfa_title), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(
                    stringResource(Res.string.web_mfa_help),
                    color = taxiColors.Ink500,
                )
                state.mfaChallengeExpiresIn?.let {
                    Text(stringResource(Res.string.web_mfa_expires, it / 60), style = MaterialTheme.typography.bodySmall)
                }
                state.error?.let { MessageBanner(it, error = true, onDismiss = onDismissError) }
                OutlinedTextField(
                    value = code,
                    onValueChange = { if (it.length <= 32) code = it.uppercase() },
                    modifier = Modifier.fillMaxWidth().semantics { contentDescription = codeLabel },
                    label = { Text(stringResource(Res.string.web_mfa_code)) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                    singleLine = true,
                    enabled = !busy,
                )
                Button(
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                    onClick = { onVerify(code) },
                    enabled = !busy && code.length >= 6,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                ) {
                    if (busy) {
                        CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                        Spacer(Modifier.width(TaxiSpacing.Sm))
                    }
                    Text(if (busy) stringResource(Res.string.web_verifying) else stringResource(Res.string.web_verify_continue))
                }
                OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onCancel, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                    Text(stringResource(Res.string.web_cancel_sign_in))
                }
            }
        }
    }
}

@Composable
private fun OperationsShell(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    BoxWithConstraints(Modifier.fillMaxSize()) {
        val desktop = maxWidth >= 980.dp
        val narrow = maxWidth < 600.dp
        if (desktop) {
            Row(Modifier.fillMaxSize()) {
                OperationsSidebar(
                    state = state,
                    onDestination = coordinator::selectDestination,
                    onStepUp = coordinator::showMfaStepUp,
                    onLogout = coordinator::logout,
                    modifier = Modifier.width(260.dp).fillMaxHeight(),
                )
                OperationsWorkspace(state, coordinator, compact = false, modifier = Modifier.weight(1f))
            }
        } else {
            Column(Modifier.fillMaxSize()) {
                CompactNavigation(
                    state = state,
                    onDestination = coordinator::selectDestination,
                    onStepUp = coordinator::showMfaStepUp,
                    onLogout = coordinator::logout,
                    narrow = narrow,
                )
                OperationsWorkspace(state, coordinator, compact = true, modifier = Modifier.weight(1f))
            }
        }
        if (state.showMfaStepUp) {
            MfaStepUpDialog(
                busy = state.mutationLabel == "Verifying MFA",
                onDismiss = coordinator::dismissMfaStepUp,
                onVerify = coordinator::stepUpMfa,
            )
        }
    }
}

@Composable
private fun OperationsSidebar(
    state: OperationsUiState,
    onDestination: (OperationsDestination) -> Unit,
    onStepUp: () -> Unit,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Column(
        modifier = modifier.background(taxiColors.Navy950).padding(TaxiSpacing.Lg),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        OperationsWordmark()
        HorizontalDivider(color = taxiColors.Navy800)
        Text(stringResource(Res.string.web_workspace), color = taxiColors.Navy300, style = MaterialTheme.typography.labelSmall)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            state.destinations.forEach { destination ->
                SidebarDestination(
                    destination = destination,
                    selected = destination == state.destination,
                    enabled = !state.interactionLocked,
                    onClick = { onDestination(destination) },
                )
            }
        }
        Surface(
            color = taxiColors.Navy900,
            shape = RoundedCornerShape(taxiRadii.Md),
        ) {
            Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Text(stringResource(Res.string.web_signed_in), color = taxiColors.Navy300, style = MaterialTheme.typography.labelSmall)
                Text(ltrIsolate(shortId(state.session?.userId)), color = Color.White, style = MaterialTheme.typography.bodyMedium)
                Text(
                    stringResource(if (state.authenticationStrength?.contains("MFA") == true)
                        Res.string.web_mfa_verified else Res.string.web_staff_session),
                    color = taxiColors.Accent400,
                    style = MaterialTheme.typography.labelSmall,
                )
                if (state.authenticationStrength?.contains("MFA") == true) {
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = onStepUp,
                        modifier = Modifier.fillMaxWidth(),
                        border = BorderStroke(1.dp, taxiColors.Navy600),
                    ) {
                        Text(stringResource(Res.string.web_reverify), color = Color.White)
                    }
                }
                OutlinedButton(
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                    onClick = onLogout,
                    modifier = Modifier.fillMaxWidth(),
                    border = BorderStroke(1.dp, taxiColors.Navy600),
                ) {
                    Text(stringResource(Res.string.sign_out), color = Color.White)
                }
            }
        }
    }
}

@Composable
private fun SidebarDestination(
    destination: OperationsDestination,
    selected: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick),
        color = if (selected) taxiColors.Accent500 else Color.Transparent,
        shape = RoundedCornerShape(taxiRadii.Md),
    ) {
        Column(Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm)) {
            Text(
                stringResource(destination.titleResource()),
                color = if (selected) MaterialTheme.colorScheme.onPrimary else Color.White,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
private fun CompactNavigation(
    state: OperationsUiState,
    onDestination: (OperationsDestination) -> Unit,
    onStepUp: () -> Unit,
    onLogout: () -> Unit,
    narrow: Boolean,
) {
    val taxiColors = TaxiTheme.colors
    Column(Modifier.fillMaxWidth().background(taxiColors.Navy950)) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OperationsWordmark(compact = true)
            if (narrow) Spacer(Modifier.weight(1f)) else Text(
                stringResource(Res.string.web_operations),
                modifier = Modifier.padding(start = TaxiSpacing.Sm).weight(1f),
                color = Color.White,
                fontWeight = FontWeight.Bold,
            )
            if (state.authenticationStrength?.contains("MFA") == true) {
                OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onStepUp, border = BorderStroke(1.dp, taxiColors.Navy600)) {
                    Text(stringResource(Res.string.web_verify), color = Color.White)
                }
                Spacer(Modifier.width(TaxiSpacing.Xs))
            }
            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onLogout, border = BorderStroke(1.dp, taxiColors.Navy600)) {
                Text(stringResource(Res.string.sign_out), color = Color.White)
            }
        }
        Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Xs),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
        ) {
            state.destinations.forEach { destination ->
                Surface(
                    modifier = Modifier.clickable(enabled = !state.interactionLocked) { onDestination(destination) },
                    color = if (destination == state.destination) taxiColors.Accent500 else taxiColors.Navy900,
                    shape = RoundedCornerShape(TaxiTheme.radii.Pill),
                ) {
                    Text(
                        stringResource(destination.titleResource()),
                        modifier = Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Xs),
                        color = if (destination == state.destination) MaterialTheme.colorScheme.onPrimary else Color.White,
                        style = MaterialTheme.typography.labelMedium,
                    )
                }
            }
        }
    }
}

@Composable
private fun MfaStepUpDialog(
    busy: Boolean,
    onDismiss: () -> Unit,
    onVerify: (String) -> Unit,
) {
    val codeLabel = stringResource(Res.string.web_mfa_code)
    var code by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(Res.string.web_step_up_title)) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(stringResource(Res.string.web_step_up_help))
                OutlinedTextField(
                    value = code,
                    onValueChange = { if (it.length <= 32) code = it.uppercase() },
                    modifier = Modifier.semantics { contentDescription = codeLabel },
                    label = { Text(stringResource(Res.string.web_mfa_code)) },
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                    singleLine = true,
                    enabled = !busy,
                )
            }
        },
        confirmButton = {
            Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onVerify(code) }, enabled = !busy && code.length >= 6) {
                Text(if (busy) stringResource(Res.string.web_verifying) else stringResource(Res.string.web_verify))
            }
        },
        dismissButton = { OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onDismiss, enabled = !busy) { Text(stringResource(Res.string.web_cancel)) } },
    )
}

@Composable
private fun OperationsWorkspace(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
    compact: Boolean,
    modifier: Modifier = Modifier,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Column(org.example.taximobile.feature.ui.components.taxiTaskSurface(
        modifier.fillMaxHeight().background(taxiColors.Surface1),
    )) {
        ScopeTopBar(state, coordinator, compact)
        if (state.isRefreshing || state.mutationLabel != null) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = taxiColors.Accent500, trackColor = taxiColors.Navy100)
        } else {
            Spacer(Modifier.height(4.dp))
        }
        Column(
            Modifier.fillMaxWidth().padding(horizontal = if (compact) TaxiSpacing.Md else TaxiSpacing.Xl),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            state.mutationLabel?.let {
                Surface(color = taxiColors.Info100, shape = RoundedCornerShape(taxiRadii.Sm)) {
                    Text(
                        stringResource(Res.string.web_pending_action),
                        modifier = Modifier.fillMaxWidth().padding(TaxiSpacing.Sm),
                        color = taxiColors.Info600,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
            state.error?.let { MessageBanner(it, error = true, onDismiss = coordinator::dismissError) }
            state.notice?.let { MessageBanner(it, error = false, onDismiss = coordinator::dismissNotice) }
        }
        Box(Modifier.fillMaxWidth().weight(1f)) {
            when {
                state.isInitialLoading -> InitialLoading()
                state.snapshot == null -> LoadFailure(onRetry = coordinator::retry)
                else -> when (state.destination) {
                    OperationsDestination.ROLLOUT -> RolloutScreen(state)
                    OperationsDestination.CITIES -> CitiesScreen(
                        state = state,
                        onSelectCity = coordinator::selectCity,
                        onCreateCity = coordinator::createCity,
                        onCreateServiceArea = coordinator::createServiceArea,
                        onTransitionServiceArea = coordinator::transitionServiceArea,
                        onCreateConfiguration = coordinator::createCityConfiguration,
                        onTransitionConfiguration = coordinator::transitionCityConfiguration,
                        onTransition = coordinator::transitionCity,
                        onReadinessDecision = coordinator::decideCityReadiness,
                    )
                    OperationsDestination.OPERATORS -> OperatorsScreen(
                        state = state,
                        onSelectOperator = coordinator::selectOperator,
                        onCreateOperator = coordinator::createOperator,
                        onUpdateOperatorStatus = coordinator::updateOperatorStatus,
                        onCreateAssignment = coordinator::createOperatorAssignment,
                        onRetireAssignment = coordinator::retireOperatorAssignment,
                    )
                    OperationsDestination.STAFF -> StaffAccessScreen(
                        state = state,
                        onCreateGrant = coordinator::createAdministrativeGrant,
                        onRevokeGrant = coordinator::revokeAdministrativeGrant,
                        onDecideRequest = coordinator::decideAdministrativeGrantRequest,
                    )
                    OperationsDestination.DRIVER_RECRUITMENT -> DriverRecruitmentScreen(state, coordinator)
                    OperationsDestination.PRICING_ECONOMICS -> PricingEconomicsScreen(state, coordinator)
                    OperationsDestination.PAYMENTS -> PaymentOperationsScreen(state, coordinator)
                    OperationsDestination.FIXED_ROUTES -> FixedRoutesScreen(state, coordinator)
                    OperationsDestination.SCHEDULED_EXCEPTIONS -> ScheduledExceptionsScreen(state)
                    OperationsDestination.ANALYTICS -> AnalyticsScreen(state)
                    OperationsDestination.CASE_OPERATIONS -> CaseOperationsScreen(state, coordinator)
                    OperationsDestination.ACCOUNT_SECURITY -> AccountSecurityScreen(state, coordinator)
                    OperationsDestination.SECURITY_INCIDENTS -> SecurityIncidentScreen(state, coordinator)
                    OperationsDestination.AUDIT -> AuditScreen(state)
                }
            }
        }
    }
}

@Composable
private fun ScopeTopBar(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
    compact: Boolean,
) {
    val taxiColors = TaxiTheme.colors
    val snapshot = state.snapshot
    val language = Locale.current.language
    val market = snapshot?.markets?.items?.firstOrNull { it.id == state.scope.marketId }
    val operator = snapshot?.operators?.items?.firstOrNull { it.id == state.scope.operatorId }
    val city = snapshot?.cities?.items?.firstOrNull { it.id == state.scope.cityId }
    Column(
        Modifier.fillMaxWidth().background(taxiColors.Surface0).padding(
            horizontal = if (compact) TaxiSpacing.Md else TaxiSpacing.Xl,
            vertical = TaxiSpacing.Sm,
        ),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(Modifier.weight(1f)) {
                Text(stringResource(state.destination.titleResource()), color = taxiColors.Navy900, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(stringResource(Res.string.web_scope_hint), color = taxiColors.Ink500, style = MaterialTheme.typography.labelSmall)
            }
            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = coordinator::refresh, enabled = !state.interactionLocked) {
                Text(stringResource(Res.string.web_refresh))
            }
        }
        Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            ScopeMenu(
                label = stringResource(Res.string.web_market),
                selected = market?.name ?: stringResource(Res.string.web_no_market),
                options = snapshot?.markets?.items.orEmpty().map { ScopeOption(it.id, it.name) },
                enabled = !state.interactionLocked,
                onSelected = coordinator::selectMarket,
            )
            ScopeMenu(
                label = stringResource(Res.string.web_operator),
                selected = operator?.name ?: stringResource(Res.string.web_all),
                options = listOf(ScopeOption(null, stringResource(Res.string.web_all_operators))) +
                    snapshot?.operators?.items.orEmpty().map { ScopeOption(it.id, it.name) },
                enabled = !state.interactionLocked,
                onSelected = coordinator::selectOperator,
            )
            ScopeMenu(
                label = stringResource(Res.string.web_city),
                selected = city?.localizedName?.preferred(language) ?: stringResource(Res.string.web_all),
                options = listOf(ScopeOption(null, stringResource(Res.string.web_all_cities))) +
                    snapshot?.cities?.items.orEmpty().map { ScopeOption(it.id, it.localizedName.preferred(language)) },
                enabled = !state.interactionLocked,
                onSelected = coordinator::selectCity,
            )
        }
    }
    HorizontalDivider(color = taxiColors.StrokeSubtle)
}

@Composable
private fun InitialLoading() {
    val taxiColors = TaxiTheme.colors
    Column(
        Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        CircularProgressIndicator(color = taxiColors.Accent500)
        Spacer(Modifier.height(TaxiSpacing.Md))
        Text(stringResource(Res.string.web_loading_scope), color = taxiColors.Ink700)
    }
}

@Composable
private fun LoadFailure(onRetry: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(TaxiSpacing.Xl),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        EmptyState(
            title = stringResource(Res.string.web_load_failed),
            detail = stringResource(Res.string.web_retry_read_only),
            modifier = Modifier.widthIn(max = 560.dp),
        )
        Spacer(Modifier.height(TaxiSpacing.Md))
        Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onRetry) { Text(stringResource(Res.string.web_retry)) }
    }
}
