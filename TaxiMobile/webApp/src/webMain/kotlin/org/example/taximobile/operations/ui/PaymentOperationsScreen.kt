package org.example.taximobile.operations.ui

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

@Composable
fun PaymentOperationsScreen(state: OperationsUiState, coordinator: OperationsCoordinator) {
    val snapshot = state.snapshot?.paymentOperations
    val canConfigure = state.session?.hasPermission(MANAGE_PAYMENT_CAPABILITIES) == true
    val canReconcile = state.session?.hasPermission(RECONCILE_PAYMENTS) == true
    val exactScope = state.scope.cityId != null && state.scope.operatorId != null
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        Text("Payment control", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(
            "Capabilities determine what passengers may select. Claims and refunds remain separate, evidence-backed accounting commands.",
            color = TaxiColors.Ink500,
        )
        if (canConfigure) {
            if (!exactScope) {
                EmptyState(
                    title = "Select one city and operator",
                    detail = "Recipient and capability changes require an exact authorized scope. Queue review may still span your grants.",
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
    OperationsPanel("New transfer recipient", "Draft first; recent MFA is required for verification.") {
        Field(label, { label = it }, "Internal label", state)
        Field(recipientName, { recipientName = it }, "Passenger-visible recipient name", state)
        Field(bankAccount, { bankAccount = it }, "Bank account / RIB (optional)", state)
        Field(walletId, { walletId = it }, "M-Wallet identifier (optional)", state)
        Button(
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
        ) { Text("Create recipient draft") }
    }
}

@Composable
private fun RecipientList(
    recipients: List<PaymentRecipientRecord>,
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    var reason by remember { mutableStateOf("") }
    OperationsPanel("Recipient accounts", "Verified destinations are immutable; replace rather than editing history.") {
        Field(reason, { reason = it }, "Audited verify/retire reason", state)
        if (recipients.isEmpty()) Text("No recipient accounts in this scope.", color = TaxiColors.Ink500)
        recipients.forEach { recipient ->
            RecordSurface {
                Text(recipient.label, fontWeight = FontWeight.Bold)
                Text("${recipient.recipientName} · ${recipient.status}", color = TaxiColors.Ink500)
                Text(
                    listOfNotNull(recipient.bankAccount, recipient.walletId).joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    if (recipient.status == "DRAFT") {
                        Button(
                            onClick = { coordinator.transitionPaymentRecipient(recipient, "verify", reason) },
                            enabled = !state.interactionLocked && reason.trim().length >= 3,
                        ) { Text("Verify") }
                    }
                    if (recipient.status == "VERIFIED") {
                        OutlinedButton(
                            onClick = { coordinator.transitionPaymentRecipient(recipient, "retire", reason) },
                            enabled = !state.interactionLocked && reason.trim().length >= 3,
                        ) { Text("Retire") }
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
    var version by remember { mutableStateOf("") }
    var serviceType by remember { mutableStateOf("ON_DEMAND") }
    var effectiveFrom by remember { mutableStateOf("") }
    var manualTransfer by remember { mutableStateOf(false) }
    var recipientId by remember { mutableStateOf<String?>(null) }
    val verified = recipients.filter { it.status == "VERIFIED" }
    OperationsPanel("New payment capability", "Cash is mandatory. Manual transfer is advertised only with a verified destination.") {
        Field(version, { version = it }, "Version (for example pay-casa-v1)", state)
        Field(effectiveFrom, { effectiveFrom = it }, "Effective from (ISO-8601 with timezone)", state)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            listOf("ON_DEMAND", "FIXED_ROUTE").forEach { value ->
                FilterChip(selected = serviceType == value, onClick = { serviceType = value }, label = { Text(value.replace('_', ' ')) })
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Switch(checked = manualTransfer, onCheckedChange = { manualTransfer = it; if (!it) recipientId = null })
            Text("Enable external bank/M-Wallet transfer", modifier = Modifier.padding(top = 12.dp))
        }
        if (manualTransfer) {
            Text("Verified recipient", style = MaterialTheme.typography.labelMedium)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                verified.forEach { recipient ->
                    FilterChip(
                        selected = recipientId == recipient.id,
                        onClick = { recipientId = recipient.id },
                        label = { Text(recipient.label) },
                    )
                }
            }
            if (verified.isEmpty()) Text("Verify a recipient before creating this capability.", color = TaxiColors.Warning600)
        }
        Button(
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
        ) { Text("Create capability draft") }
    }
}

@Composable
private fun CapabilityList(
    capabilities: List<PaymentCapabilityRecord>,
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    var reason by remember { mutableStateOf("") }
    OperationsPanel("Capability versions", "The active city bundle must reference the exact ACTIVE version.") {
        Field(reason, { reason = it }, "Audited lifecycle reason", state)
        if (capabilities.isEmpty()) Text("No payment capability versions in this scope.", color = TaxiColors.Ink500)
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
    val next = when (capability.status) {
        "DRAFT" -> "submit"
        "IN_REVIEW" -> "approve"
        "APPROVED" -> "activate"
        else -> null
    }
    RecordSurface {
        Text("${capability.version} · ${capability.serviceType.replace('_', ' ')}", fontWeight = FontWeight.Bold)
        Text(
            "${capability.status} · CASH${if (capability.manualTransferEnabled) " + MANUAL TRANSFER" else ""}",
            color = TaxiColors.Ink500,
        )
        Text("Effective ${capability.effectiveFrom}", style = MaterialTheme.typography.bodySmall)
        next?.let {
            Button(
                onClick = { coordinator.transitionPaymentCapability(capability, it, reason) },
                enabled = !state.interactionLocked && reason.trim().length >= 3,
            ) { Text(it.replaceFirstChar { character -> character.uppercase() }) }
        }
    }
}

@Composable
private fun TransferQueue(
    transfers: List<ManualTransferReconciliationRecord>,
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    var settlementReference by remember { mutableStateOf("") }
    var rejectionReason by remember { mutableStateOf("") }
    OperationsPanel("Manual-transfer queue", "A passenger claim is not proof. Match amount, currency, TaxiMobile reference, and recipient statement independently.") {
        Field(settlementReference, { settlementReference = it }, "Authoritative settlement reference", state)
        Field(rejectionReason, { rejectionReason = it }, "Correction reason when rejecting", state)
        if (transfers.isEmpty()) Text("No submitted claims in the selected authorized scope.", color = TaxiColors.Ink500)
        transfers.forEach { transfer ->
            RecordSurface {
                Text("${transfer.amount} ${transfer.currency} · ${transfer.paymentReference}", fontWeight = FontWeight.Bold)
                Text("Recipient ${transfer.recipientLabel ?: "legacy pilot configuration"}", color = TaxiColors.Ink500)
                Text("Payer reference: ${transfer.payerReference ?: "not supplied"}", style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Button(
                        onClick = { coordinator.verifyManualTransfer(transfer.paymentId, settlementReference) },
                        enabled = !state.interactionLocked && settlementReference.trim().length >= 3,
                    ) { Text("Verify against statement") }
                    OutlinedButton(
                        onClick = { coordinator.rejectManualTransfer(transfer.paymentId, rejectionReason) },
                        enabled = !state.interactionLocked && rejectionReason.trim().length >= 3,
                    ) { Text("Reject claim") }
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
    OperationsPanel("Record confirmed refund", "This appends returned-money evidence. It never initiates a bank transfer or claws back driver earnings.") {
        Field(paymentId, { paymentId = it }, "Payment ID", state)
        Field(amount, { amount = it }, "Returned amount", state)
        Field(reason, { reason = it.uppercase() }, "Reason code", state)
        Field(method, { method = it.uppercase() }, "Settlement method: CASH or EXTERNAL_TRANSFER", state)
        Field(reference, { reference = it }, "Unique handover / outbound settlement reference", state)
        Field(note, { note = it }, "Restricted operator note", state)
        Button(
            onClick = {
                coordinator.recordPaymentRefund(
                    paymentId.trim(),
                    PaymentRefundCreateRequest(amount.trim(), reason.trim(), method.trim(), reference.trim(), note.trim()),
                )
            },
            enabled = !state.interactionLocked && paymentId.isNotBlank() && amount.isNotBlank() &&
                reference.trim().length >= 3 && note.trim().length >= 3,
        ) { Text("Record returned money") }
    }
}

@Composable
private fun RefundHistory(refunds: List<org.example.taximobile.operations.model.PaymentRefundRecord>) {
    OperationsPanel("Refund history", "Append-only records visible in the selected authorization scope.") {
        if (refunds.isEmpty()) Text("No refunds in scope.", color = TaxiColors.Ink500)
        refunds.forEach { refund ->
            RecordSurface {
                Text("${refund.amount} ${refund.currency} · ${refund.reason}", fontWeight = FontWeight.Bold)
                Text("Payment ${refund.paymentId} · ${refund.settlementMethod}", color = TaxiColors.Ink500)
                Text("Remaining refundable ${refund.remainingRefundableAmount} ${refund.currency}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun OperationsPanel(title: String, detail: String, content: @Composable ColumnScope.() -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = TaxiColors.Surface0,
        shape = RoundedCornerShape(TaxiRadii.Lg),
        border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
    ) {
        Column(Modifier.padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(detail, color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
            content()
        }
    }
}

@Composable
private fun RecordSurface(content: @Composable ColumnScope.() -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = TaxiColors.Surface1,
        shape = RoundedCornerShape(TaxiRadii.Md),
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
    )
}
