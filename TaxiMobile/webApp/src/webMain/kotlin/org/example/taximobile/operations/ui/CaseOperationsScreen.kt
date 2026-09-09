package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.CaseAlertRecord
import org.example.taximobile.operations.model.CaseNoteRecord
import org.example.taximobile.operations.model.MANAGE_SAFETY_CASES
import org.example.taximobile.operations.model.MANAGE_SUPPORT_CASES
import org.example.taximobile.operations.model.MANAGE_CASE_RETENTION
import org.example.taximobile.operations.model.LegalHoldCreateCommand
import org.example.taximobile.operations.model.LegalHoldRecord
import org.example.taximobile.operations.model.CaseRetentionActionRecord
import org.example.taximobile.operations.model.SafetyCaseDetail
import org.example.taximobile.operations.model.SafetyCaseSummary
import org.example.taximobile.operations.model.SafetyTransitionCommand
import org.example.taximobile.operations.model.SupportCaseDetail
import org.example.taximobile.operations.model.SupportCaseSummary
import org.example.taximobile.operations.model.SupportSafetyEscalationCommand
import org.example.taximobile.operations.model.SupportTransitionCommand
import org.example.taximobile.operations.model.SupportTriageCommand
import org.example.taximobile.operations.model.safetyTransitionTargets
import org.example.taximobile.operations.model.supportTransitionTargets
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState

private val supportResolutionCodes = listOf(
    "INFORMATION_PROVIDED",
    "ACTION_TAKEN",
    "REFUND_RECORDED",
    "DUPLICATE",
    "OUT_OF_SCOPE",
    "NO_ACTION",
)
private val safetyResolutionCodes = listOf(
    "SAFETY_ACTION_TAKEN",
    "REFERRED_TO_AUTHORITIES",
    "INFORMATION_PROVIDED",
    "DUPLICATE",
    "NO_PLATFORM_ACTION",
)
private val safetyCategories = listOf(
    "IMMEDIATE_DANGER",
    "ASSAULT",
    "HARASSMENT",
    "UNSAFE_DRIVING",
    "DISCRIMINATION",
    "VEHICLE_SAFETY",
    "OTHER_SAFETY",
)
private val legalHoldReasons = listOf(
    "LITIGATION",
    "REGULATORY_REQUEST",
    "LAW_ENFORCEMENT_REQUEST",
    "DISPUTE_PRESERVATION",
    "OTHER_LEGAL_OBLIGATION",
)
private val legalHoldReleaseReasons = listOf(
    "OBLIGATION_ENDED",
    "REQUEST_WITHDRAWN",
    "SUPERSEDED",
    "PLACED_IN_ERROR",
)

private sealed interface SupportCaseAction {
    data object Triage : SupportCaseAction
    data class Transition(val target: String) : SupportCaseAction
    data object Escalate : SupportCaseAction
    data object LegalHold : SupportCaseAction
}

