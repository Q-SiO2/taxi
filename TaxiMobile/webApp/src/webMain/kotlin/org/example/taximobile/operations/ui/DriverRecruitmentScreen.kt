package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.DriverApplicationDecisionRequest
import org.example.taximobile.operations.model.DriverRequirementItemInput
import org.example.taximobile.operations.model.DriverRequirementItemRecord
import org.example.taximobile.operations.model.DriverRequirementVersionCreateRequest
import org.example.taximobile.operations.model.DriverRequirementVersionRecord
import org.example.taximobile.operations.model.DriverRequirementVersionUpdateRequest
import org.example.taximobile.operations.model.MANAGE_DRIVER_REQUIREMENTS
import org.example.taximobile.operations.model.OperationsDriverApplicationDetail
import org.example.taximobile.operations.model.REVIEW_DRIVER_APPLICATIONS
import org.example.taximobile.operations.model.RecruitmentLocalizedCopy
import org.example.taximobile.operations.model.VIEW_SCOPED_OPERATIONAL_AGGREGATES
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState
import org.example.taximobile.operations.state.browserProtectedDocumentDownloadAvailable

@Composable
internal fun DriverRecruitmentScreen(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val snapshot = state.snapshot ?: return
    val permissions = state.session?.permissions.orEmpty()
    val city = snapshot.cities.items.firstOrNull { it.id == state.scope.cityId }
    ScreenColumn {
        SectionHeading(
            title = "Driver recruitment",
            supportingText = "Version city requirements, review only granted applications, and inspect privacy-bounded onboarding health.",
        )
        if (city == null) {
            EmptyState("Select a city", "Driver requirements and funnel aggregates require one explicitly scoped city.")
            return@ScreenColumn
        }
        Surface(
            color = TaxiColors.Info100,
            shape = RoundedCornerShape(TaxiRadii.Md),
            border = BorderStroke(1.dp, TaxiColors.Info600.copy(alpha = 0.25f)),
        ) {
            Text(
                "Active city: ${city.localizedName.preferred()} (${city.code}). Browser selection never broadens backend grants.",
                Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                color = TaxiColors.Info600,
            )
        }
        if (VIEW_SCOPED_OPERATIONAL_AGGREGATES in permissions) {
            OnboardingAggregateSection(state)
        }
        if (MANAGE_DRIVER_REQUIREMENTS in permissions) {
            RequirementVersionSection(state, coordinator)
        }
        if (REVIEW_DRIVER_APPLICATIONS in permissions) {
            DriverReviewSection(state, coordinator)
        }
    }
}

@Composable
private fun OnboardingAggregateSection(state: OperationsUiState) {
    val aggregate = state.snapshot?.onboardingAggregate
    SectionHeading(
        "Onboarding funnel",
        "Small cells are suppressed by the backend and never reconstructed in the browser.",
    )
    if (aggregate == null) {
        EmptyState("Aggregate unavailable", "Select an authorized city or refresh the scoped data.")
        return
    }
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
        MetricCard(
            "Total applications",
            aggregate.totalApplications?.toString() ?: "Suppressed",
            if (aggregate.totalSuppressed) "Cell has fewer than ${aggregate.minimumCellSize} records" else "All statuses",
            Modifier.width(220.dp),
        )
        MetricCard(
            "Decided applications",
            aggregate.decidedApplicationCount?.toString() ?: "Suppressed",
            "Review-duration threshold: ${aggregate.minimumCellSize}",
            Modifier.width(220.dp),
        )
        MetricCard(
            "Average review time",
            aggregate.averageReviewSeconds?.let(::formatReviewDuration) ?: "Suppressed",
            "Measured only from sufficiently large decided cells",
            Modifier.width(240.dp),
        )
    }
    DataCard {
        Column(Modifier.fillMaxWidth()) {
            TableHeader(listOf("Status" to 2f, "Count" to 1f, "Privacy" to 2f))
            aggregate.statusCounts.forEach { count ->
                TableRow {
                    TableCell(count.status.replace('_', ' '), 2f)
                    TableCell(count.value?.toString() ?: "—", 1f)
                    TableCell(
                        if (count.suppressed) "Suppressed (< ${aggregate.minimumCellSize})" else "Publishable aggregate",
                        2f,
                    )
                }
            }
        }
    }
}

