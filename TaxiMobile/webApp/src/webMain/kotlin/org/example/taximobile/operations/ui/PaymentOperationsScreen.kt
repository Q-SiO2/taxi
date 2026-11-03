package org.example.taximobile.operations.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
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
import org.example.taximobile.operations.model.MANAGE_PAYMENT_CAPABILITIES
import org.example.taximobile.operations.model.ManualTransferReconciliationRecord
import org.example.taximobile.operations.model.PaymentCapabilityCreateRequest
import org.example.taximobile.operations.model.PaymentCapabilityRecord
import org.example.taximobile.operations.model.PaymentRecipientCreateRequest
import org.example.taximobile.operations.model.PaymentRecipientRecord
import org.example.taximobile.operations.model.PaymentRefundCreateRequest
import org.example.taximobile.operations.model.RECONCILE_PAYMENTS
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

@Composable
fun PaymentOperationsScreen(state: OperationsUiState, coordinator: OperationsCoordinator) {
    val taxiColors = TaxiTheme.colors
    val snapshot = state.snapshot?.paymentOperations
    val canConfigure = state.session?.hasPermission(MANAGE_PAYMENT_CAPABILITIES) == true
    val canReconcile = state.session?.hasPermission(RECONCILE_PAYMENTS) == true
    val exactScope = state.scope.cityId != null && state.scope.operatorId != null
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        Text(stringResource(Res.string.web_pay_title), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            stringResource(Res.string.web_pay_help),
            color = taxiColors.Ink500,
        )
        if (canConfigure) {
            if (!exactScope) {
                EmptyState(
                    title = stringResource(Res.string.web_pay_scope_title),
                    detail = stringResource(Res.string.web_pay_scope_help),
                )
            } else {
                RecipientCreator(state, coordinator)
                RecipientList(snapshot?.recipients?.items.orEmpty(), state, coordinator)
                CapabilityCreator(state, snapshot?.recipients?.items.orEmpty(), coordinator)
                CapabilityList(snapshot?.capabilities?.items.orEmpty(), state, coordinator)
            }
        }
        if (canReconcile) {
            TransferQueue(snapshot?.manualTransfers?.items.orEmpty(), state, coordinator)
            RefundRecorder(state, coordinator)
            RefundHistory(snapshot?.refunds?.items.orEmpty())
        }
    }
}

@Composable
private fun RecipientCreator(state: OperationsUiState, coordinator: OperationsCoordinator) {
    var label by remember { mutableStateOf("") }
    var recipientName by remember { mutableStateOf("") }
    var bankAccount by remember { mutableStateOf("") }
    var walletId by remember { mutableStateOf("") }
    OperationsPanel(stringResource(Res.string.web_pay_recipient_new), stringResource(Res.string.web_pay_recipient_new_help)) {
        Field(label, { label = it }, stringResource(Res.string.web_pay_internal_label), state)
        Field(recipientName, { recipientName = it }, stringResource(Res.string.web_pay_recipient_name), state)
        Field(bankAccount, { bankAccount = it }, stringResource(Res.string.web_pay_bank_optional), state)
        Field(walletId, { walletId = it }, stringResource(Res.string.web_pay_wallet_optional), state)
        Button(
            shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
            onClick = {
                coordinator.createPaymentRecipient(
                    PaymentRecipientCreateRequest(
                        operatorId = state.scope.operatorId.orEmpty(),
                        label = label.trim(),
                        recipientName = recipientName.trim(),
                        bankAccount = bankAccount.trim().ifBlank { null },
                        walletId = walletId.trim().ifBlank { null },
                    )
                )
            },
            enabled = !state.interactionLocked && label.length >= 2 && recipientName.length >= 2 &&
                (bankAccount.length >= 3 || walletId.length >= 3),
        ) { Text(stringResource(Res.string.web_pay_recipient_create)) }
    }
}