@Composable
internal fun CaseOperationsScreen(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val snapshot = state.snapshot?.caseOperations
    val supportAllowed = state.session?.hasPermission(MANAGE_SUPPORT_CASES) == true
    val safetyAllowed = state.session?.hasPermission(MANAGE_SAFETY_CASES) == true
    val retentionAllowed = state.session?.hasPermission(MANAGE_CASE_RETENTION) == true
    var alertToAcknowledge by remember { mutableStateOf<CaseAlertRecord?>(null) }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg),
    ) {
        item {
            SectionHeading(
                title = "Restricted case operations",
                supportingText = "Queues, counts, and mutations are filtered by the active server-side grant. Free text is never part of analytics or pager payloads.",
            )
        }
        item {
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                MetricCard(
                    "Open pager alerts",
                    snapshot?.alerts?.items.orEmpty().count { it.status == "OPEN" }.toString(),
                    "Acknowledgement stops repeat paging, not case ownership.",
                )
                if (supportAllowed) {
                    MetricCard(
                        "Support queue",
                        (snapshot?.supportCases?.total ?: 0).toString(),
                        "Ordinary cases in the selected authorized city scope.",
                    )
                }
                if (safetyAllowed) {
                    MetricCard(
                        "Safety queue",
                        (snapshot?.safetyCases?.total ?: 0).toString(),
                        "More restricted reports; not an emergency dispatch service.",
                    )
                }
            }
        }
        item {
            OverdueAlertsSection(
                alerts = snapshot?.alerts?.items.orEmpty(),
                total = snapshot?.alerts?.total ?: 0,
                locked = state.interactionLocked,
                onOpenCase = { alert ->
                    if (alert.caseType == "SUPPORT") coordinator.selectSupportCase(alert.caseId)
                    else coordinator.selectSafetyCase(alert.caseId)
                },
                onAcknowledge = { alertToAcknowledge = it },
            )
        }
        if (supportAllowed) {
            item {
                SupportQueueSection(
                    cases = snapshot?.supportCases?.items.orEmpty(),
                    total = snapshot?.supportCases?.total ?: 0,
                    locked = state.interactionLocked,
                    onSelect = coordinator::selectSupportCase,
                )
            }
        }
        if (safetyAllowed) {
            item {
                SafetyQueueSection(
                    cases = snapshot?.safetyCases?.items.orEmpty(),
                    total = snapshot?.safetyCases?.total ?: 0,
                    locked = state.interactionLocked,
                    onSelect = coordinator::selectSafetyCase,
                )
            }
        }
        if (retentionAllowed) {
            item {
                RetentionSection(
                    holds = snapshot?.legalHolds?.items.orEmpty(),
                    actions = snapshot?.retentionActions?.items.orEmpty(),
                    locked = state.interactionLocked,
                    onRelease = coordinator::releaseCaseLegalHold,
                )
            }
        }
    }

    alertToAcknowledge?.let { alert ->
        AlertAcknowledgementDialog(
            alert = alert,
            onDismiss = { alertToAcknowledge = null },
            onConfirm = { reason ->
                alertToAcknowledge = null
                coordinator.acknowledgeCaseAlert(alert, reason)
            },
        )
    }
    state.selectedSupportCase?.let { detail ->
        SupportCaseFlow(
            detail = detail,
            locked = state.interactionLocked,
            safetyHandoffAvailable = supportAllowed,
            retentionAvailable = retentionAllowed,
            onDismiss = coordinator::dismissSelectedCase,
            onTriage = coordinator::triageSupportCase,
            onTransition = coordinator::transitionSupportCase,
            onEscalate = coordinator::escalateSupportCase,
            onLegalHold = coordinator::placeCaseLegalHold,
        )
    }
    state.selectedSafetyCase?.let { detail ->
        SafetyCaseFlow(
            detail = detail,
            locked = state.interactionLocked,
            retentionAvailable = retentionAllowed,
            onDismiss = coordinator::dismissSelectedCase,
            onTransition = coordinator::transitionSafetyCase,
            onLegalHold = coordinator::placeCaseLegalHold,
        )
    }
}

@Composable
private fun OverdueAlertsSection(
    alerts: List<CaseAlertRecord>,
    total: Int,
    locked: Boolean,
    onOpenCase: (CaseAlertRecord) -> Unit,
    onAcknowledge: (CaseAlertRecord) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = "Overdue response alerts",
            supportingText = "Durable alerts continue paging every 15 minutes until acknowledged or resolved by case progress.",
        )
        if (alerts.isEmpty()) {
            EmptyState("No overdue alerts", "No durable support or safety response alert is visible in this scope.")
        } else {
            DataCard {
                Column {
                    alerts.forEachIndexed { index, alert ->
                        if (index > 0) HorizontalDivider(color = TaxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
                                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                                    StatusBadge(alert.severity)
                                    StatusBadge(alert.status)
                                    StatusBadge(alert.caseType)
                                }
                                Text(
                                    "${alert.caseType.lowercase().replaceFirstChar { it.uppercase() }} ${shortId(alert.caseId)}",
                                    color = TaxiColors.Navy900,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    "Due ${compactTimestamp(alert.responseDueAt)} · detected ${compactTimestamp(alert.firstDetectedAt)} · ${alert.deliveryAttempts} delivery attempt(s)",
                                    color = TaxiColors.Ink500,
                                )
                            }
                            OutlinedButton(onClick = { onOpenCase(alert) }, enabled = !locked) {
                                Text("Open case")
                            }
                            if (alert.status == "OPEN") {
                                Button(onClick = { onAcknowledge(alert) }, enabled = !locked) {
                                    Text("Acknowledge pager")
                                }
                            }
                        }
                    }
                }
            }
            PageLimitNote(alerts.size, total)
        }
    }
}