@Composable
private fun RequirementVersionSection(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val versions = state.snapshot?.driverRequirementVersions
    var editing by remember(state.scope.cityId) { mutableStateOf<DriverRequirementVersionRecord?>(null) }
    var pendingTransition by remember { mutableStateOf<Pair<DriverRequirementVersionRecord, String>?>(null) }
    SectionHeading(
        "Driver requirement versions",
        "Drafts are editable. Submission and activation require a fresh backend version plus explicit review evidence.",
        action = { TextButton(onClick = { editing = NEW_REQUIREMENT_VERSION }, enabled = !state.interactionLocked) { Text("New draft") } },
    )
    if (versions == null) {
        EmptyState("Requirement versions unavailable", "The active grant or city does not expose requirement administration.")
    } else if (versions.items.isEmpty()) {
        EmptyState("No requirement versions", "Create a draft before publishing driver recruitment for this city.")
    } else {
        versions.items.forEach { version ->
            DataCard {
                Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically) {
                        Column {
                            Text("Version ${version.version}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text("Backend revision ${version.optimisticVersion} · ${version.items.size} item(s)",
                                color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                        }
                        StatusBadge(version.status)
                    }
                    Text("Effective ${compactTimestamp(version.effectiveFrom)} to ${compactTimestamp(version.effectiveUntil)}")
                    version.items.sortedBy { it.displayOrder }.forEach { item ->
                        Text("${item.displayOrder}. ${item.requirementCode} · ${item.evidenceType} · ${item.validityRuleCode}",
                            color = TaxiColors.Ink700, style = MaterialTheme.typography.bodySmall)
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                        if (version.status == "DRAFT") {
                            OutlinedButton(onClick = { editing = version }, enabled = !state.interactionLocked) { Text("Edit draft") }
                            Button(onClick = { pendingTransition = version to "IN_REVIEW" }, enabled = !state.interactionLocked) {
                                Text("Submit for review")
                            }
                        }
                        if (version.status == "IN_REVIEW") {
                            Button(onClick = { pendingTransition = version to "ACTIVE" }, enabled = !state.interactionLocked) {
                                Text("Review activation")
                            }
                        }
                    }
                }
            }
        }
        PageLimitNote(versions.items.size, versions.total)
    }
    editing?.let { selected ->
        RequirementVersionEditor(
            cityId = requireNotNull(state.scope.cityId),
            existing = selected.takeUnless { it.id == NEW_REQUIREMENT_VERSION.id },
            locked = state.interactionLocked,
            onCreate = coordinator::createDriverRequirementVersion,
            onUpdate = coordinator::updateDriverRequirementVersion,
            onClose = { editing = null },
        )
    }
    pendingTransition?.let { (version, target) ->
        RequirementTransitionDialog(
            version = version,
            target = target,
            busy = state.interactionLocked,
            onConfirm = { reason ->
                pendingTransition = null
                coordinator.transitionDriverRequirementVersion(version, target, reason)
            },
            onDismiss = { pendingTransition = null },
        )
    }
}

