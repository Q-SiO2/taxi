package org.example.taximobile.operations.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
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
import org.example.taximobile.feature.ui.text.ltrIsolate
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*

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
                title = stringResource(Res.string.web_case_title),
                supportingText = stringResource(Res.string.web_case_help),
            )
        }
        item {
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                MetricCard(
                    stringResource(Res.string.web_case_open_alerts),
                    ltrIsolate(snapshot?.alerts?.items.orEmpty().count { it.status == "OPEN" }.toString()),
                    stringResource(Res.string.web_case_alert_metric_help),
                )
                if (supportAllowed) {
                    MetricCard(
                        stringResource(Res.string.web_case_support_queue),
                        ltrIsolate((snapshot?.supportCases?.total ?: 0).toString()),
                        stringResource(Res.string.web_case_support_metric_help),
                    )
                }
                if (safetyAllowed) {
                    MetricCard(
                        stringResource(Res.string.web_case_safety_queue),
                        ltrIsolate((snapshot?.safetyCases?.total ?: 0).toString()),
                        stringResource(Res.string.web_case_safety_metric_help),
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
    val taxiColors = TaxiTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = stringResource(Res.string.web_case_overdue),
            supportingText = stringResource(Res.string.web_case_overdue_help),
        )
        if (alerts.isEmpty()) {
            EmptyState(stringResource(Res.string.web_case_no_alerts), stringResource(Res.string.web_case_no_alerts_help))
        } else {
            DataCard {
                Column {
                    alerts.forEachIndexed { index, alert ->
                        if (index > 0) HorizontalDivider(color = taxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
                                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                                    StatusBadge(alert.severity, label = caseLabel(alert.severity))
                                    StatusBadge(alert.status, label = caseLabel(alert.status))
                                    StatusBadge(alert.caseType, label = caseLabel(alert.caseType))
                                }
                                Text(
                                    stringResource(Res.string.web_case_reference, caseLabel(alert.caseType), ltrIsolate(shortId(alert.caseId))),
                                    color = taxiColors.Navy900,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    stringResource(Res.string.web_case_alert_dates, ltrIsolate(compactTimestamp(alert.responseDueAt)), ltrIsolate(compactTimestamp(alert.firstDetectedAt)), ltrIsolate(alert.deliveryAttempts.toString())),
                                    color = taxiColors.Ink500,
                                )
                            }
                            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onOpenCase(alert) }, enabled = !locked) {
                                Text(stringResource(Res.string.web_case_open))
                            }
                            if (alert.status == "OPEN") {
                                Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onAcknowledge(alert) }, enabled = !locked) {
                                    Text(stringResource(Res.string.web_case_ack_alert))
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
    val taxiColors = TaxiTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = stringResource(Res.string.web_case_support),
            supportingText = stringResource(Res.string.web_case_support_help),
        )
        if (cases.isEmpty()) {
            EmptyState(stringResource(Res.string.web_case_no_support), stringResource(Res.string.web_case_no_support_help))
        } else {
            DataCard(tableMinWidth = 860.dp) {
                Column {
                    QueueHeader(listOf(stringResource(Res.string.web_case_case), stringResource(Res.string.web_case_category), stringResource(Res.string.web_table_status), stringResource(Res.string.web_case_priority), stringResource(Res.string.web_case_due), stringResource(Res.string.web_case_owner), ""))
                    cases.forEach { item ->
                        HorizontalDivider(color = taxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            QueueText("${ltrIsolate(shortId(item.id))}\n${item.subject}", Modifier.weight(1.5f))
                            QueueText(caseLabel(item.category), Modifier.weight(1f))
                            StatusBadge(item.status, Modifier.weight(0.8f), label = caseLabel(item.status))
                            StatusBadge(item.priority, Modifier.weight(0.8f), label = caseLabel(item.priority))
                            QueueText(ltrIsolate(compactTimestamp(item.responseDueAt)), Modifier.weight(1f))
                            QueueText(ltrIsolate(shortId(item.assignedToUserId)), Modifier.weight(0.8f))
                            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onSelect(item.id) }, enabled = !locked) { Text(stringResource(Res.string.web_recruit_review)) }
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
    val taxiColors = TaxiTheme.colors
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = stringResource(Res.string.web_case_safety),
            supportingText = stringResource(Res.string.web_case_safety_help),
        )
        if (cases.isEmpty()) {
            EmptyState(stringResource(Res.string.web_case_no_safety), stringResource(Res.string.web_case_no_safety_help))
        } else {
            DataCard(tableMinWidth = 860.dp) {
                Column {
                    QueueHeader(listOf(stringResource(Res.string.web_case_report), stringResource(Res.string.web_case_category), stringResource(Res.string.web_table_status), stringResource(Res.string.web_case_priority), stringResource(Res.string.web_case_due), stringResource(Res.string.web_case_owner), ""))
                    cases.forEach { item ->
                        HorizontalDivider(color = taxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            QueueText("${ltrIsolate(shortId(item.id))}\n${stringResource(Res.string.web_case_ride)} ${ltrIsolate(shortId(item.rideId))}", Modifier.weight(1.5f))
                            QueueText(caseLabel(item.category), Modifier.weight(1f))
                            StatusBadge(item.status, Modifier.weight(0.8f), label = caseLabel(item.status))
                            StatusBadge(item.priority, Modifier.weight(0.8f), label = caseLabel(item.priority))
                            QueueText(ltrIsolate(compactTimestamp(item.responseDueAt)), Modifier.weight(1f))
                            QueueText(ltrIsolate(shortId(item.assignedToUserId)), Modifier.weight(0.8f))
                            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onSelect(item.id) }, enabled = !locked) { Text(stringResource(Res.string.web_recruit_review)) }
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
    val taxiColors = TaxiTheme.colors
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
                color = taxiColors.Ink500,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
private fun QueueText(value: String, modifier: Modifier) {
    val taxiColors = TaxiTheme.colors
    Text(value, style = recruitmentTextStyle(value), modifier = modifier, color = taxiColors.Ink700, maxLines = 2, overflow = TextOverflow.Ellipsis)
}

@Composable
private fun RetentionSection(
    holds: List<LegalHoldRecord>,
    actions: List<CaseRetentionActionRecord>,
    locked: Boolean,
    onRelease: (LegalHoldRecord, String) -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    var releasing by remember { mutableStateOf<LegalHoldRecord?>(null) }
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        SectionHeading(
            title = stringResource(Res.string.web_case_retention),
            supportingText = stringResource(Res.string.web_case_retention_help),
        )
        if (holds.isEmpty() && actions.isEmpty()) {
            EmptyState(stringResource(Res.string.web_case_no_retention), stringResource(Res.string.web_case_no_retention_help))
        } else {
            DataCard {
                Column {
                    holds.forEachIndexed { index, hold ->
                        if (index > 0) HorizontalDivider(color = taxiColors.StrokeSubtle)
                        Row(
                            Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
                                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                                    StatusBadge(hold.status, label = caseLabel(hold.status))
                                    StatusBadge(hold.caseKind, label = caseLabel(hold.caseKind))
                                }
                                Text("${caseLabel(hold.caseKind)} ${ltrIsolate(shortId(hold.caseId))} · ${caseLabel(hold.reasonCode)}", color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
                                Text(stringResource(Res.string.web_case_hold_reference, ltrIsolate(hold.authorityReference), ltrIsolate(compactTimestamp(hold.reviewDueAt))), color = taxiColors.Ink500)
                            }
                            if (hold.status == "ACTIVE") {
                                OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { releasing = hold }, enabled = !locked) { Text(stringResource(Res.string.web_case_release)) }
                            }
                        }
                    }
                    actions.forEach { action ->
                        HorizontalDivider(color = taxiColors.StrokeSubtle)
                        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
                            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                                StatusBadge("ERASED", label = caseLabel("ERASED"))
                                StatusBadge(action.caseKind, label = caseLabel(action.caseKind))
                            }
                            Text("${caseLabel(action.caseKind)} ${ltrIsolate(shortId(action.caseId))} · ${caseLabel(action.action)}", color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
                            Text(stringResource(Res.string.web_case_erasure_dates, ltrIsolate(compactTimestamp(action.retentionDueAt)), ltrIsolate(compactTimestamp(action.executedAt)), ltrIsolate(action.erasedNoteCount.toString())), color = taxiColors.Ink500)
                        }
                    }
                }
            }
        }
    }
    releasing?.let { hold ->
        var reason by remember(hold.id) { mutableStateOf(legalHoldReleaseReasons.first()) }
        CommandDialog(
            title = stringResource(Res.string.web_case_release_title, ltrIsolate(shortId(hold.id))),
            guidance = stringResource(Res.string.web_case_release_help),
            onDismiss = { releasing = null },
            onConfirm = { releasing = null; onRelease(hold, reason) },
        ) {
            ControlledChoice(stringResource(Res.string.web_case_release_reason), reason, legalHoldReleaseReasons) { reason = it }
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
        shape = RoundedCornerShape(TaxiTheme.radii.Lg),
        title = { Text(stringResource(Res.string.web_case_support_reference, ltrIsolate(shortId(detail.id)))) },
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
                    Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onAction(SupportCaseAction.Triage) }, enabled = !locked) {
                        Text(if (detail.status == "OPEN") stringResource(Res.string.web_case_claim) else stringResource(Res.string.web_case_retriage))
                    }
                }
                supportTransitionTargets(detail.status).forEach { target ->
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = { onAction(SupportCaseAction.Transition(target)) },
                        enabled = !locked,
                    ) { Text(caseLabel(target)) }
                }
                if (
                    safetyHandoffAvailable && detail.rideId != null &&
                    detail.status !in setOf("RESOLVED", "CLOSED")
                ) {
                    OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onAction(SupportCaseAction.Escalate) }, enabled = !locked) {
                        Text(stringResource(Res.string.web_case_handoff))
                    }
                }
                if (retentionAvailable) {
                    OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onAction(SupportCaseAction.LegalHold) }, enabled = !locked) {
                        Text(stringResource(Res.string.web_case_hold))
                    }
                }
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(Res.string.web_recruit_close)) } },
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
            shape = RoundedCornerShape(TaxiTheme.radii.Lg),
            title = { Text(stringResource(Res.string.web_case_safety_reference, ltrIsolate(shortId(detail.id)))) },
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
                        Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { target = next }, enabled = !locked) {
                            Text(caseLabel(next))
                        }
                    }
                    if (retentionAvailable) {
                        OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { placingHold = true }, enabled = !locked) {
                            Text(stringResource(Res.string.web_case_hold))
                        }
                    }
                }
            },
            dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(Res.string.web_recruit_close)) } },
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    Column(
        Modifier.widthIn(max = 760.dp).fillMaxWidth().heightIn(max = 520.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
    ) {
        Surface(
            color = taxiColors.Warning100,
            shape = RoundedCornerShape(taxiRadii.Md),
            border = BorderStroke(1.dp, taxiColors.Warning600.copy(alpha = 0.25f)),
        ) {
            Text(
                stringResource(Res.string.web_case_restricted_help),
                Modifier.fillMaxWidth().padding(TaxiSpacing.Sm),
                color = taxiColors.Warning600,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            StatusBadge(status, label = caseLabel(status))
            StatusBadge(priority, label = caseLabel(priority))
            StatusBadge(category, label = caseLabel(category))
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg)) {
            KeyValue(stringResource(Res.string.web_city), ltrIsolate(shortId(cityId)), Modifier.weight(1f))
            KeyValue(stringResource(Res.string.web_case_ride), ltrIsolate(shortId(rideId)), Modifier.weight(1f))
            KeyValue(stringResource(Res.string.web_case_owner), ltrIsolate(shortId(assignedTo)), Modifier.weight(1f))
        }
        KeyValue(stringResource(Res.string.web_case_due), ltrIsolate(compactTimestamp(responseDueAt)))
        KeyValue(stringResource(Res.string.web_req_description), description)
        retentionUntil?.let { KeyValue(stringResource(Res.string.web_case_retention_due), ltrIsolate(compactTimestamp(it))) }
        HorizontalDivider(color = taxiColors.StrokeSubtle)
        Text(stringResource(Res.string.web_case_notes), color = taxiColors.Navy900, fontWeight = FontWeight.Bold)
        if (notes.isEmpty()) Text(stringResource(Res.string.web_case_no_notes), color = taxiColors.Ink500)
        notes.forEach { note ->
            Surface(
                color = if (note.visibility == "INTERNAL") taxiColors.Surface2 else taxiColors.Info100,
                shape = RoundedCornerShape(taxiRadii.Md),
            ) {
                Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Sm)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(caseLabel(note.visibility), fontWeight = FontWeight.Bold, color = taxiColors.Navy900)
                        Text(ltrIsolate(compactTimestamp(note.createdAt)), color = taxiColors.Ink500)
                    }
                    Text(note.message, style = recruitmentTextStyle(note.message), color = taxiColors.Ink700)
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
        title = stringResource(Res.string.web_case_triage_title),
        guidance = stringResource(Res.string.web_case_triage_help),
        onDismiss = onDismiss,
        onConfirm = { onConfirm(SupportTriageCommand(priority, participantMessage = participant, internalNote = internal)) },
    ) {
        ControlledChoice(stringResource(Res.string.web_case_priority), priority, listOf("LOW", "NORMAL", "HIGH", "URGENT")) { priority = it }
        CommandText(stringResource(Res.string.web_case_participant_ack), participant) { participant = it }
        CommandText(stringResource(Res.string.web_case_internal_note), internal) { internal = it }
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
        title = stringResource(Res.string.web_case_support_transition_title, caseLabel(target)),
        guidance = if (terminal) stringResource(Res.string.web_case_resolution_required) else stringResource(Res.string.web_case_reopen_help),
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
        if (terminal) ControlledChoice(stringResource(Res.string.web_case_resolution), resolution, supportResolutionCodes) { resolution = it }
        CommandText(stringResource(if (terminal) Res.string.web_case_participant_message else Res.string.web_case_optional_message), participant) { participant = it }
        CommandText(stringResource(Res.string.web_case_internal_note), internal) { internal = it }
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
        title = stringResource(Res.string.web_case_handoff_title),
        guidance = stringResource(Res.string.web_case_handoff_help),
        onDismiss = onDismiss,
        onConfirm = { onConfirm(SupportSafetyEscalationCommand(category, internal)) },
    ) {
        ControlledChoice(stringResource(Res.string.web_case_safety_category), category, safetyCategories) { category = it }
        CommandText(stringResource(Res.string.web_case_handoff_note), internal) { internal = it }
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
        title = stringResource(Res.string.web_case_safety_transition_title, caseLabel(target)),
        guidance = stringResource(Res.string.web_case_safety_transition_help),
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
        if (terminal) ControlledChoice(stringResource(Res.string.web_case_resolution), resolution, safetyResolutionCodes) { resolution = it }
        CommandText(stringResource(Res.string.web_case_participant_message), participant) { participant = it }
        CommandText(stringResource(Res.string.web_case_internal_note), internal) { internal = it }
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
        title = stringResource(Res.string.web_case_ack_title, caseLabel(alert.caseType)),
        guidance = stringResource(Res.string.web_case_ack_help, ltrIsolate(shortId(alert.id))),
        onDismiss = onDismiss,
        onConfirm = { onConfirm(reason) },
    ) {
        CommandText(stringResource(Res.string.web_case_ack_reason), reason, singleLine = true) { reason = it }
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
        title = stringResource(Res.string.web_case_hold_title, caseLabel(caseKind), ltrIsolate(shortId(caseId))),
        guidance = stringResource(Res.string.web_case_hold_help),
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
        ControlledChoice(stringResource(Res.string.web_case_legal_reason), reason, legalHoldReasons) { reason = it }
        CommandText(stringResource(Res.string.web_case_authority_reference), authorityReference, singleLine = true) { authorityReference = it }
        CommandText(stringResource(Res.string.web_case_review_due), reviewDueAt, singleLine = true) { reviewDueAt = it }
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
    val taxiColors = TaxiTheme.colors
    AlertDialog(
        onDismissRequest = onDismiss,
        shape = RoundedCornerShape(TaxiTheme.radii.Lg),
        title = { Text(title) },
        text = {
            Column(
                Modifier.widthIn(max = 640.dp).fillMaxWidth().verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Text(guidance, color = taxiColors.Ink500)
                fields()
            }
        },
        confirmButton = { Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = onConfirm) { Text(stringResource(Res.string.web_case_confirm)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(Res.string.web_cancel)) } },
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
        selected = caseLabel(selected),
        options = options.map { ScopeOption(it, caseLabel(it)) },
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
        textStyle = recruitmentTextStyle(value),
        modifier = Modifier.fillMaxWidth(),
        singleLine = singleLine,
        minLines = if (singleLine) 1 else 3,
        maxLines = if (singleLine) 1 else 6,
    )
}