@Composable
private fun SupportQueueSection(
    cases: List<SupportCaseSummary>,
    total: Int,
    locked: Boolean,
    onSelect: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = "Ordinary support",
            supportingText = "Claim, communicate, resolve, or hand ride-linked safety concerns into the restricted queue.",
        )
        if (cases.isEmpty()) {
            EmptyState("No support cases", "No ordinary support case is visible in the selected scope.")
        } else {
            DataCard(tableMinWidth = 860.dp) {
                Column {
                    QueueHeader(listOf("Case", "Category", "Status", "Priority", "Response due", "Owner", ""))
                    cases.forEach { item ->
                        HorizontalDivider(color = TaxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            QueueText("${shortId(item.id)}\n${item.subject}", Modifier.weight(1.5f))
                            QueueText(item.category.replace('_', ' '), Modifier.weight(1f))
                            StatusBadge(item.status, Modifier.weight(0.8f))
                            StatusBadge(item.priority, Modifier.weight(0.8f))
                            QueueText(compactTimestamp(item.responseDueAt), Modifier.weight(1f))
                            QueueText(shortId(item.assignedToUserId), Modifier.weight(0.8f))
                            OutlinedButton(onClick = { onSelect(item.id) }, enabled = !locked) { Text("Review") }
                        }
                    }
                }
            }
            PageLimitNote(cases.size, total)
        }
    }
}

@Composable
private fun SafetyQueueSection(
    cases: List<SafetyCaseSummary>,
    total: Int,
    locked: Boolean,
    onSelect: (String) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = "Restricted safety",
            supportingText = "Acknowledge every transition to the participant; immediate danger copy must direct them to local emergency services.",
        )
        if (cases.isEmpty()) {
            EmptyState("No safety reports", "No safety report is visible in the selected scope.")
        } else {
            DataCard(tableMinWidth = 860.dp) {
                Column {
                    QueueHeader(listOf("Report", "Category", "Status", "Priority", "Response due", "Owner", ""))
                    cases.forEach { item ->
                        HorizontalDivider(color = TaxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            QueueText("${shortId(item.id)}\nride ${shortId(item.rideId)}", Modifier.weight(1.5f))
                            QueueText(item.category.replace('_', ' '), Modifier.weight(1f))
                            StatusBadge(item.status, Modifier.weight(0.8f))
                            StatusBadge(item.priority, Modifier.weight(0.8f))
                            QueueText(compactTimestamp(item.responseDueAt), Modifier.weight(1f))
                            QueueText(shortId(item.assignedToUserId), Modifier.weight(0.8f))
                            OutlinedButton(onClick = { onSelect(item.id) }, enabled = !locked) { Text("Review") }
                        }
                    }
                }
            }
            PageLimitNote(cases.size, total)
        }
    }
}

