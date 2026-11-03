package org.example.taximobile.operations.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlin.time.Clock
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.ADMINISTRATIVE_ROLE_TEMPLATES
import org.example.taximobile.operations.model.AdministrativeGrantCreateRequest
import org.example.taximobile.operations.model.AdministrativeGrantChangeRequestRecord
import org.example.taximobile.operations.model.AdministrativeGrantRecord
import org.example.taximobile.operations.model.AdministrativeGrantScopeKind
import org.example.taximobile.operations.model.StaffPageState
import org.example.taximobile.operations.model.MANAGE_SCOPED_STAFF_GRANTS
import org.example.taximobile.operations.model.administrativeGrantInputError
import org.example.taximobile.operations.model.administrativeRoleTemplate
import org.example.taximobile.operations.model.matchesSelectedScope
import org.example.taximobile.operations.state.OperationsUiState
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
internal fun StaffAccessScreen(
    state: OperationsUiState,
    onCreateGrant: (AdministrativeGrantCreateRequest) -> Unit,
    onRevokeGrant: (AdministrativeGrantRecord, String) -> Unit,
    onDecideRequest: (AdministrativeGrantChangeRequestRecord, String, String) -> Unit,
    onSelectRequestPage: (Int) -> Unit,
    onSelectGrantPage: (Int) -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    val snapshot = state.snapshot ?: return
    val grants = snapshot.grants
    val grantPage = grants?.let { StaffPageState(it.page, it.limit, it.total, it.items.size) }
    val mayManage = state.session?.hasPermission(MANAGE_SCOPED_STAFF_GRANTS) == true
    var showCreateDialog by remember { mutableStateOf(false) }
    var pendingRevocation by remember { mutableStateOf<AdministrativeGrantRecord?>(null) }
    var pendingDecision by remember {
        mutableStateOf<Pair<AdministrativeGrantChangeRequestRecord, String>?>(null)
    }
    val cityNames = snapshot.cities.items.associate { it.id to it.localizedName.preferred() }
    val operatorNames = snapshot.operators.items.associate { it.id to it.name }
    val marketNames = snapshot.markets.items.associate { it.id to it.name }
    val isSelectedMarket = state.scope.marketId != null && snapshot.staffMarketId == state.scope.marketId

    ScreenColumn {
        SectionHeading(
            title = "Scoped staff access",
            supportingText = "Recent MFA and independent approval are required.",
            action = {
                Button(
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                    onClick = { showCreateDialog = true },
                    enabled = mayManage && grants != null && state.scope.marketId != null && !state.interactionLocked,
                ) {
                    Text("Request access")
                }
            },
        )
        when {
            grants == null -> EmptyState(
                "Grant management not authorized",
                "This destination is available only to a market-scoped platform administrator.",
            )
            grantPage?.isCollectionEmpty == true -> EmptyState(
                "No active grants",
                "No active administrative grants were returned for this authorized market. Submit a request from an approved staff record.",
            )
            grantPage?.isPageStale == true -> EmptyState(
                stringResource(Res.string.web_staff_grants_stale_title),
                stringResource(Res.string.web_staff_grants_stale_detail),
            )
            else -> {
                DataCard(tableMinWidth = 1220.dp) {
                    Column(Modifier.fillMaxWidth().widthIn(min = 1220.dp)) {
                        TableHeader(
                            listOf(
                                "User" to 1.2f,
                                "Role" to 1.3f,
                                "Scope" to 1.6f,
                                "Granted" to 1.1f,
                                "Expiry / review" to 1.4f,
                                "Reason" to 1.8f,
                                "Action" to 1.0f,
                            )
                        )
                        grants.items.forEach { grant ->
                            val isCurrentUser = grant.userId.equals(state.session?.userId, ignoreCase = true)
                            val scopeLabel = scopeLabelForGrant(grant, marketNames, operatorNames, cityNames)
                            TableRow {
                                TableCell(shortId(grant.userId), 1.2f, supporting = if (isCurrentUser) "Current account" else null)
                                TableCell(grant.roleTemplate.replace('_', ' '), 1.3f)
                                TableCell(scopeLabel, 1.6f)
                                TableCell(compactTimestamp(grant.grantedAt), 1.1f, supporting = "By ${shortId(grant.grantedByUserId)}")
                                TableCell(
                                    grant.expiresAt?.let(::compactTimestamp) ?: "No expiry",
                                    1.4f,
                                    supporting = if (grant.expiresAt == null) "Manual recertification required" else "Review before expiry",
                                )
                                TableCell(grant.grantReason, 1.8f)
                                Box(Modifier.weight(1.0f)) {
                                    OutlinedButton(
                                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                                        onClick = { pendingRevocation = grant },
                                        enabled = !isCurrentUser && isSelectedMarket && !state.interactionLocked,
                                    ) {
                                        Text(
                                            when {
                                                isCurrentUser -> "Protected"
                                                !isSelectedMarket -> "Select market"
                                                else -> "Request revoke"
                                            }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        if (grants != null && grantPage != null && !grantPage.isCollectionEmpty) {
            StaffPageControls(
                grantPage,
                stringResource(Res.string.web_staff_grants_page, grants.page, grants.total),
                state.interactionLocked,
                onSelectGrantPage,
            )
        }
        val requests = snapshot.grantRequests
        val pending = requests?.items?.filter { it.status == "PENDING" }.orEmpty()
        val requestPage = requests?.let { StaffPageState(it.page, it.limit, it.total, pending.size) }
        SectionHeading(
            title = "Grant change queue",
            supportingText = "Pending requests require a different authorized administrator.",
        )
        when {
            requests == null -> EmptyState(
                "Request queue not authorized",
                "The active operations grant does not expose staff-change requests.",
            )
            requestPage?.isCollectionEmpty == true -> EmptyState(
                "No pending staff changes",
                stringResource(Res.string.web_staff_queue_empty_detail),
            )
            requestPage?.isPageStale == true -> EmptyState(
                stringResource(Res.string.web_staff_queue_stale_title),
                stringResource(Res.string.web_staff_queue_stale_detail),
            )
            else -> {
                DataCard(tableMinWidth = 1180.dp) {
                    Column(Modifier.fillMaxWidth().widthIn(min = 1180.dp)) {
                        TableHeader(
                            listOf(
                                "Request" to 1.0f,
                                "Change" to 1.2f,
                                "Target / role" to 1.5f,
                                "Scope" to 1.5f,
                                "Requester" to 1.1f,
                                "Reason" to 1.8f,
                                "Decision" to 1.8f,
                            )
                        )
                        pending.forEach { request ->
                            val currentUserId = state.session?.userId.orEmpty()
                            val isRequester = request.requesterUserId.equals(
                                currentUserId,
                                ignoreCase = true,
                            )
                            val isTarget = request.targetUserId.equals(
                                currentUserId,
                                ignoreCase = true,
                            )
                            TableRow {
                                TableCell(
                                    shortId(request.id),
                                    1.0f,
                                    supporting = "v${request.optimisticVersion}",
                                )
                                TableCell(request.action, 1.2f)
                                TableCell(
                                    shortId(request.targetUserId),
                                    1.5f,
                                    supporting = request.roleTemplate.replace('_', ' '),
                                )
                                TableCell(
                                    scopeLabelForRequest(
                                        request,
                                        marketNames,
                                        operatorNames,
                                        cityNames,
                                    ),
                                    1.5f,
                                )
                                TableCell(
                                    shortId(request.requesterUserId),
                                    1.1f,
                                    supporting = compactTimestamp(request.requestedAt),
                                )
                                TableCell(request.reason, 1.8f)
                                Box(Modifier.weight(1.8f)) {
                                    when {
                                        isRequester -> OutlinedButton(
                                            shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                                            onClick = { pendingDecision = request to "cancel" },
                                            enabled = !state.interactionLocked,
                                        ) { Text("Cancel request") }
                                        isTarget -> Text(
                                            "Target cannot decide",
                                            color = taxiColors.Ink500,
                                            style = MaterialTheme.typography.bodySmall,
                                        )
                                        else -> Row(
                                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
                                        ) {
                                            Button(
                                                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                                                onClick = { pendingDecision = request to "approve" },
                                                enabled = !state.interactionLocked,
                                            ) { Text("Approve") }
                                            OutlinedButton(
                                                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                                                onClick = { pendingDecision = request to "reject" },
                                                enabled = !state.interactionLocked,
                                            ) { Text("Reject") }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        if (requests != null && requestPage != null && !requestPage.isCollectionEmpty) {
            StaffPageControls(
                requestPage,
                stringResource(Res.string.web_staff_queue_page, requests.page, requests.total),
                state.interactionLocked,
                onSelectRequestPage,
            )
        }
    }

    if (showCreateDialog) {
        CreateAdministrativeGrantDialog(
            state = state,
            onDismiss = { showCreateDialog = false },
            onConfirm = { request ->
                showCreateDialog = false
                onCreateGrant(request)
            },
        )
    }
    pendingRevocation?.let { grant ->
        RevokeAdministrativeGrantDialog(
            grant = grant,
            scopeLabel = scopeLabelForGrant(grant, marketNames, operatorNames, cityNames),
            busy = state.mutationLabel != null,
            onDismiss = { pendingRevocation = null },
            onConfirm = { reason ->
                pendingRevocation = null
                onRevokeGrant(grant, reason)
            },
        )
    }
    pendingDecision?.let { (request, decision) ->
        AdministrativeGrantDecisionDialog(
            request = request,
            decision = decision,
            busy = state.mutationLabel != null,
            onDismiss = { pendingDecision = null },
            onConfirm = { reason ->
                pendingDecision = null
                onDecideRequest(request, decision, reason)
            },
        )
    }
}

@Composable
private fun StaffPageControls(
    page: StaffPageState,
    label: String,
    busy: Boolean,
    onSelect: (Int) -> Unit,
) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
        Text(label, style = MaterialTheme.typography.bodySmall)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            if (page.isPageStale) {
                OutlinedButton(onClick = { onSelect(page.page) }, enabled = !busy) {
                    Text(stringResource(Res.string.web_staff_queue_retry))
                }
            }
            OutlinedButton(onClick = { onSelect(page.page - 1) }, enabled = page.canPrevious && !busy) {
                Text(stringResource(Res.string.web_staff_queue_previous))
            }
            OutlinedButton(onClick = { onSelect(page.page + 1) }, enabled = page.canNext && !busy) {
                Text(stringResource(Res.string.web_staff_queue_next))
            }
        }
    }
}

@Composable
private fun CreateAdministrativeGrantDialog(
    state: OperationsUiState,
    onDismiss: () -> Unit,
    onConfirm: (AdministrativeGrantCreateRequest) -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    var userId by remember { mutableStateOf("") }
    var roleTemplate by remember { mutableStateOf("CITY_MANAGER") }
    var expiresAt by remember { mutableStateOf("") }
    var reason by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    val role = administrativeRoleTemplate(roleTemplate)!!
    val request = AdministrativeGrantCreateRequest(
        userId = userId.trim(),
        roleTemplate = roleTemplate,
        marketId = state.scope.marketId.takeIf { role.scopeKind == AdministrativeGrantScopeKind.MARKET },
        operatorId = state.scope.operatorId.takeIf { role.scopeKind == AdministrativeGrantScopeKind.OPERATOR },
        cityId = state.scope.cityId.takeIf { role.scopeKind == AdministrativeGrantScopeKind.CITY },
        expiresAt = expiresAt.trim().ifEmpty { null },
        reason = reason.trim(),
    )
    val inputError: String? = if (state.session == null) {
        "The operations session is unavailable."
    } else {
        administrativeGrantInputError(request, state.session.userId, Clock.System.now())
    }
    val scopeLabel = selectedScopeLabel(state, role.scopeKind)
    val valid = inputError == null && request.matchesSelectedScope(state.scope) && confirmation.trim() == "GRANT"
    val busy = state.mutationLabel != null

    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text("Request staff access") },
        text = {
            Column(
                Modifier.fillMaxWidth().heightIn(max = 580.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                OutlinedTextField(
                    value = userId,
                    onValueChange = { userId = it.take(36) },
                    label = { Text("Target user UUID") },
                    placeholder = { Text("00000000-0000-4000-8000-000000000000") },
                    singleLine = true,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                ScopeMenu(
                    label = "Role template",
                    selected = role.displayName,
                    options = ADMINISTRATIVE_ROLE_TEMPLATES.map { ScopeOption(it.value, it.displayName) },
                    enabled = !busy,
                    onSelected = { selected -> selected?.let { roleTemplate = it } },
                    modifier = Modifier.fillMaxWidth(),
                )
                Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                    Text("${role.scopeKind.displayName.uppercase()} SCOPE", color = taxiColors.Ink500, style = MaterialTheme.typography.labelSmall)
                    Text(scopeLabel, color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
                }
                OutlinedTextField(
                    value = expiresAt,
                    onValueChange = { expiresAt = it.take(40) },
                    label = { Text("Expires at · optional") },
                    placeholder = { Text("2026-12-31T23:59:59Z") },
                    singleLine = true,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                StaffReasonConfirmationFields(
                    reason = reason,
                    onReasonChange = { reason = it },
                    confirmation = confirmation,
                    onConfirmationChange = { confirmation = it },
                    phrase = "GRANT",
                    reasonLabel = "Audit reason",
                    reasonHint = "3–240 characters; cite the approved access record without entering secrets or personal data.",
                    busy = busy,
                )
                inputError?.let {
                    Text(it, color = taxiColors.Danger600, style = MaterialTheme.typography.bodySmall)
                }
            }
        },
        confirmButton = {
            Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onConfirm(request) }, enabled = !busy && valid) {
                Text(if (busy) "Waiting for backend…" else "Submit request")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}

@Composable
private fun RevokeAdministrativeGrantDialog(
    grant: AdministrativeGrantRecord,
    scopeLabel: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    StaffReviewDialog(
        key = grant.id,
        title = "Request staff revocation",
        phrase = "REVOKE",
        reasonLabel = "Audit reason",
        reasonHint = "3–240 characters; reference the approved offboarding or access-review record.",
        submitLabel = "Submit revocation",
        dismissLabel = "Cancel",
        busy = busy,
        onDismiss = onDismiss,
        onConfirm = onConfirm,
        description = {
            Text(
                "Request revocation of ${grant.roleTemplate.replace('_', ' ')} for ${shortId(grant.userId)} in $scopeLabel. Access remains active until a different administrator approves the request.",
                color = TaxiTheme.colors.Ink700,
            )
        },
    )
}

@Composable
private fun AdministrativeGrantDecisionDialog(
    request: AdministrativeGrantChangeRequestRecord,
    decision: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    val phrase = decision.uppercase()
    StaffReviewDialog(
        key = "${request.id}:$decision",
        title = "${decision.replaceFirstChar { it.uppercase() }} staff request",
        phrase = phrase,
        reasonLabel = "Independent decision reason",
        reasonHint = "3–240 characters; cite reviewed evidence without personal data.",
        submitLabel = phrase,
        dismissLabel = "Back",
        busy = busy,
        onDismiss = onDismiss,
        onConfirm = onConfirm,
        description = {
            Text(
                "Request ${shortId(request.id)} asks to ${request.action.lowercase()} " +
                    "${request.roleTemplate.replace('_', ' ')} for " +
                    "${shortId(request.targetUserId)}. You are deciding version " +
                    "${request.optimisticVersion}; the backend will reject stale state.",
                color = TaxiTheme.colors.Ink700,
            )
            Text(
                "Requester: ${shortId(request.requesterUserId)} · original reason: " + request.reason,
                color = TaxiTheme.colors.Ink500,
                style = MaterialTheme.typography.bodySmall,
            )
        },
    )
}

@Composable
private fun StaffReviewDialog(
    key: String,
    title: String,
    phrase: String,
    reasonLabel: String,
    reasonHint: String,
    submitLabel: String,
    dismissLabel: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
    description: @Composable () -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    var reason by remember(key) { mutableStateOf("") }
    var confirmation by remember(key) { mutableStateOf("") }
    val valid = reason.trim().length in 3..240 && confirmation.trim() == phrase
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                description()
                StaffReasonConfirmationFields(
                    reason = reason,
                    onReasonChange = { reason = it },
                    confirmation = confirmation,
                    onConfirmationChange = { confirmation = it },
                    phrase = phrase,
                    reasonLabel = reasonLabel,
                    reasonHint = reasonHint,
                    busy = busy,
                )
            }
        },
        confirmButton = {
            Button(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                onClick = { onConfirm(reason.trim()) },
                enabled = !busy && valid,
            ) {
                Text(if (busy) "Waiting for backend…" else submitLabel)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !busy) { Text(dismissLabel) }
        },
    )
}

@Composable
private fun StaffReasonConfirmationFields(
    reason: String,
    onReasonChange: (String) -> Unit,
    confirmation: String,
    onConfirmationChange: (String) -> Unit,
    phrase: String,
    reasonLabel: String,
    reasonHint: String,
    busy: Boolean,
) {
    OutlinedTextField(
        value = reason,
        onValueChange = { onReasonChange(it.take(240)) },
        label = { Text(reasonLabel) },
        supportingText = { Text(reasonHint) },
        minLines = 2,
        enabled = !busy,
        modifier = Modifier.fillMaxWidth(),
    )
    OutlinedTextField(
        value = confirmation,
        onValueChange = { onConfirmationChange(it.uppercase().take(phrase.length)) },
        label = { Text("Type $phrase to confirm") },
        singleLine = true,
        enabled = !busy,
        modifier = Modifier.fillMaxWidth(),
    )
}

private fun staffScopeLabel(
    cityId: String?,
    operatorId: String?,
    marketId: String?,
    marketNames: Map<String, String>,
    operatorNames: Map<String, String>,
    cityNames: Map<String, String>,
): String = when {
    cityId != null -> "City · ${cityNames[cityId] ?: shortId(cityId)}"
    operatorId != null -> "Operator · ${operatorNames[operatorId] ?: shortId(operatorId)}"
    marketId != null -> "Market · ${marketNames[marketId] ?: shortId(marketId)}"
    else -> "Invalid scope"
}

private fun scopeLabelForGrant(
    grant: AdministrativeGrantRecord,
    marketNames: Map<String, String>,
    operatorNames: Map<String, String>,
    cityNames: Map<String, String>,
): String = staffScopeLabel(grant.cityId, grant.operatorId, grant.marketId, marketNames, operatorNames, cityNames)

private fun scopeLabelForRequest(
    request: AdministrativeGrantChangeRequestRecord,
    marketNames: Map<String, String>,
    operatorNames: Map<String, String>,
    cityNames: Map<String, String>,
): String = staffScopeLabel(request.cityId, request.operatorId, request.marketId, marketNames, operatorNames, cityNames)

private fun selectedScopeLabel(state: OperationsUiState, kind: AdministrativeGrantScopeKind): String {
    val snapshot = state.snapshot
    return when (kind) {
        AdministrativeGrantScopeKind.MARKET -> state.scope.marketId?.let { id ->
            "Market · ${snapshot?.markets?.items?.firstOrNull { it.id == id }?.name ?: shortId(id)}"
        } ?: "No market selected"
        AdministrativeGrantScopeKind.OPERATOR -> state.scope.operatorId?.let { id ->
            "Operator · ${snapshot?.operators?.items?.firstOrNull { it.id == id }?.name ?: shortId(id)}"
        } ?: "No operator selected"
        AdministrativeGrantScopeKind.CITY -> state.scope.cityId?.let { id ->
            "City · ${snapshot?.cities?.items?.firstOrNull { it.id == id }?.localizedName?.preferred() ?: shortId(id)}"
        } ?: "No city selected"
    }
}