@Composable
private fun RequirementVersionEditor(
    cityId: String,
    existing: DriverRequirementVersionRecord?,
    locked: Boolean,
    onCreate: (DriverRequirementVersionCreateRequest) -> Unit,
    onUpdate: (DriverRequirementVersionRecord, DriverRequirementVersionUpdateRequest) -> Unit,
    onClose: () -> Unit,
) {
    var version by remember(existing?.id) { mutableStateOf(existing?.version.orEmpty()) }
    var effectiveFrom by remember(existing?.id) { mutableStateOf(existing?.effectiveFrom.orEmpty()) }
    var effectiveUntil by remember(existing?.id) { mutableStateOf(existing?.effectiveUntil.orEmpty()) }
    var items by remember(existing?.id) {
        mutableStateOf(existing?.items?.map(RequirementItemDraft::fromRecord) ?: listOf(RequirementItemDraft()))
    }
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(if (existing == null) "Create requirement draft" else "Edit requirement ${existing.version}",
                    style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                TextButton(onClick = onClose, enabled = !locked) { Text("Close") }
            }
            Text("City ID ${shortId(cityId)} · all timestamps must include a timezone (for example 2026-08-24T12:00:00Z).",
                color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
            OutlinedTextField(version, { version = it.take(64) }, Modifier.fillMaxWidth(), label = { Text("Version") },
                enabled = !locked && existing == null, singleLine = true)
            OutlinedTextField(effectiveFrom, { effectiveFrom = it.take(40) }, Modifier.fillMaxWidth(),
                label = { Text("Effective from (ISO 8601)") }, enabled = !locked, singleLine = true)
            OutlinedTextField(effectiveUntil, { effectiveUntil = it.take(40) }, Modifier.fillMaxWidth(),
                label = { Text("Effective until (optional)") }, enabled = !locked, singleLine = true)
            items.forEachIndexed { index, item ->
                RequirementItemEditor(
                    index = index,
                    item = item,
                    locked = locked,
                    onChange = { changed -> items = items.toMutableList().also { it[index] = changed } },
                    onRemove = { items = items.toMutableList().also { it.removeAt(index) } },
                    allowRemove = items.size > 1,
                )
            }
            OutlinedButton(onClick = { items = items + RequirementItemDraft(displayOrder = items.size) }, enabled = !locked) {
                Text("Add requirement item")
            }
            val inputs = items.mapNotNull(RequirementItemDraft::toInputOrNull)
            val valid = version.matches(Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")) &&
                effectiveFrom.hasTimezone() && inputs.size == items.size && inputs.isNotEmpty() &&
                inputs.map { it.requirementCode }.distinct().size == inputs.size &&
                inputs.map { it.displayOrder }.distinct().size == inputs.size
            Button(
                onClick = {
                    if (existing == null) {
                        onCreate(
                            DriverRequirementVersionCreateRequest(
                                version = version,
                                effectiveFrom = effectiveFrom,
                                effectiveUntil = effectiveUntil.ifBlank { null },
                                items = inputs,
                            ),
                        )
                    } else {
                        onUpdate(
                            existing,
                            DriverRequirementVersionUpdateRequest(
                                expectedVersion = existing.optimisticVersion,
                                effectiveFrom = effectiveFrom,
                                effectiveUntil = effectiveUntil.ifBlank { null },
                                clearEffectiveUntil = effectiveUntil.isBlank() && existing.effectiveUntil != null,
                                items = inputs,
                            ),
                        )
                    }
                },
                enabled = valid && !locked,
                modifier = Modifier.fillMaxWidth(),
            ) { Text(if (existing == null) "Create backend draft" else "Save backend draft") }
            if (!valid) Text("Complete unique codes/orders, localized copy, compatible evidence rules, and timezone-aware dates.",
                color = TaxiColors.Warning600, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun RequirementItemEditor(
    index: Int,
    item: RequirementItemDraft,
    locked: Boolean,
    onChange: (RequirementItemDraft) -> Unit,
    onRemove: () -> Unit,
    allowRemove: Boolean,
) {
    Surface(color = TaxiColors.Surface1, shape = RoundedCornerShape(TaxiRadii.Md),
        border = BorderStroke(1.dp, TaxiColors.StrokeSubtle)) {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Requirement ${index + 1}", fontWeight = FontWeight.Bold)
                if (allowRemove) TextButton(onClick = onRemove, enabled = !locked) { Text("Remove") }
            }
            OutlinedTextField(item.requirementCode, { onChange(item.copy(requirementCode = it.uppercase().take(64))) },
                Modifier.fillMaxWidth(), label = { Text("Requirement code") }, enabled = !locked, singleLine = true)
            OutlinedTextField(item.copyKey, { onChange(item.copy(copyKey = it.lowercase().take(120))) },
                Modifier.fillMaxWidth(), label = { Text("Localized copy key") }, enabled = !locked, singleLine = true)
            Text("Evidence type", style = MaterialTheme.typography.labelMedium)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                EVIDENCE_TYPES.forEach { type ->
                    OutlinedButton(
                        onClick = {
                            onChange(
                                item.copy(
                                    evidenceType = type,
                                    validityRule = DEFAULT_VALIDITY_RULE.getValue(type),
                                    referenceType = if (type == "CREDENTIAL") item.referenceType else "",
                                ),
                            )
                        },
                        enabled = !locked,
                        border = BorderStroke(if (item.evidenceType == type) 2.dp else 1.dp,
                            if (item.evidenceType == type) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
                    ) { Text(type.replace('_', ' ')) }
                }
            }
            Text("Validity rule", style = MaterialTheme.typography.labelMedium)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                VALIDITY_RULES.getValue(item.evidenceType).forEach { rule ->
                    OutlinedButton(
                        onClick = { onChange(item.copy(validityRule = rule)) },
                        enabled = !locked,
                        border = BorderStroke(if (item.validityRule == rule) 2.dp else 1.dp,
                            if (item.validityRule == rule) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
                    ) { Text(rule.replace('_', ' ')) }
                }
            }
            if (item.evidenceType == "CREDENTIAL") {
                OutlinedTextField(item.referenceType, { onChange(item.copy(referenceType = it.uppercase().take(64))) },
                    Modifier.fillMaxWidth(), label = { Text("Credential type code") }, enabled = !locked, singleLine = true)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(item.required, { onChange(item.copy(required = it)) }, enabled = !locked)
                Text("Required")
            }
            OutlinedTextField(item.displayOrder.toString(), { value ->
                value.filter(Char::isDigit).toIntOrNull()?.let { onChange(item.copy(displayOrder = it.coerceAtMost(1000))) }
            }, Modifier.fillMaxWidth(), label = { Text("Display order") }, enabled = !locked, singleLine = true)
            LocalizedCopyFields("Label", item.label, locked) { onChange(item.copy(label = it)) }
            LocalizedCopyFields("Description", item.description, locked) { onChange(item.copy(description = it)) }
        }
    }
}

@Composable
private fun LocalizedCopyFields(
    prefix: String,
    value: RecruitmentLocalizedCopy,
    locked: Boolean,
    onChange: (RecruitmentLocalizedCopy) -> Unit,
) {
    Text(prefix, style = MaterialTheme.typography.labelLarge)
    OutlinedTextField(value.en, { onChange(value.copy(en = it.take(500))) }, Modifier.fillMaxWidth(),
        label = { Text("$prefix · English") }, enabled = !locked)
    OutlinedTextField(value.fr, { onChange(value.copy(fr = it.take(500))) }, Modifier.fillMaxWidth(),
        label = { Text("$prefix · Français") }, enabled = !locked)
    OutlinedTextField(value.ar, { onChange(value.copy(ar = it.take(500))) }, Modifier.fillMaxWidth(),
        label = { Text("$prefix · العربية") }, enabled = !locked)
}

@Composable
private fun RequirementTransitionDialog(
    version: DriverRequirementVersionRecord,
    target: String,
    busy: Boolean,
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    var reason by remember(version.id, target) { mutableStateOf("") }
    var confirmed by remember(version.id, target) { mutableStateOf(false) }
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(if (target == "ACTIVE") "Activate requirement version?" else "Submit requirement version?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text("Version ${version.version}, backend revision ${version.optimisticVersion}, ${version.items.size} item(s).")
                Text("This command is audited and may replace the city's previous active requirements.", color = TaxiColors.Warning600)
                OutlinedTextField(reason, { reason = it.take(240) }, Modifier.fillMaxWidth(), label = { Text("Review reason") })
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(confirmed, { confirmed = it }, enabled = !busy)
                    Text("I reviewed the city, effective period, and complete item set.")
                }
            }
        },
        confirmButton = {
            Button(onClick = { onConfirm(reason) }, enabled = !busy && confirmed && reason.trim().length >= 3) {
                Text(if (target == "ACTIVE") "Confirm activation" else "Confirm submission")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}

@Composable
private fun DriverReviewSection(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val queue = state.snapshot?.driverApplications
    SectionHeading("Scoped application queue", "Oldest submitted applications appear first; every detail read is backend-scoped.")
    if (queue == null || queue.items.isEmpty()) {
        EmptyState("No applications in this city queue", "Draft, withdrawn, or out-of-scope records may be intentionally absent.")
    } else {
        DataCard(tableMinWidth = 900.dp) {
            Column(Modifier.fillMaxWidth()) {
                TableHeader(listOf("Applicant" to 1.5f, "City" to 1f, "Status" to 1.3f, "Submitted" to 1.4f, "Action" to 1f))
                queue.items.forEach { application ->
                    TableRow(selected = application.id == state.selectedDriverApplication?.application?.id) {
                        TableCell(application.displayName, 1.5f, shortId(application.driverId))
                        TableCell(application.cityCode, 1f, "requirements ${application.requirementVersion}")
                        Box(Modifier.weight(1.3f)) { StatusBadge(application.status) }
                        TableCell(compactTimestamp(application.submittedAt), 1.4f)
                        Box(Modifier.weight(1f)) {
                            OutlinedButton(onClick = { coordinator.selectDriverApplication(application.id) },
                                enabled = !state.interactionLocked) { Text("Review") }
                        }
                    }
                }
            }
        }
        PageLimitNote(queue.items.size, queue.total)
    }
    state.selectedDriverApplication?.let { detail -> DriverApplicationReview(detail, state, coordinator) }
}

@Composable
private fun DriverApplicationReview(
    detail: OperationsDriverApplicationDetail,
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val application = detail.application
    HorizontalDivider(color = TaxiColors.StrokeSubtle)
    SectionHeading("Application review", "Personally identifying data below is available only for the current scoped review task.")
    Surface(color = TaxiColors.Warning100, shape = RoundedCornerShape(TaxiRadii.Md)) {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
            Text("Restricted applicant data", fontWeight = FontWeight.Bold, color = TaxiColors.Warning600)
            Text("${detail.applicantDisplayName} · ${detail.applicantEmail ?: "no email"} · ${detail.applicantPhoneNumber ?: "no phone"}")
            Text("Do not copy these fields into audit reasons, analytics, or applicant-safe messages.", style = MaterialTheme.typography.bodySmall)
        }
    }
    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
        StatusBadge(application.status)
        Text("Application version ${application.optimisticVersion} · submission ${application.submissionRevision}")
    }
    application.requirements.sortedBy { it.displayOrder }.forEach { requirement ->
        val answer = application.answers.firstOrNull { it.requirementItemId == requirement.id }
        val evidence = application.evidence.firstOrNull { it.requirementItemId == requirement.id }
        DataCard {
            Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(requirement.localizedLabel.en, fontWeight = FontWeight.Bold)
                    StatusBadge(evidence?.status ?: if (requirement.id in application.missingRequiredItemIds) "MISSING" else "PRESENT")
                }
                Text("${requirement.requirementCode} · ${requirement.evidenceType} · ${requirement.validityRuleCode}",
                    color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                answer?.let {
                    Text("Answer: ${it.textValue ?: it.dateValue ?: it.booleanValue?.toString() ?: "—"}")
                }
                evidence?.let {
                    Text("Evidence reference: ${shortId(it.vehicleId ?: it.credentialId ?: it.profileId ?: it.documentId)}")
                }
                application.documents.filter { it.requirementItemId == requirement.id }.forEach { document ->
                    Surface(color = TaxiColors.Surface1, shape = RoundedCornerShape(TaxiRadii.Sm)) {
                        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Sm)) {
                            Text("Document ${shortId(document.id)} · ${document.scanStatus}")
                            Text("${document.mediaType}, ${document.byteSize} bytes", style = MaterialTheme.typography.bodySmall)
                            OutlinedButton(
                                onClick = {
                                    coordinator.downloadDriverApplicationDocument(application.id, document.id)
                                },
                                enabled = canDownloadProtectedDocument(
                                    browserAvailable = browserProtectedDocumentDownloadAvailable,
                                    scanStatus = document.scanStatus,
                                    interactionLocked = state.interactionLocked,
                                ),
                            ) { Text("Download protected copy") }
                            Text(
                                if (browserProtectedDocumentDownloadAvailable) {
                                    "Requires recent MFA. The audited response is no-store and uses an opaque filename."
                                } else {
                                    "Protected download is unavailable in this browser build."
                                },
                                color = TaxiColors.Warning600,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }
        }
    }
    if (detail.decisions.isNotEmpty()) {
        Text("Decision history", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        detail.decisions.forEach { decision ->
            Text("${compactTimestamp(decision.createdAt)} · ${decision.decision} · ${decision.reasonCode} · ${decision.applicantSafeMessage}")
        }
    }
    CityAuthorizationReview(application, state.interactionLocked, coordinator)
    DriverDecisionForm(detail, state.interactionLocked, coordinator::decideDriverApplication)
}

internal fun canDownloadProtectedDocument(
    browserAvailable: Boolean,
    scanStatus: String,
    interactionLocked: Boolean,
): Boolean = browserAvailable && scanStatus == "CLEAN" && !interactionLocked

@Composable
private fun DriverDecisionForm(
    detail: OperationsDriverApplicationDetail,
    locked: Boolean,
    onDecision: (DriverApplicationDecisionRequest) -> Unit,
) {
    val application = detail.application
    val decisions = when (application.status) {
        "SUBMITTED" -> listOf("START_REVIEW")
        "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED" -> listOf("REQUEST_ADDITIONAL_INFORMATION", "APPROVE", "REJECT")
        else -> emptyList()
    }
    if (decisions.isEmpty()) {
        Surface(color = TaxiColors.Surface2, shape = RoundedCornerShape(TaxiRadii.Md)) {
            Text("No review transition is available from ${application.status}.", Modifier.fillMaxWidth().padding(TaxiSpacing.Md))
        }
        return
    }
    var decision by remember(application.id, application.optimisticVersion) { mutableStateOf(decisions.first()) }
    val reasons = DECISION_REASONS.getValue(decision)
    var reason by remember(decision) { mutableStateOf(reasons.first()) }
    var message by remember(application.id, application.optimisticVersion) { mutableStateOf("") }
    var onDemand by remember(application.id, application.optimisticVersion) { mutableStateOf(true) }
    var fixedRoute by remember(application.id, application.optimisticVersion) { mutableStateOf(false) }
    var scheduled by remember(application.id, application.optimisticVersion) { mutableStateOf(false) }
    var vehicleId by remember(application.id, application.optimisticVersion) { mutableStateOf<String?>(null) }
    var validUntil by remember(application.id, application.optimisticVersion) { mutableStateOf("") }
    var confirmed by remember(application.id, application.optimisticVersion) { mutableStateOf(false) }
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Text("Record a decision", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("A safe message is shown to the applicant. Reviewer identity remains operations-only.", color = TaxiColors.Ink500)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                decisions.forEach { candidate ->
                    OutlinedButton(
                        onClick = { decision = candidate; reason = DECISION_REASONS.getValue(candidate).first(); confirmed = false },
                        enabled = !locked,
                        border = BorderStroke(if (candidate == decision) 2.dp else 1.dp,
                            if (candidate == decision) TaxiColors.Accent500 else TaxiColors.StrokeSubtle),
                    ) { Text(candidate.replace('_', ' ')) }
                }
            }
            ScopeMenu(
                label = "Reason",
                selected = reason.replace('_', ' '),
                options = DECISION_REASONS.getValue(decision).map { ScopeOption(it, it.replace('_', ' ')) },
                enabled = !locked,
                onSelected = { selected -> selected?.let { reason = it } },
            )
            OutlinedTextField(message, { message = it.take(500) }, Modifier.fillMaxWidth(),
                label = { Text("Applicant-safe message") }, enabled = !locked)
            if (decision == "APPROVE") {
                Text("Authorized services", fontWeight = FontWeight.Bold)
                ServiceCheckbox("On-demand", onDemand, !locked) { onDemand = it }
                ServiceCheckbox("Fixed route", fixedRoute, !locked) { fixedRoute = it }
                ServiceCheckbox("Scheduled", scheduled, !locked) { scheduled = it }
                val vehicleChoices = application.evidence.mapNotNull { it.vehicleId }.distinct()
                ScopeMenu(
                    label = "Authorized vehicle",
                    selected = shortId(vehicleId),
                    options = listOf(ScopeOption(null, "No vehicle binding")) + vehicleChoices.map { ScopeOption(it, shortId(it)) },
                    enabled = !locked,
                    onSelected = { vehicleId = it },
                )
                OutlinedTextField(validUntil, { validUntil = it.take(40) }, Modifier.fillMaxWidth(),
                    label = { Text("Authorization expiry (optional ISO 8601)") }, enabled = !locked)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(confirmed, { confirmed = it }, enabled = !locked)
                Text("I reviewed the current requirement version, evidence, city, reason, and applicant-safe message.")
            }
            val serviceTypes = buildList {
                if (onDemand) add("ON_DEMAND")
                if (fixedRoute) add("FIXED_ROUTE")
                if (scheduled) add("SCHEDULED")
            }
            Button(
                onClick = {
                    onDecision(
                        DriverApplicationDecisionRequest(
                            expectedVersion = application.optimisticVersion,
                            decision = decision,
                            reasonCode = reason,
                            applicantSafeMessage = message.trim(),
                            authorizedServiceTypes = serviceTypes.takeIf { decision == "APPROVE" },
                            authorizedVehicleId = vehicleId.takeIf { decision == "APPROVE" },
                            authorizationValidUntil = validUntil.trim().ifBlank { null }.takeIf { decision == "APPROVE" },
                        ),
                    )
                },
                enabled = !locked && confirmed && message.trim().length >= 3 &&
                    (decision != "APPROVE" || serviceTypes.isNotEmpty()) &&
                    (validUntil.isBlank() || validUntil.hasTimezone()),
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Confirm backend decision") }
        }
    }
}

@Composable
private fun ServiceCheckbox(label: String, checked: Boolean, enabled: Boolean, onChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked, onChange, enabled = enabled)
        Text(label)
    }
}