@Composable
private fun QueueHeader(labels: List<String>) {
    Row(
        Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
    ) {
        labels.forEachIndexed { index, label ->
            val weight = when (index) {
                0 -> 1.5f
                1, 4 -> 1f
                2, 3, 5 -> 0.8f
                else -> 0.75f
            }
            Text(
                label.uppercase(),
                modifier = Modifier.weight(weight),
                color = TaxiColors.Ink500,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
private fun QueueText(value: String, modifier: Modifier) {
    Text(value, modifier = modifier, color = TaxiColors.Ink700, maxLines = 2, overflow = TextOverflow.Ellipsis)
}

@Composable
private fun RetentionSection(
    holds: List<LegalHoldRecord>,
    actions: List<CaseRetentionActionRecord>,
    locked: Boolean,
    onRelease: (LegalHoldRecord, String) -> Unit,
) {
    var releasing by remember { mutableStateOf<LegalHoldRecord?>(null) }
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = "Legal holds and retention evidence",
            supportingText = "Platform retention authority only. Active holds prevent erasure; release never runs erasure inside the browser request.",
        )
        if (holds.isEmpty() && actions.isEmpty()) {
            EmptyState("No retention records", "No legal hold or completed personal-data erasure is visible in this authorized scope.")
        } else {
            DataCard {
                Column {
                    holds.forEachIndexed { index, hold ->
                        if (index > 0) HorizontalDivider(color = TaxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
                                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                                    StatusBadge(hold.status)
                                    StatusBadge(hold.caseKind)
                                }
                                Text("${hold.caseKind.lowercase()} ${shortId(hold.caseId)} · ${hold.reasonCode.replace('_', ' ')}", color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
                                Text("Reference ${hold.authorityReference} · review ${compactTimestamp(hold.reviewDueAt)}", color = TaxiColors.Ink500)
                            }
                            if (hold.status == "ACTIVE") {
                                OutlinedButton(onClick = { releasing = hold }, enabled = !locked) { Text("Release") }
                            }
                        }
                    }
                    actions.forEach { action ->
                        HorizontalDivider(color = TaxiColors.StrokeSubtle)
                        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
                            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                                StatusBadge("ERASED")
                                StatusBadge(action.caseKind)
                            }
                            Text("${action.caseKind.lowercase()} ${shortId(action.caseId)} · ${action.action.replace('_', ' ')}", color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
                            Text("Due ${compactTimestamp(action.retentionDueAt)} · executed ${compactTimestamp(action.executedAt)} · ${action.erasedNoteCount} note(s) erased", color = TaxiColors.Ink500)
                        }
                    }
                }
            }
        }
    }
    releasing?.let { hold ->
        var reason by remember(hold.id) { mutableStateOf(legalHoldReleaseReasons.first()) }
        CommandDialog(
            title = "Release legal hold ${shortId(hold.id)}",
            guidance = "Release is audited and cannot be undone with the same hold. If retention is due, the worker may erase personal fields on its next pass.",
            onDismiss = { releasing = null },
            onConfirm = { releasing = null; onRelease(hold, reason) },
        ) {
            ControlledChoice("Release reason", reason, legalHoldReleaseReasons) { reason = it }
        }
    }
}

@Composable
private fun SupportCaseFlow(
    detail: SupportCaseDetail,
    locked: Boolean,
    safetyHandoffAvailable: Boolean,
    retentionAvailable: Boolean,
    onDismiss: () -> Unit,
    onTriage: (SupportTriageCommand) -> Unit,
    onTransition: (SupportTransitionCommand) -> Unit,
    onEscalate: (SupportSafetyEscalationCommand) -> Unit,
    onLegalHold: (LegalHoldCreateCommand) -> Unit,
) {
    var action by remember(detail.id) { mutableStateOf<SupportCaseAction?>(null) }
    when (val selectedAction = action) {
        null -> SupportCaseDetailDialog(
            detail = detail,
            locked = locked,
            safetyHandoffAvailable = safetyHandoffAvailable,
            retentionAvailable = retentionAvailable,
            onDismiss = onDismiss,
            onAction = { action = it },
        )
        SupportCaseAction.Triage -> SupportTriageDialog(
            currentPriority = detail.priority,
            onDismiss = { action = null },
            onConfirm = { action = null; onTriage(it) },
        )
        is SupportCaseAction.Transition -> SupportTransitionDialog(
            target = selectedAction.target,
            onDismiss = { action = null },
            onConfirm = { action = null; onTransition(it) },
        )
        SupportCaseAction.Escalate -> SafetyHandoffDialog(
            onDismiss = { action = null },
            onConfirm = { action = null; onEscalate(it) },
        )
        SupportCaseAction.LegalHold -> LegalHoldDialog(
            caseKind = "SUPPORT",
            caseId = detail.id,
            onDismiss = { action = null },
            onConfirm = { action = null; onLegalHold(it) },
        )
    }
}

