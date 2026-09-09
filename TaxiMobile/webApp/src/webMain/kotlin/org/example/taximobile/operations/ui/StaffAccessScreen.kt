package org.example.taximobile.operations.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import org.example.taximobile.operations.model.MANAGE_SCOPED_STAFF_GRANTS
import org.example.taximobile.operations.model.administrativeGrantInputError
import org.example.taximobile.operations.model.administrativeRoleTemplate
import org.example.taximobile.operations.model.matchesSelectedScope
import org.example.taximobile.operations.state.OperationsUiState

@Composable
internal fun StaffAccessScreen(
    state: OperationsUiState,
    onCreateGrant: (AdministrativeGrantCreateRequest) -> Unit,
    onRevokeGrant: (AdministrativeGrantRecord, String) -> Unit,
    onDecideRequest: (AdministrativeGrantChangeRequestRecord, String, String) -> Unit,
) {
    val snapshot = state.snapshot ?: return
    val grants = snapshot.grants
    val mayManage = state.session?.hasPermission(MANAGE_SCOPED_STAFF_GRANTS) == true
    var showCreateDialog by remember { mutableStateOf(false) }
    var pendingRevocation by remember { mutableStateOf<AdministrativeGrantRecord?>(null) }
    var pendingDecision by remember {
        mutableStateOf<Pair<AdministrativeGrantChangeRequestRecord, String>?>(null)
    }
    val cityNames = snapshot.cities.items.associate { it.id to it.localizedName.preferred() }
    val operatorNames = snapshot.operators.items.associate { it.id to it.name }
    val marketNames = snapshot.markets.items.associate { it.id to it.name }
    val operatorMarkets = snapshot.operators.items.associate { it.id to it.marketId }
    val cityMarkets = snapshot.cities.items.associate { it.id to it.marketId }

    ScreenColumn {
        SectionHeading(
            title = "Scoped staff access",
            supportingText = "Request, independently approve, and audit scoped authority.",
            action = {
                Button(
                    onClick = { showCreateDialog = true },
                    enabled = mayManage && grants != null && state.scope.marketId != null && !state.interactionLocked,
                ) {
                    Text("Request access")
                }
            },
        )
        Text(
            "Every change requires recent operations MFA and a durable maker-checker request. The requester, target, and approving administrator must be distinct; a revocation does not take effect while it is pending.",
            color = TaxiColors.Ink700,
            style = MaterialTheme.typography.bodySmall,
        )
        when {
            grants == null -> EmptyState(
                "Grant management not authorized",
                "This destination is available only to a market-scoped platform administrator.",
            )
            grants.items.isEmpty() -> EmptyState(
                "No active grants",
                "No active administrative grants were returned for this authorized market. Submit a request from an approved staff record.",
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
                            val isSelectedMarket = grantBelongsToMarket(
                                grant = grant,
                                marketId = state.scope.marketId,
                                operatorMarkets = operatorMarkets,
                                cityMarkets = cityMarkets,
                            )
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
                PageLimitNote(grants.items.size, grants.total)
            }
        }
        val requests = snapshot.grantRequests
        SectionHeading(
            title = "Grant change queue",
            supportingText = "Pending requests require a different authorized administrator.",
        )
        when {
            requests == null -> EmptyState(
                "Request queue not authorized",
                "The active operations grant does not expose staff-change requests.",
            )
            requests.items.none { it.status == "PENDING" } -> EmptyState(
                "No pending staff changes",
                "Submitted, approved, rejected, and cancelled records remain available after refresh.",
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
                        requests.items.filter { it.status == "PENDING" }.forEach { request ->
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
                                            onClick = { pendingDecision = request to "cancel" },
                                            enabled = !state.interactionLocked,
                                        ) { Text("Cancel request") }
                                        isTarget -> Text(
                                            "Target cannot decide",
                                            color = TaxiColors.Ink500,
                                            style = MaterialTheme.typography.bodySmall,
                                        )
                                        else -> Row(
                                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
                                        ) {
                                            Button(
                                                onClick = { pendingDecision = request to "approve" },
                                                enabled = !state.interactionLocked,
                                            ) { Text("Approve") }
                                            OutlinedButton(
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
                PageLimitNote(requests.items.size, requests.total)
            }
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
private fun CreateAdministrativeGrantDialog(
    state: OperationsUiState,
    onDismiss: () -> Unit,
    onConfirm: (AdministrativeGrantCreateRequest) -> Unit,
) {
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
                Text(
                    "Use the exact UUID of an existing active user. The backend records a pending snapshot and rechecks the user, scope, permission, duplicate state, and MFA again at approval.",
                    color = TaxiColors.Ink700,
                    style = MaterialTheme.typography.bodyMedium,
                )
                OutlinedTextField(
                    value = userId,
                    onValueChange = { userId = it.take(36) },
                    label = { Text("Target user UUID") },
                    placeholder = { Text("00000000-0000-4000-8000-000000000000") },
                    supportingText = { Text("Copy from the approved staff onboarding record; names and email are intentionally not accepted here.") },
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
                    Text("${role.scopeKind.displayName.uppercase()} SCOPE", color = TaxiColors.Ink500, style = MaterialTheme.typography.labelSmall)
                    Text(scopeLabel, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
                    Text(
                        "Change the scope selectors in the page header before opening this review if this is not the intended authority boundary.",
                        color = TaxiColors.Ink500,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                OutlinedTextField(
                    value = expiresAt,
                    onValueChange = { expiresAt = it.take(40) },
                    label = { Text("Expires at · optional") },
                    placeholder = { Text("2026-12-31T23:59:59Z") },
                    supportingText = { Text("Prefer bounded access. Blank grants require manual recertification and later revocation.") },
                    singleLine = true,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = { reason = it.take(240) },
                    label = { Text("Audit reason") },
                    supportingText = { Text("3–240 characters; cite the approved access record without entering secrets or personal data.") },
                    minLines = 2,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    "Review: ${role.displayName} for ${userId.ifBlank { "target user" }} in $scopeLabel.",
                    color = TaxiColors.Navy900,
                    fontWeight = FontWeight.Bold,
                )
                OutlinedTextField(
                    value = confirmation,
                    onValueChange = { confirmation = it.uppercase().take(5) },
                    label = { Text("Type GRANT to confirm") },
                    singleLine = true,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                inputError?.let {
                    Text(it, color = TaxiColors.Danger600, style = MaterialTheme.typography.bodySmall)
                }
                Text(
                    "No authority changes now. A different platform administrator must review and approve this request. A failed command is not automatically replayed after MFA step-up.",
                    color = TaxiColors.Ink700,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        },
        confirmButton = {
            Button(onClick = { onConfirm(request) }, enabled = !busy && valid) {
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
    var reason by remember(grant.id) { mutableStateOf("") }
    var confirmation by remember(grant.id) { mutableStateOf("") }
    val valid = reason.trim().length in 3..240 && confirmation.trim() == "REVOKE"
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text("Request staff revocation") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(
                    "Request revocation of ${grant.roleTemplate.replace('_', ' ')} for ${shortId(grant.userId)} in $scopeLabel. Access remains active until a different administrator approves the request.",
                    color = TaxiColors.Ink700,
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = { reason = it.take(240) },
                    label = { Text("Audit reason") },
                    supportingText = { Text("3–240 characters; reference the approved offboarding or access-review record.") },
                    minLines = 2,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = confirmation,
                    onValueChange = { confirmation = it.uppercase().take(6) },
                    label = { Text("Type REVOKE to confirm") },
                    singleLine = true,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            Button(onClick = { onConfirm(reason.trim()) }, enabled = !busy && valid) {
                Text(if (busy) "Waiting for backend…" else "Submit revocation")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
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
    var reason by remember(request.id, decision) { mutableStateOf("") }
    var confirmation by remember(request.id, decision) { mutableStateOf("") }
    val phrase = decision.uppercase()
    val valid = reason.trim().length in 3..240 && confirmation.trim() == phrase
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text("${decision.replaceFirstChar { it.uppercase() }} staff request") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(
                    "Request ${shortId(request.id)} asks to ${request.action.lowercase()} " +
                        "${request.roleTemplate.replace('_', ' ')} for " +
                        "${shortId(request.targetUserId)}. You are deciding version " +
                        "${request.optimisticVersion}; the backend will reject stale state.",
                    color = TaxiColors.Ink700,
                )
                Text(
                    "Requester: ${shortId(request.requesterUserId)} · original reason: " +
                        request.reason,
                    color = TaxiColors.Ink500,
                    style = MaterialTheme.typography.bodySmall,
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = { reason = it.take(240) },
                    label = { Text("Independent decision reason") },
                    supportingText = {
                        Text("3–240 characters; cite reviewed evidence without personal data.")
                    },
                    minLines = 2,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = confirmation,
                    onValueChange = { confirmation = it.uppercase().take(phrase.length) },
                    label = { Text("Type $phrase to confirm") },
                    singleLine = true,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
                Text(
                    "Approval revalidates current account, scope, live authority, duplicates, " +
                        "expiry, and platform-admin continuity in one transaction.",
                    color = TaxiColors.Ink500,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onConfirm(reason.trim()) },
                enabled = !busy && valid,
            ) {
                Text(if (busy) "Waiting for backend…" else phrase)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !busy) { Text("Back") }
        },
    )
}

private fun scopeLabelForGrant(
    grant: AdministrativeGrantRecord,
    marketNames: Map<String, String>,
    operatorNames: Map<String, String>,
    cityNames: Map<String, String>,
): String = when {
    grant.cityId != null -> "City · ${cityNames[grant.cityId] ?: shortId(grant.cityId)}"
    grant.operatorId != null -> "Operator · ${operatorNames[grant.operatorId] ?: shortId(grant.operatorId)}"
    grant.marketId != null -> "Market · ${marketNames[grant.marketId] ?: shortId(grant.marketId)}"
    else -> "Invalid scope"
}

private fun scopeLabelForRequest(
    request: AdministrativeGrantChangeRequestRecord,
    marketNames: Map<String, String>,
    operatorNames: Map<String, String>,
    cityNames: Map<String, String>,
): String = when {
    request.cityId != null -> "City · ${cityNames[request.cityId] ?: shortId(request.cityId)}"
    request.operatorId != null ->
        "Operator · ${operatorNames[request.operatorId] ?: shortId(request.operatorId)}"
    request.marketId != null ->
        "Market · ${marketNames[request.marketId] ?: shortId(request.marketId)}"
    else -> "Invalid scope"
}

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

private fun grantBelongsToMarket(
    grant: AdministrativeGrantRecord,
    marketId: String?,
    operatorMarkets: Map<String, String>,
    cityMarkets: Map<String, String>,
): Boolean = when {
    marketId == null -> false
    grant.marketId != null -> grant.marketId == marketId
    grant.operatorId != null -> operatorMarkets[grant.operatorId] == marketId
    grant.cityId != null -> cityMarkets[grant.cityId] == marketId
    else -> false
}