@Composable
private fun RecipientList(
    recipients: List<PaymentRecipientRecord>,
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val taxiColors = TaxiTheme.colors
    var reason by remember { mutableStateOf("") }
    OperationsPanel(stringResource(Res.string.web_pay_recipients), stringResource(Res.string.web_pay_recipients_help)) {
        Field(reason, { reason = it }, stringResource(Res.string.web_pay_recipient_reason), state)
        if (recipients.isEmpty()) Text(stringResource(Res.string.web_pay_recipients_empty), color = taxiColors.Ink500)
        recipients.forEach { recipient ->
            RecordSurface {
                Text(recipient.label, style = recruitmentTextStyle(recipient.label), fontWeight = FontWeight.Bold)
                Text(
                    "${recipient.recipientName} · ${paymentLabel(recipient.status)}",
                    style = recruitmentTextStyle(recipient.recipientName), color = taxiColors.Ink500,
                )
                Text(
                    listOfNotNull(recipient.bankAccount, recipient.walletId).joinToString(" · ") { ltrIsolate(it) },
                    style = MaterialTheme.typography.bodySmall,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    if (recipient.status == "DRAFT") {
                        Button(
                            shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                            onClick = { coordinator.transitionPaymentRecipient(recipient, "verify", reason) },
                            enabled = !state.interactionLocked && reason.trim().length >= 3,
                        ) { Text(stringResource(Res.string.web_pay_verify)) }
                    }
                    if (recipient.status == "VERIFIED") {
                        OutlinedButton(
                            shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                            onClick = { coordinator.transitionPaymentRecipient(recipient, "retire", reason) },
                            enabled = !state.interactionLocked && reason.trim().length >= 3,
                        ) { Text(stringResource(Res.string.web_pay_retire)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun CapabilityCreator(
    state: OperationsUiState,
    recipients: List<PaymentRecipientRecord>,
    coordinator: OperationsCoordinator,
) {
    val taxiColors = TaxiTheme.colors
    var version by remember { mutableStateOf("") }
    var serviceType by remember { mutableStateOf("ON_DEMAND") }
    var effectiveFrom by remember { mutableStateOf("") }
    var manualTransfer by remember { mutableStateOf(false) }
    var recipientId by remember { mutableStateOf<String?>(null) }
    val verified = recipients.filter { it.status == "VERIFIED" }
    OperationsPanel(stringResource(Res.string.web_pay_capability_new), stringResource(Res.string.web_pay_capability_help)) {
        Field(version, { version = it }, stringResource(Res.string.web_pay_version), state)
        Field(effectiveFrom, { effectiveFrom = it }, stringResource(Res.string.web_pay_effective_input), state)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            listOf("ON_DEMAND", "FIXED_ROUTE").forEach { value ->
                FilterChip(selected = serviceType == value, onClick = { serviceType = value }, label = { Text(recruitmentLabel(value)) })
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Switch(checked = manualTransfer, onCheckedChange = { manualTransfer = it; if (!it) recipientId = null })
            Text(stringResource(Res.string.web_pay_enable_transfer), modifier = Modifier.padding(top = 12.dp))
        }
        if (manualTransfer) {
            Text(stringResource(Res.string.web_pay_verified_recipient), style = MaterialTheme.typography.labelMedium)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                verified.forEach { recipient ->
                    FilterChip(
                        selected = recipientId == recipient.id,
                        onClick = { recipientId = recipient.id },
                        label = { Text(recipient.label, style = recruitmentTextStyle(recipient.label)) },
                    )
                }
            }
            if (verified.isEmpty()) Text(stringResource(Res.string.web_pay_verify_first), color = taxiColors.Warning600)
        }
        Button(
            shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
            onClick = {
                coordinator.createPaymentCapability(
                    PaymentCapabilityCreateRequest(
                        operatorId = state.scope.operatorId.orEmpty(),
                        serviceType = serviceType,
                        version = version.trim(),
                        manualTransferEnabled = manualTransfer,
                        recipientAccountId = recipientId,
                        effectiveFrom = effectiveFrom.trim(),
                    )
                )
            },
            enabled = !state.interactionLocked && version.isNotBlank() && effectiveFrom.isNotBlank() &&
                (!manualTransfer || recipientId != null),
        ) { Text(stringResource(Res.string.web_pay_capability_create)) }
    }
}

@Composable
private fun CapabilityList(
    capabilities: List<PaymentCapabilityRecord>,
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val taxiColors = TaxiTheme.colors
    var reason by remember { mutableStateOf("") }
    OperationsPanel(stringResource(Res.string.web_pay_versions), stringResource(Res.string.web_pay_versions_help)) {
        Field(reason, { reason = it }, stringResource(Res.string.web_pay_lifecycle_reason), state)
        if (capabilities.isEmpty()) Text(stringResource(Res.string.web_pay_versions_empty), color = taxiColors.Ink500)
        capabilities.forEach { capability ->
            CapabilityRow(capability, state, reason, coordinator)
        }
    }
}

@Composable
private fun CapabilityRow(
    capability: PaymentCapabilityRecord,
    state: OperationsUiState,
    reason: String,
    coordinator: OperationsCoordinator,
) {
    val taxiColors = TaxiTheme.colors
    val next = when (capability.status) {
        "DRAFT" -> "submit"
        "IN_REVIEW" -> "approve"
        "APPROVED" -> "activate"
        else -> null
    }
    RecordSurface {
        Text("${ltrIsolate(capability.version)} · ${recruitmentLabel(capability.serviceType)}", fontWeight = FontWeight.Bold)
        Text(
            "${paymentLabel(capability.status)} · ${stringResource(if (capability.manualTransferEnabled) Res.string.web_pay_cash_transfer else Res.string.payment_method_cash)}",
            color = taxiColors.Ink500,
        )
        Text(stringResource(Res.string.web_pay_effective_value, ltrIsolate(compactTimestamp(capability.effectiveFrom))), style = MaterialTheme.typography.bodySmall)
        next?.let {
            Button(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                onClick = { coordinator.transitionPaymentCapability(capability, it, reason) },
                enabled = !state.interactionLocked && reason.trim().length >= 3,
            ) { Text(paymentLabel(it)) }
        }
    }
}

@Composable
private fun TransferQueue(
    transfers: List<ManualTransferReconciliationRecord>,
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val taxiColors = TaxiTheme.colors
    var settlementReference by remember { mutableStateOf("") }
    var rejectionReason by remember { mutableStateOf("") }
    OperationsPanel(stringResource(Res.string.web_pay_transfers), stringResource(Res.string.web_pay_transfers_help)) {
        Field(settlementReference, { settlementReference = it }, stringResource(Res.string.web_pay_settlement_reference), state)
        Field(rejectionReason, { rejectionReason = it }, stringResource(Res.string.web_pay_rejection_reason), state)
        if (transfers.isEmpty()) Text(stringResource(Res.string.web_pay_transfers_empty), color = taxiColors.Ink500)
        transfers.forEach { transfer ->
            RecordSurface {
                Text("${ltrIsolate("${transfer.amount} ${transfer.currency}")} · ${ltrIsolate(transfer.paymentReference)}", fontWeight = FontWeight.Bold)
                val recipientLabel = transfer.recipientLabel ?: stringResource(Res.string.web_pay_legacy_recipient)
                Text(stringResource(Res.string.web_pay_recipient_value, recipientLabel), style = recruitmentTextStyle(recipientLabel), color = taxiColors.Ink500)
                Text(stringResource(Res.string.web_pay_payer_reference, transfer.payerReference?.let(::ltrIsolate) ?: "—"), style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Button(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = { coordinator.verifyManualTransfer(transfer.paymentId, settlementReference) },
                        enabled = !state.interactionLocked && settlementReference.trim().length >= 3,
                    ) { Text(stringResource(Res.string.web_pay_verify_statement)) }
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = { coordinator.rejectManualTransfer(transfer.paymentId, rejectionReason) },
                        enabled = !state.interactionLocked && rejectionReason.trim().length >= 3,
                    ) { Text(stringResource(Res.string.web_pay_reject_claim)) }
                }
            }
        }
    }
}

@Composable
private fun RefundRecorder(state: OperationsUiState, coordinator: OperationsCoordinator) {
    var paymentId by remember { mutableStateOf("") }
    var amount by remember { mutableStateOf("") }
    var reason by remember { mutableStateOf("SERVICE_RECOVERY") }
    var method by remember { mutableStateOf("EXTERNAL_TRANSFER") }
    var reference by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    OperationsPanel(stringResource(Res.string.web_pay_refund_new), stringResource(Res.string.web_pay_refund_help)) {
        Field(paymentId, { paymentId = it }, stringResource(Res.string.web_pay_payment_id), state)
        Field(amount, { amount = it }, stringResource(Res.string.web_pay_returned_amount), state)
        Field(reason, { reason = it.uppercase() }, stringResource(Res.string.web_pay_reason_code), state)
        Field(method, { method = it.uppercase() }, stringResource(Res.string.web_pay_settlement_method), state)
        Field(reference, { reference = it }, stringResource(Res.string.web_pay_refund_reference), state)
        Field(note, { note = it }, stringResource(Res.string.web_pay_restricted_note), state)
        Button(
            shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
            onClick = {
                coordinator.recordPaymentRefund(
                    paymentId.trim(),
                    PaymentRefundCreateRequest(amount.trim(), reason.trim(), method.trim(), reference.trim(), note.trim()),
                )
            },
            enabled = !state.interactionLocked && paymentId.isNotBlank() && amount.isNotBlank() &&
                reference.trim().length >= 3 && note.trim().length >= 3,
        ) { Text(stringResource(Res.string.web_pay_record_returned)) }
    }
}

@Composable
private fun RefundHistory(refunds: List<org.example.taximobile.operations.model.PaymentRefundRecord>) {
    val taxiColors = TaxiTheme.colors
    OperationsPanel(stringResource(Res.string.web_pay_refund_history), stringResource(Res.string.web_pay_refund_history_help)) {
        if (refunds.isEmpty()) Text(stringResource(Res.string.web_pay_refunds_empty), color = taxiColors.Ink500)
        refunds.forEach { refund ->
            RecordSurface {
                Text("${ltrIsolate("${refund.amount} ${refund.currency}")} · ${ltrIsolate(refund.reason)}", fontWeight = FontWeight.Bold)
                Text("${stringResource(Res.string.web_pay_payment_id)}: ${ltrIsolate(refund.paymentId)} · ${paymentLabel(refund.settlementMethod)}", color = taxiColors.Ink500)
                Text(stringResource(Res.string.web_pay_remaining_value, ltrIsolate("${refund.remainingRefundableAmount} ${refund.currency}")), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun OperationsPanel(title: String, detail: String, content: @Composable ColumnScope.() -> Unit) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = taxiColors.Surface0,
        shape = RoundedCornerShape(taxiRadii.Lg),
        border = BorderStroke(1.dp, taxiColors.StrokeSubtle),
    ) {
        Column(Modifier.padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(detail, color = taxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
            content()
        }
    }
}

@Composable
private fun RecordSurface(content: @Composable ColumnScope.() -> Unit) {
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = taxiColors.Surface1,
        shape = RoundedCornerShape(taxiRadii.Md),
    ) {
        Column(Modifier.padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) { content() }
    }
}

@Composable
private fun Field(value: String, onValue: (String) -> Unit, label: String, state: OperationsUiState) {
    OutlinedTextField(
        value = value,
        onValueChange = { if (it.length <= 500) onValue(it) },
        label = { Text(label) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        enabled = !state.interactionLocked,
        textStyle = recruitmentTextStyle(value),
    )
}