@Composable
private fun SupportCaseDetailDialog(
    detail: SupportCaseDetail,
    locked: Boolean,
    safetyHandoffAvailable: Boolean,
    retentionAvailable: Boolean,
    onDismiss: () -> Unit,
    onAction: (SupportCaseAction) -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Support ${shortId(detail.id)}") },
        text = {
            CaseDetailBody(
                status = detail.status,
                priority = detail.priority,
                cityId = detail.cityId,
                rideId = detail.rideId,
                category = detail.category,
                responseDueAt = detail.responseDueAt,
                assignedTo = detail.assignedToUserId,
                description = detail.description,
                notes = detail.notes,
                retentionUntil = detail.retentionUntil,
            )
        },
        confirmButton = {
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
            ) {
                if (detail.status in setOf("OPEN", "IN_PROGRESS")) {
                    Button(onClick = { onAction(SupportCaseAction.Triage) }, enabled = !locked) {
                        Text(if (detail.status == "OPEN") "Claim & acknowledge" else "Retriage")
                    }
                }
                supportTransitionTargets(detail.status).forEach { target ->
                    OutlinedButton(
                        onClick = { onAction(SupportCaseAction.Transition(target)) },
                        enabled = !locked,
                    ) { Text(target.replace('_', ' ')) }
                }
                if (
                    safetyHandoffAvailable && detail.rideId != null &&
                    detail.status !in setOf("RESOLVED", "CLOSED")
                ) {
                    OutlinedButton(onClick = { onAction(SupportCaseAction.Escalate) }, enabled = !locked) {
                        Text("Hand to safety")
                    }
                }
                if (retentionAvailable) {
                    OutlinedButton(onClick = { onAction(SupportCaseAction.LegalHold) }, enabled = !locked) {
                        Text("Place legal hold")
                    }
                }
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Close") } },
    )
}

@Composable
private fun SafetyCaseFlow(
    detail: SafetyCaseDetail,
    locked: Boolean,
    retentionAvailable: Boolean,
    onDismiss: () -> Unit,
    onTransition: (SafetyTransitionCommand) -> Unit,
    onLegalHold: (LegalHoldCreateCommand) -> Unit,
) {
    var target by remember(detail.id) { mutableStateOf<String?>(null) }
    var placingHold by remember(detail.id) { mutableStateOf(false) }
    if (placingHold) {
        LegalHoldDialog(
            caseKind = "SAFETY",
            caseId = detail.id,
            onDismiss = { placingHold = false },
            onConfirm = { placingHold = false; onLegalHold(it) },
        )
    } else if (target == null) {
        AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text("Safety ${shortId(detail.id)}") },
            text = {
                CaseDetailBody(
                    status = detail.status,
                    priority = detail.priority,
                    cityId = detail.cityId,
                    rideId = detail.rideId,
                    category = detail.category,
                    responseDueAt = detail.responseDueAt,
                    assignedTo = detail.assignedToUserId,
                    description = detail.description,
                    notes = detail.notes,
                    retentionUntil = detail.retentionUntil,
                )
            },
            confirmButton = {
                Row(
                    Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs),
                ) {
                    safetyTransitionTargets(detail.status).forEach { next ->
                        Button(onClick = { target = next }, enabled = !locked) {
                            Text(next.replace('_', ' '))
                        }
                    }
                    if (retentionAvailable) {
                        OutlinedButton(onClick = { placingHold = true }, enabled = !locked) {
                            Text("Place legal hold")
                        }
                    }
                }
            },
            dismissButton = { TextButton(onClick = onDismiss) { Text("Close") } },
        )
    } else {
        SafetyTransitionDialog(
            target = target!!,
            onDismiss = { target = null },
            onConfirm = { target = null; onTransition(it) },
        )
    }
}

