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
import org.example.taximobile.operations.model.OperationsDestination
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsSessionPhase
import org.example.taximobile.operations.state.OperationsUiState

@Composable
fun OperationsApp(coordinator: OperationsCoordinator) {
    val state by coordinator.state.collectAsState()
    TaxiTheme {
        Surface(modifier = Modifier.fillMaxSize(), color = TaxiColors.Surface1) {
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

@Composable
private fun OperationsLogin(
    state: OperationsUiState,
    onLogin: (String, String) -> Unit,
    onDismissError: () -> Unit,
) {
    var identifier by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val busy = state.sessionPhase == OperationsSessionPhase.SIGNING_IN
    BoxWithConstraints(Modifier.fillMaxSize().background(TaxiColors.Navy950)) {
        val wide = maxWidth >= 860.dp
        if (wide) {
            Row(Modifier.fillMaxSize()) {
                LoginBrandPanel(Modifier.weight(1f))
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .background(TaxiColors.Surface1)
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
                    .background(TaxiColors.Surface1)
                    .verticalScroll(rememberScrollState())
                    .padding(TaxiSpacing.Xl),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Surface(
                    color = TaxiColors.Navy950,
                    shape = RoundedCornerShape(TaxiRadii.Lg),
                    modifier = Modifier.fillMaxWidth().widthIn(max = 520.dp),
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
    Column(
        modifier = modifier.fillMaxHeight().padding(64.dp),
        verticalArrangement = Arrangement.SpaceBetween,
    ) {
        OperationsWordmark()
        Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg)) {
            Text(
                "Deploy city by city.\nKeep authority explicit.",
                color = Color.White,
                style = MaterialTheme.typography.displaySmall,
                fontWeight = FontWeight.Bold,
            )
            Text(
                "A protected control plane for rollout readiness, city configuration, operator authority, scoped staff access, and audit review.",
                color = TaxiColors.Navy200,
                style = MaterialTheme.typography.bodyLarge,
                modifier = Modifier.widthIn(max = 520.dp),
            )
        }
        Text(
            "National operations · Staged city rollout",
            color = TaxiColors.Accent400,
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
    Surface(
        modifier = Modifier.fillMaxWidth().widthIn(max = 480.dp),
        color = TaxiColors.Surface0,
        shape = RoundedCornerShape(TaxiRadii.Xl),
        border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
        shadowElevation = 4.dp,
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Xxl),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
        ) {
            Text("Operations sign in", style = MaterialTheme.typography.headlineSmall, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text(
                "Use an active account with an explicitly bootstrapped operations grant.",
                style = MaterialTheme.typography.bodyMedium,
                color = TaxiColors.Ink500,
            )
            Surface(
                color = TaxiColors.Warning100,
                shape = RoundedCornerShape(TaxiRadii.Md),
                border = BorderStroke(1.dp, TaxiColors.Warning600.copy(alpha = 0.25f)),
            ) {
                Text(
                    "Production requires an enrolled authenticator factor. Password-only access remains restricted to explicitly configured local/test environments.",
                    modifier = Modifier.padding(TaxiSpacing.Md),
                    color = TaxiColors.Warning600,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            state.error?.let {
                MessageBanner(it, error = true, onDismiss = onDismissError)
            }
            OutlinedTextField(
                value = identifier,
                onValueChange = { if (it.length <= 320) onIdentifier(it) },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Email or phone" },
                label = { Text("Email or phone") },
                singleLine = true,
                enabled = !busy,
            )
            OutlinedTextField(
                value = password,
                onValueChange = { if (it.length <= 256) onPassword(it) },
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Password" },
                label = { Text("Password") },
                singleLine = true,
                enabled = !busy,
                visualTransformation = PasswordVisualTransformation(),
            )
            Button(
                onClick = { onLogin(identifier, password) },
                enabled = !busy && identifier.isNotBlank() && password.length >= 8,
                modifier = Modifier.fillMaxWidth().height(52.dp),
            ) {
                if (busy) {
                    CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = TaxiColors.Navy950)
                    Spacer(Modifier.width(TaxiSpacing.Sm))
                    Text("Verifying scoped access…")
                } else {
                    Text("Sign in")
                }
            }
            HorizontalDivider(color = TaxiColors.StrokeSubtle)
            Text("API", style = MaterialTheme.typography.labelSmall, color = TaxiColors.Ink500)
            Text(
                state.apiBaseUrl,
                color = TaxiColors.Navy700,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
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
    var code by remember { mutableStateOf("") }
    val busy = state.sessionPhase == OperationsSessionPhase.VERIFYING_MFA
    Box(
        Modifier.fillMaxSize().background(TaxiColors.Navy950).padding(TaxiSpacing.Xl),
        contentAlignment = Alignment.Center,
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth().widthIn(max = 480.dp),
            color = TaxiColors.Surface0,
            shape = RoundedCornerShape(TaxiRadii.Xl),
            border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
            shadowElevation = 4.dp,
        ) {
            Column(
                Modifier.padding(TaxiSpacing.Xxl),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Text("Verify your second factor", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(
                    "Enter the current six-digit code from your authenticator app. An unused recovery code also works once.",
                    color = TaxiColors.Ink500,
                )
                state.mfaChallengeExpiresIn?.let {
                    Text("This password challenge expires in ${it / 60} minutes.", style = MaterialTheme.typography.bodySmall)
                }
                state.error?.let { MessageBanner(it, error = true, onDismiss = onDismissError) }
                OutlinedTextField(
                    value = code,
                    onValueChange = { if (it.length <= 32) code = it.uppercase() },
                    modifier = Modifier.fillMaxWidth().semantics { contentDescription = "Authenticator or recovery code" },
                    label = { Text("Authenticator or recovery code") },
                    singleLine = true,
                    enabled = !busy,
                )
                Button(
                    onClick = { onVerify(code) },
                    enabled = !busy && code.length >= 6,
                    modifier = Modifier.fillMaxWidth().height(52.dp),
                ) {
                    if (busy) {
                        CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                        Spacer(Modifier.width(TaxiSpacing.Sm))
                    }
                    Text(if (busy) "Verifying…" else "Verify and continue")
                }
                OutlinedButton(onClick = onCancel, enabled = !busy, modifier = Modifier.fillMaxWidth()) {
                    Text("Cancel sign in")
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
    Column(
        modifier = modifier.background(TaxiColors.Navy950).padding(TaxiSpacing.Lg),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        OperationsWordmark()
        HorizontalDivider(color = TaxiColors.Navy800)
        Text("CONTROL PLANE", color = TaxiColors.Navy300, style = MaterialTheme.typography.labelSmall)
        Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            state.destinations.forEach { destination ->
                SidebarDestination(
                    destination = destination,
                    selected = destination == state.destination,
                    enabled = !state.interactionLocked,
                    onClick = { onDestination(destination) },
                )
            }
        }
        Spacer(Modifier.weight(1f))
        Surface(
            color = TaxiColors.Navy900,
            shape = RoundedCornerShape(TaxiRadii.Md),
        ) {
            Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Text("Signed in", color = TaxiColors.Navy300, style = MaterialTheme.typography.labelSmall)
                Text(shortId(state.session?.userId), color = Color.White, style = MaterialTheme.typography.bodyMedium)
                Text(
                    state.authenticationStrength?.replace('_', ' ') ?: "Operations session",
                    color = TaxiColors.Accent400,
                    style = MaterialTheme.typography.labelSmall,
                )
                if (state.authenticationStrength?.contains("MFA") == true) {
                    OutlinedButton(
                        onClick = onStepUp,
                        modifier = Modifier.fillMaxWidth(),
                        border = BorderStroke(1.dp, TaxiColors.Navy600),
                    ) {
                        Text("Reverify MFA", color = Color.White)
                    }
                }
                OutlinedButton(
                    onClick = onLogout,
                    modifier = Modifier.fillMaxWidth(),
                    border = BorderStroke(1.dp, TaxiColors.Navy600),
                ) {
                    Text("Sign out", color = Color.White)
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
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(enabled = enabled, onClick = onClick),
        color = if (selected) TaxiColors.Accent500 else Color.Transparent,
        shape = RoundedCornerShape(TaxiRadii.Md),
    ) {
        Column(Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm)) {
            Text(
                destination.title,
                color = if (selected) TaxiColors.Navy950 else Color.White,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Bold,
            )
            Text(
                destination.supportingText,
                color = if (selected) TaxiColors.Navy700 else TaxiColors.Navy300,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
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
) {
    Column(Modifier.fillMaxWidth().background(TaxiColors.Navy950)) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OperationsWordmark(compact = true)
            Text(
                "National operations",
                modifier = Modifier.padding(start = TaxiSpacing.Sm).weight(1f),
                color = Color.White,
                fontWeight = FontWeight.Bold,
            )
            if (state.authenticationStrength?.contains("MFA") == true) {
                OutlinedButton(onClick = onStepUp, border = BorderStroke(1.dp, TaxiColors.Navy600)) {
                    Text("Verify MFA", color = Color.White)
                }
                Spacer(Modifier.width(TaxiSpacing.Xs))
            }
            OutlinedButton(onClick = onLogout, border = BorderStroke(1.dp, TaxiColors.Navy600)) {
                Text("Sign out", color = Color.White)
            }
        }
        Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Xs),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
        ) {
            state.destinations.forEach { destination ->
                Surface(
                    modifier = Modifier.clickable(enabled = !state.interactionLocked) { onDestination(destination) },
                    color = if (destination == state.destination) TaxiColors.Accent500 else TaxiColors.Navy900,
                    shape = CircleShape,
                ) {
                    Text(
                        destination.title,
                        modifier = Modifier.padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Xs),
                        color = if (destination == state.destination) TaxiColors.Navy950 else Color.White,
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
    var code by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Reverify sensitive access") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text("A current authenticator or unused recovery code unlocks protected commands for ten minutes. A rejected command is never replayed automatically.")
                OutlinedTextField(
                    value = code,
                    onValueChange = { if (it.length <= 32) code = it.uppercase() },
                    label = { Text("Authenticator or recovery code") },
                    singleLine = true,
                    enabled = !busy,
                )
            }
        },
        confirmButton = {
            Button(onClick = { onVerify(code) }, enabled = !busy && code.length >= 6) {
                Text(if (busy) "Verifying…" else "Verify")
            }
        },
        dismissButton = { OutlinedButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}

@Composable
private fun OperationsWorkspace(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
    compact: Boolean,
    modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxHeight().background(TaxiColors.Surface1)) {
        ScopeTopBar(state, coordinator, compact)
        if (state.isRefreshing || state.mutationLabel != null) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth(), color = TaxiColors.Accent500, trackColor = TaxiColors.Navy100)
        } else {
            Spacer(Modifier.height(4.dp))
        }
        Column(
            Modifier.fillMaxWidth().padding(horizontal = if (compact) TaxiSpacing.Md else TaxiSpacing.Xl),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            state.mutationLabel?.let {
                Surface(color = TaxiColors.Info100, shape = RoundedCornerShape(TaxiRadii.Sm)) {
                    Text(
                        "$it. Waiting for backend authority…",
                        modifier = Modifier.fillMaxWidth().padding(TaxiSpacing.Sm),
                        color = TaxiColors.Info600,
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
    val snapshot = state.snapshot
    val market = snapshot?.markets?.items?.firstOrNull { it.id == state.scope.marketId }
    val operator = snapshot?.operators?.items?.firstOrNull { it.id == state.scope.operatorId }
    val city = snapshot?.cities?.items?.firstOrNull { it.id == state.scope.cityId }
    Column(
        Modifier.fillMaxWidth().background(TaxiColors.Surface0).padding(
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
            Column {
                Text(state.destination.title, color = TaxiColors.Navy900, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text("Active scope is presentation; backend grants remain authority.", color = TaxiColors.Ink500, style = MaterialTheme.typography.labelSmall)
            }
            OutlinedButton(onClick = coordinator::refresh, enabled = !state.interactionLocked) {
                Text("Refresh")
            }
        }
        Row(
            Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            ScopeMenu(
                label = "Market",
                selected = market?.name ?: "No market",
                options = snapshot?.markets?.items.orEmpty().map { ScopeOption(it.id, it.name) },
                enabled = !state.interactionLocked,
                onSelected = coordinator::selectMarket,
            )
            ScopeMenu(
                label = "Operator",
                selected = operator?.name ?: "All authorized",
                options = listOf(ScopeOption(null, "All authorized operators")) +
                    snapshot?.operators?.items.orEmpty().map { ScopeOption(it.id, it.name) },
                enabled = !state.interactionLocked,
                onSelected = coordinator::selectOperator,
            )
            ScopeMenu(
                label = "City",
                selected = city?.localizedName?.preferred() ?: "All authorized",
                options = listOf(ScopeOption(null, "All authorized cities")) +
                    snapshot?.cities?.items.orEmpty().map { ScopeOption(it.id, it.localizedName.preferred()) },
                enabled = !state.interactionLocked,
                onSelected = coordinator::selectCity,
            )
        }
    }
    HorizontalDivider(color = TaxiColors.StrokeSubtle)
}

@Composable
private fun InitialLoading() {
    Column(
        Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        CircularProgressIndicator(color = TaxiColors.Accent500)
        Spacer(Modifier.height(TaxiSpacing.Md))
        Text("Loading authorized operations scope…", color = TaxiColors.Ink700)
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
            title = "Operations data is unavailable",
            detail = "Retry performs read-only scope/session loading and never replays a failed mutation.",
            modifier = Modifier.widthIn(max = 560.dp),
        )
        Spacer(Modifier.height(TaxiSpacing.Md))
        Button(onClick = onRetry) { Text("Retry connection") }
    }
}