internal data class RequirementItemDraft(
    val requirementCode: String = "PROFILE_OWNERSHIP",
    val evidenceType: String = "PROFILE",
    val required: Boolean = true,
    val validityRule: String = "PROFILE_OWNED",
    val referenceType: String = "",
    val displayOrder: Int = 0,
    val copyKey: String = "driver.requirement.profile",
    val label: RecruitmentLocalizedCopy = RecruitmentLocalizedCopy("Profile ownership", "Profil du conducteur", "ملكية الملف الشخصي"),
    val description: RecruitmentLocalizedCopy = RecruitmentLocalizedCopy(
        "Confirm that this application belongs to the signed-in profile.",
        "Confirmer que cette candidature appartient au profil connecté.",
        "تأكيد أن هذا الطلب يخص الملف الشخصي المسجل.",
    ),
) {
    fun toInputOrNull(): DriverRequirementItemInput? {
        if (!requirementCode.matches(Regex("^[A-Z][A-Z0-9_]{1,63}$"))) return null
        if (!copyKey.matches(Regex("^[a-z][a-z0-9_.-]{2,119}$"))) return null
        if (displayOrder !in 0..1000 || listOf(label.en, label.fr, label.ar, description.en, description.fr, description.ar).any(String::isBlank)) return null
        if (validityRule !in VALIDITY_RULES.getValue(evidenceType)) return null
        if (evidenceType == "CREDENTIAL" && !referenceType.matches(Regex("^[A-Z][A-Z0-9_]{1,63}$"))) return null
        return DriverRequirementItemInput(
            requirementCode = requirementCode,
            evidenceType = evidenceType,
            required = required,
            validityRuleCode = validityRule,
            referenceTypeCode = referenceType.takeIf { evidenceType == "CREDENTIAL" },
            displayOrder = displayOrder,
            localizedCopyKey = copyKey,
            localizedLabel = label,
            localizedDescription = description,
        )
    }

    companion object {
        fun fromRecord(record: DriverRequirementItemRecord) = RequirementItemDraft(
            requirementCode = record.requirementCode,
            evidenceType = record.evidenceType,
            required = record.required,
            validityRule = record.validityRuleCode,
            referenceType = record.referenceTypeCode.orEmpty(),
            displayOrder = record.displayOrder,
            copyKey = record.localizedCopyKey,
            label = record.localizedLabel,
            description = record.localizedDescription,
        )
    }
}