@Composable
private fun CaseDetailBody(
    status: String,
    priority: String,
    cityId: String,
    rideId: String?,
    category: String,
    responseDueAt: String,
    assignedTo: String?,
    description: String,
    notes: List<CaseNoteRecord>,
    retentionUntil: String?,
) {
    Column(
        Modifier.widthIn(min = 520.dp, max = 760.dp).heightIn(max = 520.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
    ) {
        Surface(
            color = TaxiColors.Warning100,
            shape = RoundedCornerShape(TaxiRadii.Md),
            border = BorderStroke(1.dp, TaxiColors.Warning600.copy(alpha = 0.25f)),
        ) {
            Text(
                "Restricted case content. Do not copy credentials, statements, identity documents, or unrelated personal data into notes.",
                Modifier.fillMaxWidth().padding(TaxiSpacing.Sm),
                color = TaxiColors.Warning600,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            StatusBadge(status)
            StatusBadge(priority)
            StatusBadge(category)
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg)) {
            KeyValue("City", shortId(cityId), Modifier.weight(1f))
            KeyValue("Ride", shortId(rideId), Modifier.weight(1f))
            KeyValue("Owner", shortId(assignedTo), Modifier.weight(1f))
        }
        KeyValue("Response due", compactTimestamp(responseDueAt))
        KeyValue("Description", description)
        retentionUntil?.let { KeyValue("Retention due", compactTimestamp(it)) }
        HorizontalDivider(color = TaxiColors.StrokeSubtle)
        Text("Append-only notes", color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
        if (notes.isEmpty()) Text("No case notes recorded.", color = TaxiColors.Ink500)
        notes.forEach { note ->
            Surface(
                color = if (note.visibility == "INTERNAL") TaxiColors.Surface2 else TaxiColors.Info100,
                shape = RoundedCornerShape(TaxiRadii.Md),
            ) {
                Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Sm)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(note.visibility, fontWeight = FontWeight.Bold, color = TaxiColors.Navy900)
                        Text(compactTimestamp(note.createdAt), color = TaxiColors.Ink500)
                    }
                    Text(note.message, color = TaxiColors.Ink700)
                }
            }
        }
    }
}

@Composable
private fun SupportTriageDialog(
    currentPriority: String,
    onDismiss: () -> Unit,
    onConfirm: (SupportTriageCommand) -> Unit,
) {
    var priority by remember { mutableStateOf(currentPriority) }
    var participant by remember { mutableStateOf("") }
    var internal by remember { mutableStateOf("") }
    CommandDialog(
        title = "Claim and acknowledge support",
        guidance = "This assigns the case to you. Keep participant communication separate from the minimal internal note.",
        onDismiss = onDismiss,
        onConfirm = { onConfirm(SupportTriageCommand(priority, participantMessage = participant, internalNote = internal)) },
    ) {
        ControlledChoice("Priority", priority, listOf("LOW", "NORMAL", "HIGH", "URGENT")) { priority = it }
        CommandText("Participant acknowledgement", participant) { participant = it }
        CommandText("Internal note", internal) { internal = it }
    }
}

@Composable
private fun SupportTransitionDialog(
    target: String,
    onDismiss: () -> Unit,
    onConfirm: (SupportTransitionCommand) -> Unit,
) {
    val terminal = target in setOf("RESOLVED", "CLOSED")
    var resolution by remember { mutableStateOf(if (terminal) supportResolutionCodes.first() else "") }
    var participant by remember { mutableStateOf("") }
    var internal by remember { mutableStateOf("") }
    CommandDialog(
        title = "Move support case to ${target.replace('_', ' ')}",
        guidance = if (terminal) "A controlled resolution and participant message are mandatory." else "Reopening clears the prior resolution projection; notes remain append-only.",
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                SupportTransitionCommand(
                    targetStatus = target,
                    resolutionCode = resolution.ifBlank { null },
                    participantMessage = participant.trim().ifBlank { null },
                    internalNote = internal,
                )
            )
        },
    ) {
        if (terminal) ControlledChoice("Resolution", resolution, supportResolutionCodes) { resolution = it }
        CommandText("Participant message${if (terminal) "" else " (optional)"}", participant) { participant = it }
        CommandText("Internal note", internal) { internal = it }
    }
}

@Composable
private fun SafetyHandoffDialog(
    onDismiss: () -> Unit,
    onConfirm: (SupportSafetyEscalationCommand) -> Unit,
) {
    var category by remember { mutableStateOf(safetyCategories.first()) }
    var internal by remember { mutableStateOf("") }
    CommandDialog(
        title = "Create restricted safety handoff",
        guidance = "The original description is copied into a separate safety report. The support response receives only a minimal receipt.",
        onDismiss = onDismiss,
        onConfirm = { onConfirm(SupportSafetyEscalationCommand(category, internal)) },
    ) {
        ControlledChoice("Safety category", category, safetyCategories) { category = it }
        CommandText("Internal handoff note", internal) { internal = it }
    }
}

