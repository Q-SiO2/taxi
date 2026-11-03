package org.example.taximobile.operations.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.ACCOUNT_SECURITY_REASON_CODES
import org.example.taximobile.operations.model.AccountSecurityAction
import org.example.taximobile.operations.model.AccountSecurityInputIssue
import org.example.taximobile.operations.model.accountSecurityInputIssue
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState
import org.jetbrains.compose.resources.StringResource
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

private fun AccountSecurityAction.titleResource(): StringResource = when (this) {
    AccountSecurityAction.REVOKE_SESSIONS -> Res.string.web_account_revoke_sessions
    AccountSecurityAction.SUSPEND -> Res.string.web_account_suspend
    AccountSecurityAction.REACTIVATE -> Res.string.web_account_reactivate
}

private fun accountReasonResource(code: String): StringResource = when (code) {
    "ACCOUNT_COMPROMISE" -> Res.string.web_account_reason_compromise
    "VERIFIED_USER_REQUEST" -> Res.string.web_account_reason_request
    "SAFETY_CONTAINMENT" -> Res.string.web_account_reason_safety
    "LEGAL_REQUIREMENT" -> Res.string.web_account_reason_legal
    "SECURITY_INCIDENT" -> Res.string.web_account_reason_incident
    else -> Res.string.web_account_reason
}

private fun AccountSecurityInputIssue.messageResource(): StringResource = when (this) {
    AccountSecurityInputIssue.MARKET -> Res.string.web_account_error_market
    AccountSecurityInputIssue.TARGET -> Res.string.web_account_error_target
    AccountSecurityInputIssue.REASON -> Res.string.web_account_error_reason
    AccountSecurityInputIssue.CASE_REFERENCE -> Res.string.web_account_error_case
    AccountSecurityInputIssue.CONFIRMATION -> Res.string.web_account_error_confirmation
}

@Composable
internal fun AccountSecurityScreen(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    var targetUserId by remember { mutableStateOf("") }
    var action by remember { mutableStateOf(AccountSecurityAction.REVOKE_SESSIONS) }
    var reasonCode by remember { mutableStateOf("ACCOUNT_COMPROMISE") }
    var caseReference by remember { mutableStateOf("") }
    var confirmation by remember(action) { mutableStateOf("") }
    val selectedMarket = state.snapshot?.markets?.items?.firstOrNull { it.id == state.scope.marketId }
    val inputError = accountSecurityInputIssue(
        marketId = state.scope.marketId,
        targetUserId = targetUserId,
        action = action,
        reasonCode = reasonCode,
        caseReference = caseReference,
        confirmation = confirmation,
    )

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        Text(stringResource(Res.string.web_account_title), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            stringResource(Res.string.web_account_scope_help),
            color = taxiColors.Ink500,
        )
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = taxiColors.Warning100,
            shape = RoundedCornerShape(taxiRadii.Md),
            border = BorderStroke(1.dp, taxiColors.Warning600),
        ) {
            Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Text(stringResource(Res.string.web_account_market), fontWeight = FontWeight.Bold, color = taxiColors.Navy900)
                Text(
                    selectedMarket?.let { "${it.name} (${ltrIsolate(it.code)})" }
                        ?: stringResource(Res.string.web_account_choose_market),
                    color = taxiColors.Ink500,
                )
                Text(
                    stringResource(Res.string.web_account_market_warning),
                    style = MaterialTheme.typography.bodySmall,
                    color = taxiColors.Ink500,
                )
            }
        }
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = taxiColors.Surface0,
            shape = RoundedCornerShape(taxiRadii.Lg),
            border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
        ) {
            Column(Modifier.padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                OutlinedTextField(
                    value = targetUserId,
                    onValueChange = { if (it.length <= 36) targetUserId = it },
                    label = { Text(stringResource(Res.string.web_account_target)) },
                    supportingText = { Text(stringResource(Res.string.web_account_target_help)) },
                    modifier = Modifier.fillMaxWidth(),
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                    singleLine = true,
                    enabled = !state.interactionLocked,
                )
                Text(stringResource(Res.string.web_account_action), style = MaterialTheme.typography.labelLarge)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    AccountSecurityAction.entries.forEach { candidate ->
                        FilterChip(
                            selected = action == candidate,
                            onClick = { action = candidate },
                            label = { Text(stringResource(candidate.titleResource())) },
                            enabled = !state.interactionLocked,
                        )
                    }
                }
                Text(stringResource(Res.string.web_account_reason), style = MaterialTheme.typography.labelLarge)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    ACCOUNT_SECURITY_REASON_CODES.forEach { candidate ->
                        FilterChip(
                            selected = reasonCode == candidate,
                            onClick = { reasonCode = candidate },
                            label = { Text(stringResource(accountReasonResource(candidate))) },
                            enabled = !state.interactionLocked,
                        )
                    }
                }
                OutlinedTextField(
                    value = caseReference,
                    onValueChange = { if (it.length <= 72) caseReference = it.uppercase() },
                    label = { Text(stringResource(Res.string.web_account_case_reference)) },
                    modifier = Modifier.fillMaxWidth(),
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                    singleLine = true,
                    enabled = !state.interactionLocked,
                )
                OutlinedTextField(
                    value = confirmation,
                    onValueChange = { if (it.length <= 10) confirmation = it.uppercase() },
                    label = { Text(stringResource(Res.string.web_account_confirm, ltrIsolate(action.confirmationPhrase))) },
                    supportingText = { Text(stringResource(Res.string.web_account_no_replay)) },
                    modifier = Modifier.fillMaxWidth(),
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr),
                    singleLine = true,
                    enabled = !state.interactionLocked,
                )
                inputError?.let {
                    Text(
                        if (it == AccountSecurityInputIssue.CONFIRMATION) stringResource(it.messageResource(), ltrIsolate(action.confirmationPhrase))
                        else stringResource(it.messageResource()),
                        color = taxiColors.Warning600,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                Button(
                    shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                    onClick = {
                        val submittedConfirmation = confirmation
                        confirmation = ""
                        coordinator.applyAccountSecurityAction(
                            targetUserId = targetUserId,
                            action = action,
                            reasonCode = reasonCode,
                            caseReference = caseReference,
                            confirmation = submittedConfirmation,
                        )
                    },
                    enabled = !state.interactionLocked && inputError == null,
                ) { Text(stringResource(action.titleResource())) }
            }
        }
    }
}
