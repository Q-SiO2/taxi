package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import kotlin.time.Clock
import kotlin.time.Duration.Companion.hours
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.MANAGE_SECURITY_INCIDENTS
import org.example.taximobile.operations.model.SecurityIncidentCategory
import org.example.taximobile.operations.model.SecurityIncidentPostmortemOutcome
import org.example.taximobile.operations.model.SecurityIncidentRecord
import org.example.taximobile.operations.model.SecurityIncidentResponsibility
import org.example.taximobile.operations.model.SecurityIncidentSeverity
import org.example.taximobile.operations.model.SecurityIncidentTimelineKind
import org.example.taximobile.operations.model.securityIncidentCreateInputError
import org.example.taximobile.operations.model.securityIncidentPostmortemInputError
import org.example.taximobile.operations.model.securityIncidentResponsibilityInputError
import org.example.taximobile.operations.model.securityIncidentTimelineInputError
import org.example.taximobile.operations.model.securityIncidentTransitionFor
import org.example.taximobile.operations.model.securityIncidentTransitionInputError
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState

@Composable
internal fun SecurityIncidentScreen(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val workspace = state.snapshot?.securityIncidents
    val authorized = state.session?.hasPermission(MANAGE_SECURITY_INCIDENTS) == true

    ScreenColumn {
        SectionHeading(
            title = "Security incidents",
            supportingText = "Restricted containment, evidence, recovery, and postmortem control.",
        )
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = TaxiColors.Warning100,
            shape = RoundedCornerShape(TaxiRadii.Md),
            border = BorderStroke(1.dp, TaxiColors.Warning600),
        ) {
            Text(
                "Never paste passwords, tokens, provider credentials, raw callback bodies, or unnecessary participant identity here. Commands are not replayed automatically after MFA or conflicts.",
                modifier = Modifier.padding(TaxiSpacing.Md),
                color = TaxiColors.Ink700,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        when {
            !authorized || workspace == null -> EmptyState(
                "Incident workflow not authorized",
                "A market-scoped platform grant with the dedicated security-incident permission is required.",
            )
            else -> {
                CreateSecurityIncidentPanel(state, coordinator)
                IncidentQueue(state, coordinator)
                state.selectedSecurityIncident?.let { incident ->
                    IncidentDetail(state, incident)
                    IncidentResponsibilitiesPanel(state, coordinator, incident)
                    TimelinePanel(state, coordinator, incident)
                    IncidentTransitionPanel(state, coordinator, incident)
                    IncidentPostmortemPanel(state, coordinator, incident)
                }
            }
        }
    }
}

@Composable
private fun CreateSecurityIncidentPanel(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    var severity by remember { mutableStateOf(SecurityIncidentSeverity.SEV2) }
    var category by remember { mutableStateOf(SecurityIncidentCategory.ACCOUNT_COMPROMISE) }
    var summary by remember { mutableStateOf("") }
    var detectedAt by remember { mutableStateOf(Clock.System.now().toString()) }
    var containmentDueAt by remember { mutableStateOf((Clock.System.now() + 2.hours).toString()) }
    var cityScoped by remember(state.scope.cityId) { mutableStateOf(state.scope.cityId != null) }
    var confirmation by remember { mutableStateOf("") }
    val inputError = securityIncidentCreateInputError(
        state.scope.marketId,
        summary,
        detectedAt,
        containmentDueAt,
    )
    SecurityIncidentPanel("Open a restricted incident", "The reporting administrator becomes the initial lead.") {
        Text("Severity", style = MaterialTheme.typography.labelLarge)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            SecurityIncidentSeverity.entries.forEach { candidate ->
                FilterChip(
                    selected = severity == candidate,
                    onClick = { severity = candidate },
                    label = { Text(candidate.label) },
                    enabled = !state.interactionLocked,
                )
            }
        }
        Text("Category", style = MaterialTheme.typography.labelLarge)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            SecurityIncidentCategory.entries.forEach { candidate ->
                FilterChip(
                    selected = category == candidate,
                    onClick = { category = candidate },
                    label = { Text(candidate.label) },
                    enabled = !state.interactionLocked,
                )
            }
        }
        if (state.scope.cityId != null) {
            FilterChip(
                selected = cityScoped,
                onClick = { cityScoped = !cityScoped },
                label = { Text(if (cityScoped) "Selected city scope" else "Whole selected market") },
                enabled = !state.interactionLocked,
            )
        }
        OutlinedTextField(
            value = summary,
            onValueChange = { if (it.length <= 500) summary = it },
            label = { Text("Operational summary") },
            supportingText = { Text("10–500 characters; no secrets or copied case narrative.") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2,
            enabled = !state.interactionLocked,
        )
        TimestampFields(
            firstLabel = "Detected at (ISO UTC)",
            first = detectedAt,
            onFirst = { detectedAt = it },
            secondLabel = "Containment due at (ISO UTC)",
            second = containmentDueAt,
            onSecond = { containmentDueAt = it },
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = confirmation,
            onValueChange = { if (it.length <= 20) confirmation = it.uppercase() },
            label = { Text("Type OPEN INCIDENT") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        inputError?.let { Text(it, color = TaxiColors.Warning600) }
        Button(
            onClick = {
                val submitted = confirmation
                confirmation = ""
                coordinator.createSecurityIncident(
                    severity,
                    category,
                    summary,
                    detectedAt,
                    containmentDueAt,
                    cityScoped,
                    submitted,
                )
            },
            enabled = !state.interactionLocked && inputError == null &&
                confirmation.trim() == "OPEN INCIDENT",
        ) { Text("Open incident") }
    }
}

@Composable
private fun IncidentQueue(state: OperationsUiState, coordinator: OperationsCoordinator) {
    val page = state.snapshot?.securityIncidents?.incidents ?: return
    SectionHeading("Incident queue", "Open and closed records in the selected market scope.")
    if (page.items.isEmpty()) {
        EmptyState("No security incidents", "No restricted incident record exists in this authorized market.")
        return
    }
    DataCard {
        Column(Modifier.fillMaxWidth()) {
            page.items.forEach { incident ->
                Row(
                    Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                    horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                ) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                            StatusBadge(incident.severity)
                            StatusBadge(incident.status)
                        }
                        Text(incident.reference, fontWeight = FontWeight.Bold, color = TaxiColors.Navy900)
                        Text(incident.summary, color = TaxiColors.Ink700, maxLines = 2)
                        Text(
                            "Opened ${compactTimestamp(incident.openedAt)} · containment ${compactTimestamp(incident.containmentDueAt)}",
                            style = MaterialTheme.typography.bodySmall,
                            color = TaxiColors.Ink500,
                        )
                    }
                    OutlinedButton(
                        onClick = { coordinator.selectSecurityIncident(incident.id) },
                        enabled = !state.interactionLocked,
                    ) { Text(if (state.selectedSecurityIncident?.id == incident.id) "Selected" else "Review") }
                }
            }
        }
    }
    PageLimitNote(page.items.size, page.total)
}