private val NEW_REQUIREMENT_VERSION = DriverRequirementVersionRecord(
    id = "new",
    cityId = "new",
    version = "",
    status = "DRAFT",
    effectiveFrom = "",
    optimisticVersion = 1,
    items = emptyList(),
    createdAt = "",
    updatedAt = "",
)

private val EVIDENCE_TYPES = listOf("PROFILE", "VEHICLE", "CREDENTIAL", "DOCUMENT", "BOOLEAN", "DATE", "TEXT")

private val DEFAULT_VALIDITY_RULE = mapOf(
    "PROFILE" to "PROFILE_OWNED",
    "VEHICLE" to "VEHICLE_VERIFIED",
    "CREDENTIAL" to "CREDENTIAL_VERIFIED",
    "DOCUMENT" to "DOCUMENT_SCANNED_CLEAN",
    "BOOLEAN" to "BOOLEAN_TRUE",
    "DATE" to "DATE_NOT_FUTURE",
    "TEXT" to "TEXT_PRESENT",
)

private val VALIDITY_RULES = mapOf(
    "PROFILE" to listOf("PROFILE_OWNED"),
    "VEHICLE" to listOf("VEHICLE_OWNED", "VEHICLE_VERIFIED"),
    "CREDENTIAL" to listOf("CREDENTIAL_OWNED", "CREDENTIAL_VERIFIED", "CREDENTIAL_UNEXPIRED"),
    "DOCUMENT" to listOf("DOCUMENT_SCANNED_CLEAN"),
    "BOOLEAN" to listOf("BOOLEAN_TRUE"),
    "DATE" to listOf("DATE_NOT_FUTURE"),
    "TEXT" to listOf("TEXT_PRESENT"),
)

private val DECISION_REASONS = mapOf(
    "START_REVIEW" to listOf("MANUAL_REVIEW_STARTED"),
    "REQUEST_ADDITIONAL_INFORMATION" to listOf(
        "MISSING_OR_INVALID_EVIDENCE", "CREDENTIAL_NOT_VALID", "VEHICLE_NOT_ELIGIBLE", "JURISDICTION_REQUIREMENT_NOT_MET",
    ),
    "APPROVE" to listOf("REQUIREMENTS_CONFIRMED", "LEGACY_COMPATIBILITY_APPROVAL"),
    "REJECT" to listOf("CREDENTIAL_NOT_VALID", "VEHICLE_NOT_ELIGIBLE", "JURISDICTION_REQUIREMENT_NOT_MET", "DUPLICATE_APPLICATION"),
)

internal fun String.hasTimezone(): Boolean = endsWith("Z") || drop(10).contains('+') || drop(10).contains('-')

private fun formatReviewDuration(seconds: Double): String = when {
    seconds < 3600 -> "${(seconds / 60).toInt()} min"
    seconds < 86_400 -> "${(seconds / 3600).toInt()} hr"
    else -> "${(seconds / 86_400).toInt()} days"
}
