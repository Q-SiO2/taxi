package org.example.taximobile.operations.ui

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
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.ACCOUNT_SECURITY_REASON_CODES
import org.example.taximobile.operations.model.AccountSecurityAction
import org.example.taximobile.operations.model.accountSecurityInputError
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState

@Composable
internal fun AccountSecurityScreen(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    var targetUserId by remember { mutableStateOf("") }
    var action by remember { mutableStateOf(AccountSecurityAction.REVOKE_SESSIONS) }
    var reasonCode by remember { mutableStateOf("ACCOUNT_COMPROMISE") }
    var caseReference by remember { mutableStateOf("") }
    var confirmation by remember(action) { mutableStateOf("") }
    val selectedMarket = state.snapshot?.markets?.items?.firstOrNull { it.id == state.scope.marketId }
    val inputError = accountSecurityInputError(
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
        Text("Account containment", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            "Use only from a verified support, safety, security, or legal case. The backend treats this as an account-wide action and refuses it unless your permission covers every market associated with the target.",
            color = TaxiColors.Ink500,
        )
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = TaxiColors.Warning100,
            shape = RoundedCornerShape(TaxiRadii.Md),
            border = BorderStroke(1.dp, TaxiColors.Warning600),
        ) {
            Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Text("Selected association market", fontWeight = FontWeight.Bold, color = TaxiColors.Navy900)
                Text(
                    selectedMarket?.let { "${it.name} (${it.code})" }
                        ?: "Select an authorized market before entering a command.",
                    color = TaxiColors.Ink500,
                )
                Text(
                    "This selection does not reduce the command to one city. Partial cross-market authority fails closed.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TaxiColors.Ink500,
                )
            }
        }
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = TaxiColors.Surface0,
            shape = RoundedCornerShape(TaxiRadii.Lg),
            border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
        ) {
            Column(Modifier.padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                OutlinedTextField(
                    value = targetUserId,
                    onValueChange = { if (it.length <= 36) targetUserId = it },
                    label = { Text("Exact target user UUID") },
                    supportingText = { Text("Copy from the authorized case record; there is no broad account search here.") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = !state.interactionLocked,
                )
                Text("Action", style = MaterialTheme.typography.labelLarge)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    AccountSecurityAction.entries.forEach { candidate ->
                        FilterChip(
                            selected = action == candidate,
                            onClick = { action = candidate },
                            label = { Text(candidate.label) },
                            enabled = !state.interactionLocked,
                        )
                    }
                }
                Text("Controlled reason", style = MaterialTheme.typography.labelLarge)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    ACCOUNT_SECURITY_REASON_CODES.forEach { candidate ->
                        FilterChip(
                            selected = reasonCode == candidate,
                            onClick = { reasonCode = candidate },
                            label = { Text(candidate.replace('_', ' ')) },
                            enabled = !state.interactionLocked,
                        )
                    }
                }
                OutlinedTextField(
                    value = caseReference,
                    onValueChange = { if (it.length <= 72) caseReference = it.uppercase() },
                    label = { Text("SUP-, SAF-, or SEC- case reference") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = !state.interactionLocked,
                )
                OutlinedTextField(
                    value = confirmation,
                    onValueChange = { if (it.length <= 10) confirmation = it.uppercase() },
                    label = { Text("Type ${action.confirmationPhrase} to confirm") },
                    supportingText = { Text("The command is not automatically replayed after MFA step-up or an error.") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = !state.interactionLocked,
                )
                inputError?.let {
                    Text(it, color = TaxiColors.Warning600, style = MaterialTheme.typography.bodySmall)
                }
                Button(
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
                ) { Text(action.label) }
            }
        }
    }
}