@Composable
private fun IncidentDetail(state: OperationsUiState, incident: SecurityIncidentRecord) {
    SecurityIncidentPanel(incident.reference, "Authoritative incident state · version ${incident.optimisticVersion}") {
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            StatusBadge(incident.severity)
            StatusBadge(incident.status)
            StatusBadge(incident.category)
        }
        Text(incident.summary, color = TaxiColors.Ink900)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xl)) {
            KeyValue("Lead", shortId(incident.leadUserId))
            KeyValue("Detected", compactTimestamp(incident.detectedAt))
            KeyValue("Containment due", compactTimestamp(incident.containmentDueAt))
            KeyValue("City", incident.cityId?.let(::shortId) ?: "Market-wide")
            incident.postmortemDueAt?.let {
                KeyValue("Postmortem due", compactTimestamp(it))
            }
            incident.postmortemCompletedAt?.let {
                KeyValue("Postmortem completed", compactTimestamp(it))
            }
            incident.postmortemOutcome?.let {
                KeyValue("Postmortem outcome", it.replace('_', ' '))
            }
        }
        if (state.securityIncidentTimeline == null) {
            Text("Timeline unavailable; refresh before acting.", color = TaxiColors.Warning600)
        }
    }
}

@Composable
private fun IncidentResponsibilitiesPanel(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
    incident: SecurityIncidentRecord,
) {
    val page = state.securityIncidentResponsibilities
    var responsibility by remember(incident.id) {
        mutableStateOf(SecurityIncidentResponsibility.SECURITY_RESPONSE_LEAD)
    }
    var assignedUserId by remember(incident.id, incident.optimisticVersion) {
        mutableStateOf("")
    }
    var occurredAt by remember(incident.id, incident.optimisticVersion) {
        mutableStateOf(Clock.System.now().toString())
    }
    var externalReference by remember(incident.id, incident.optimisticVersion) {
        mutableStateOf("")
    }
    var confirmation by remember(incident.id, incident.optimisticVersion) {
        mutableStateOf("")
    }
    val inputError = securityIncidentResponsibilityInputError(
        incident,
        assignedUserId,
        occurredAt,
        externalReference,
        confirmation,
    )
    SecurityIncidentPanel(
        "Incident responsibilities",
        "One active assignee per role. Reassignment releases the prior tenure but preserves its history.",
    ) {
        when {
            page == null -> Text(
                "Responsibility history unavailable; refresh before assigning.",
                color = TaxiColors.Warning600,
            )
            page.items.isEmpty() -> Text(
                "No responsibility assignment was returned. Stop and investigate the incident record.",
                color = TaxiColors.Warning600,
            )
            else -> {
                page.items.filter { it.releasedAt == null }.forEach { assignment ->
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                    ) {
                        StatusBadge(assignment.responsibility.replace('_', ' '))
                        Column(Modifier.weight(1f)) {
                            Text("Active · ${shortId(assignment.assignedUserId)}")
                            Text(
                                "Since ${compactTimestamp(assignment.assignedAt)} · ${assignment.assignmentReference}",
                                color = TaxiColors.Ink500,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
                val released = page.items.filter { it.releasedAt != null }
                if (released.isNotEmpty()) {
                    Text("Released history", fontWeight = FontWeight.Bold)
                    released.forEach { assignment ->
                        Text(
                            "${assignment.responsibility.replace('_', ' ')} · ${shortId(assignment.assignedUserId)} · " +
                                "${compactTimestamp(assignment.assignedAt)} to ${compactTimestamp(assignment.releasedAt!!)}",
                            color = TaxiColors.Ink500,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
                PageLimitNote(page.items.size, page.total)
            }
        }
        if (incident.postmortemCompletedAt != null) {
            Text(
                "Postmortem complete: responsibility history is read-only.",
                color = TaxiColors.Ink500,
            )
            return@SecurityIncidentPanel
        }
        Text("Assign or replace", style = MaterialTheme.typography.labelLarge)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            SecurityIncidentResponsibility.entries.forEach { candidate ->
                FilterChip(
                    selected = responsibility == candidate,
                    onClick = { responsibility = candidate },
                    label = { Text(candidate.label) },
                    enabled = !state.interactionLocked,
                )
            }
        }
        OutlinedTextField(
            value = assignedUserId,
            onValueChange = { if (it.length <= 36) assignedUserId = it },
            label = { Text("Exact approved responder UUID") },
            supportingText = {
                Text("The responder must already hold active authority for this market.")
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = occurredAt,
            onValueChange = { occurredAt = it },
            label = { Text("Assigned at (ISO UTC)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = externalReference,
            onValueChange = { if (it.length <= 160) externalReference = it },
            label = { Text("Approved roster/shift reference") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = confirmation,
            onValueChange = {
                if (it.length <= 21) confirmation = it.uppercase()
            },
            label = { Text("Type ASSIGN RESPONSIBILITY") },
            supportingText = {
                Text("A stale version reloads the record and requires fresh confirmation.")
            },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        inputError?.let { Text(it, color = TaxiColors.Warning600) }
        Button(
            onClick = {
                val submitted = confirmation
                confirmation = ""
                coordinator.assignSecurityIncidentResponsibility(
                    responsibility,
                    assignedUserId,
                    occurredAt,
                    externalReference,
                    submitted,
                )
            },
            enabled = !state.interactionLocked && page != null && inputError == null,
        ) { Text("Assign responsibility") }
    }
}

@Composable
private fun TimelinePanel(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
    incident: SecurityIncidentRecord,
) {
    var kind by remember { mutableStateOf(SecurityIncidentTimelineKind.EVIDENCE_LINKED) }
    var summary by remember { mutableStateOf("") }
    var occurredAt by remember { mutableStateOf(Clock.System.now().toString()) }
    var auditLogId by remember { mutableStateOf("") }
    var externalReference by remember { mutableStateOf("") }
    var confirmation by remember { mutableStateOf("") }
    val inputError = securityIncidentTimelineInputError(
        incident,
        summary,
        occurredAt,
        auditLogId,
        externalReference,
        confirmation,
    )
    SecurityIncidentPanel("Immutable timeline", "Corrections are new events; existing facts cannot be edited or deleted.") {
        state.securityIncidentTimeline?.items?.forEach { entry ->
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = TaxiColors.Surface1,
                shape = RoundedCornerShape(TaxiRadii.Md),
            ) {
                Column(Modifier.padding(TaxiSpacing.Md)) {
                    Text("#${entry.sequence} · ${entry.kind.replace('_', ' ')}", fontWeight = FontWeight.Bold)
                    Text(entry.summary, color = TaxiColors.Ink700)
                    Text(
                        "${compactTimestamp(entry.occurredAt)} · ${entry.externalReference ?: entry.auditLogId?.let(::shortId) ?: "Lifecycle event"}",
                        style = MaterialTheme.typography.bodySmall,
                        color = TaxiColors.Ink500,
                    )
                }
            }
        }
        Text("Append a referenced fact", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            SecurityIncidentTimelineKind.entries.forEach { candidate ->
                FilterChip(
                    selected = kind == candidate,
                    onClick = { kind = candidate },
                    label = { Text(candidate.label) },
                    enabled = !state.interactionLocked,
                )
            }
        }
        OutlinedTextField(
            value = summary,
            onValueChange = { if (it.length <= 500) summary = it },
            label = { Text("Timeline summary") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2,
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = occurredAt,
            onValueChange = { occurredAt = it },
            label = { Text("Occurred at (ISO UTC)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        TimestampFields(
            firstLabel = "Scoped audit UUID (optional)",
            first = auditLogId,
            onFirst = { auditLogId = it },
            secondLabel = "External runbook/reference (optional)",
            second = externalReference,
            onSecond = { externalReference = it },
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = confirmation,
            onValueChange = { if (it.length <= 8) confirmation = it.uppercase() },
            label = { Text("Type APPEND") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        inputError?.let { Text(it, color = TaxiColors.Warning600) }
        Button(
            onClick = {
                val submitted = confirmation
                confirmation = ""
                coordinator.appendSecurityIncidentTimeline(
                    kind,
                    summary,
                    occurredAt,
                    auditLogId,
                    externalReference,
                    submitted,
                )
            },
            enabled = !state.interactionLocked && inputError == null,
        ) { Text("Append fact") }
    }
}

@Composable
private fun IncidentTransitionPanel(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
    incident: SecurityIncidentRecord,
) {
    val transition = securityIncidentTransitionFor(incident.status)
    if (transition == null) {
        EmptyState(
            "Incident closed",
            if (incident.postmortemCompletedAt == null) {
                "Complete the required postmortem below; supporting facts remain append-only."
            } else {
                "The postmortem is complete. Corrections remain append-only timeline facts."
            },
        )
        return
    }
    var summary by remember(incident.id, incident.optimisticVersion) { mutableStateOf("") }
    var occurredAt by remember(incident.id, incident.optimisticVersion) {
        mutableStateOf(Clock.System.now().toString())
    }
    var postmortemDueAt by remember(incident.id, incident.optimisticVersion) { mutableStateOf("") }
    var confirmation by remember(incident.id, incident.optimisticVersion) { mutableStateOf("") }
    val inputError = securityIncidentTransitionInputError(
        incident,
        transition,
        summary,
        occurredAt,
        postmortemDueAt,
        confirmation,
    )
    SecurityIncidentPanel(transition.label, "Only the next forward lifecycle action is available.") {
        Text("${incident.status} → ${transition.targetStatus}", fontWeight = FontWeight.Bold)
        OutlinedTextField(
            value = summary,
            onValueChange = { if (it.length <= 500) summary = it },
            label = { Text("Action summary") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2,
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = occurredAt,
            onValueChange = { occurredAt = it },
            label = { Text("Occurred at (ISO UTC)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        if (transition.targetStatus == "CLOSED") {
            OutlinedTextField(
                value = postmortemDueAt,
                onValueChange = { postmortemDueAt = it },
                label = { Text("Postmortem due at (ISO UTC)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                enabled = !state.interactionLocked,
            )
        }
        OutlinedTextField(
            value = confirmation,
            onValueChange = { if (it.length <= 24) confirmation = it.uppercase() },
            label = { Text("Type ${transition.confirmationPhrase}") },
            supportingText = { Text("A stale version reloads the queue; review and confirm again.") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        inputError?.let { Text(it, color = TaxiColors.Warning600) }
        Button(
            onClick = {
                val submitted = confirmation
                confirmation = ""
                coordinator.transitionSecurityIncident(
                    transition,
                    summary,
                    occurredAt,
                    postmortemDueAt,
                    submitted,
                )
            },
            enabled = !state.interactionLocked && inputError == null,
        ) { Text(transition.label) }
    }
}

@Composable
private fun IncidentPostmortemPanel(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
    incident: SecurityIncidentRecord,
) {
    if (incident.status != "CLOSED") return
    if (incident.postmortemCompletedAt != null) {
        SecurityIncidentPanel(
            "Postmortem completed",
            "The completion is immutable; append any correction or follow-up as a new timeline fact.",
        ) {
            StatusBadge(incident.postmortemOutcome ?: "RECORDED")
            KeyValue("Completed", compactTimestamp(incident.postmortemCompletedAt))
            incident.postmortemCompletedByUserId?.let {
                KeyValue("Completed by", shortId(it))
            }
        }
        return
    }
    var outcome by remember(incident.id, incident.optimisticVersion) {
        mutableStateOf(SecurityIncidentPostmortemOutcome.CONTROL_CHANGED)
    }
    var summary by remember(incident.id, incident.optimisticVersion) { mutableStateOf("") }
    var occurredAt by remember(incident.id, incident.optimisticVersion) {
        mutableStateOf(Clock.System.now().toString())
    }
    var auditLogId by remember(incident.id, incident.optimisticVersion) { mutableStateOf("") }
    var externalReference by remember(incident.id, incident.optimisticVersion) { mutableStateOf("") }
    var confirmation by remember(incident.id, incident.optimisticVersion) { mutableStateOf("") }
    val inputError = securityIncidentPostmortemInputError(
        incident,
        outcome,
        summary,
        occurredAt,
        auditLogId,
        externalReference,
        confirmation,
    )
    SecurityIncidentPanel(
        "Complete required postmortem",
        "Record one controlled outcome and immutable evidence. Follow-up work must link its approved external reference.",
    ) {
        incident.postmortemDueAt?.let {
            Text("Due ${compactTimestamp(it)}", fontWeight = FontWeight.Bold)
        }
        FlowRow(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            SecurityIncidentPostmortemOutcome.entries.forEach { candidate ->
                FilterChip(
                    selected = outcome == candidate,
                    onClick = { outcome = candidate },
                    label = { Text(candidate.label) },
                    enabled = !state.interactionLocked,
                )
            }
        }
        OutlinedTextField(
            value = summary,
            onValueChange = { if (it.length <= 500) summary = it },
            label = { Text("Postmortem conclusion") },
            supportingText = { Text("10–500 characters; exclude secrets and unnecessary participant data.") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2,
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = occurredAt,
            onValueChange = { occurredAt = it },
            label = { Text("Completed at (ISO UTC)") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        TimestampFields(
            firstLabel = "Scoped audit UUID (optional)",
            first = auditLogId,
            onFirst = { auditLogId = it },
            secondLabel = if (outcome == SecurityIncidentPostmortemOutcome.FOLLOW_UP_REQUIRED) {
                "Approved follow-up reference (required)"
            } else {
                "Postmortem/follow-up reference (optional)"
            },
            second = externalReference,
            onSecond = { externalReference = it },
            enabled = !state.interactionLocked,
        )
        OutlinedTextField(
            value = confirmation,
            onValueChange = { if (it.length <= 24) confirmation = it.uppercase() },
            label = { Text("Type COMPLETE POSTMORTEM") },
            supportingText = { Text("A stale version reloads the record and requires a new review.") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = !state.interactionLocked,
        )
        inputError?.let { Text(it, color = TaxiColors.Warning600) }
        Button(
            onClick = {
                val submitted = confirmation
                confirmation = ""
                coordinator.completeSecurityIncidentPostmortem(
                    outcome,
                    summary,
                    occurredAt,
                    auditLogId,
                    externalReference,
                    submitted,
                )
            },
            enabled = !state.interactionLocked && inputError == null,
        ) { Text("Complete postmortem") }
    }
}

@Composable
private fun TimestampFields(
    firstLabel: String,
    first: String,
    onFirst: (String) -> Unit,
    secondLabel: String,
    second: String,
    onSecond: (String) -> Unit,
    enabled: Boolean,
) {
    Column(
        Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
    ) {
        OutlinedTextField(
            value = first,
            onValueChange = onFirst,
            label = { Text(firstLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = enabled,
        )
        OutlinedTextField(
            value = second,
            onValueChange = onSecond,
            label = { Text(secondLabel) },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            enabled = enabled,
        )
    }
}

@Composable
private fun SecurityIncidentPanel(
    title: String,
    detail: String,
    content: @Composable ColumnScope.() -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = TaxiColors.Surface0,
        shape = RoundedCornerShape(TaxiRadii.Lg),
        border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
    ) {
        Column(
            Modifier.padding(TaxiSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(detail, color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
            content()
        }
    }
}