@Composable
private fun SafetyTransitionDialog(
    target: String,
    onDismiss: () -> Unit,
    onConfirm: (SafetyTransitionCommand) -> Unit,
) {
    val terminal = target in setOf("RESOLVED", "CLOSED")
    var resolution by remember { mutableStateOf(if (terminal) safetyResolutionCodes.first() else "") }
    var participant by remember { mutableStateOf("") }
    var internal by remember { mutableStateOf("") }
    CommandDialog(
        title = "Move safety report to ${target.replace('_', ' ')}",
        guidance = "Every safety transition requires a participant-safe message. TaxiMobile does not claim to dispatch emergency help.",
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                SafetyTransitionCommand(
                    targetStatus = target,
                    resolutionCode = resolution.ifBlank { null },
                    participantMessage = participant,
                    internalNote = internal,
                )
            )
        },
    ) {
        if (terminal) ControlledChoice("Resolution", resolution, safetyResolutionCodes) { resolution = it }
        CommandText("Participant message", participant) { participant = it }
        CommandText("Internal note", internal) { internal = it }
    }
}

@Composable
private fun AlertAcknowledgementDialog(
    alert: CaseAlertRecord,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var reason by remember { mutableStateOf("") }
    CommandDialog(
        title = "Acknowledge ${alert.caseType.lowercase()} pager",
        guidance = "This stops repeat delivery for alert ${shortId(alert.id)}. It does not resolve, assign, or acknowledge the underlying case.",
        onDismiss = onDismiss,
        onConfirm = { onConfirm(reason) },
    ) {
        CommandText("Bounded acknowledgement reason", reason, singleLine = true) { reason = it }
    }
}

@Composable
private fun LegalHoldDialog(
    caseKind: String,
    caseId: String,
    onDismiss: () -> Unit,
    onConfirm: (LegalHoldCreateCommand) -> Unit,
) {
    var reason by remember { mutableStateOf(legalHoldReasons.first()) }
    var authorityReference by remember { mutableStateOf("") }
    var reviewDueAt by remember { mutableStateOf("") }
    CommandDialog(
        title = "Place legal hold on ${caseKind.lowercase()} ${shortId(caseId)}",
        guidance = "Use only an approved non-secret authority reference. A hold preserves case personal data until controlled release and review.",
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                LegalHoldCreateCommand(
                    caseKind = caseKind,
                    caseId = caseId,
                    reasonCode = reason,
                    authorityReference = authorityReference,
                    reviewDueAt = reviewDueAt,
                )
            )
        },
    ) {
        ControlledChoice("Legal reason", reason, legalHoldReasons) { reason = it }
        CommandText("Authority reference", authorityReference, singleLine = true) { authorityReference = it }
        CommandText("Review due (ISO 8601 with timezone)", reviewDueAt, singleLine = true) { reviewDueAt = it }
    }
}

@Composable
private fun CommandDialog(
    title: String,
    guidance: String,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
    fields: @Composable () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column(
                Modifier.widthIn(min = 480.dp, max = 640.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Text(guidance, color = TaxiColors.Ink500)
                fields()
            }
        },
        confirmButton = { Button(onClick = onConfirm) { Text("Confirm") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}

@Composable
private fun ControlledChoice(
    label: String,
    selected: String,
    options: List<String>,
    onSelected: (String) -> Unit,
) {
    ScopeMenu(
        label = label,
        selected = selected.replace('_', ' '),
        options = options.map { ScopeOption(it, it.replace('_', ' ')) },
        enabled = true,
        onSelected = { value -> value?.let(onSelected) },
    )
}

@Composable
private fun CommandText(
    label: String,
    value: String,
    singleLine: Boolean = false,
    onValueChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = singleLine,
        minLines = if (singleLine) 1 else 3,
        maxLines = if (singleLine) 1 else 6,
    )
}
