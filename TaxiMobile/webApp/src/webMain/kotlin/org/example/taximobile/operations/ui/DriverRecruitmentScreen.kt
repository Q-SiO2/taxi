package org.example.taximobile.operations.ui

import org.example.taximobile.feature.ui.theme.TaxiTheme
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
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.ui.text.intl.Locale
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import org.jetbrains.compose.resources.stringResource
import taximobile.shared.generated.resources.*
import org.example.taximobile.feature.app.driverApplicationStatusResource
import org.example.taximobile.feature.ui.text.ltrIsolate
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val snapshot = state.snapshot ?: return
    val permissions = state.session?.permissions.orEmpty()
    val city = snapshot.cities.items.firstOrNull { it.id == state.scope.cityId }
    ScreenColumn {
        SectionHeading(
            title = stringResource(Res.string.web_recruitment_title),
            supportingText = stringResource(Res.string.web_recruitment_intro),
        )
        if (city == null) {
            EmptyState(stringResource(Res.string.web_recruitment_choose_city),
                stringResource(Res.string.web_recruitment_select_city_help))
            return@ScreenColumn
        }
        Surface(
            color = taxiColors.Info100,
            shape = RoundedCornerShape(taxiRadii.Md),
            border = BorderStroke(1.dp, taxiColors.Info600.copy(alpha = 0.25f)),
        ) {
            Text(
                stringResource(Res.string.web_recruitment_city, city.localizedName.preferred(Locale.current.language)),
                Modifier.fillMaxWidth().padding(TaxiSpacing.Md),
                color = taxiColors.Info600,
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
        stringResource(Res.string.web_onboarding_funnel),
        stringResource(Res.string.web_onboarding_privacy_help),
    )
    if (aggregate == null) {
        EmptyState(stringResource(Res.string.web_onboarding_unavailable),
            stringResource(Res.string.web_onboarding_unavailable_help))
        return
    }
    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
        MetricCard(
            stringResource(Res.string.web_total_applications),
            aggregate.totalApplications?.let { ltrIsolate(it.toString()) }
                ?: stringResource(Res.string.web_privacy_hidden),
            if (aggregate.totalSuppressed) stringResource(Res.string.web_privacy_below_count, aggregate.minimumCellSize)
                else stringResource(Res.string.web_all_statuses),
            Modifier.width(220.dp),
        )
        MetricCard(
            stringResource(Res.string.web_decided_applications),
            aggregate.decidedApplicationCount?.let { ltrIsolate(it.toString()) }
                ?: stringResource(Res.string.web_privacy_hidden),
            stringResource(Res.string.web_review_minimum_count, aggregate.minimumCellSize),
            Modifier.width(220.dp),
        )
        MetricCard(
            stringResource(Res.string.web_average_review_time),
            aggregate.averageReviewSeconds?.let { seconds ->
                when {
                    seconds < 3600 -> stringResource(Res.string.web_review_minutes, (seconds / 60).toInt())
                    seconds < 86_400 -> stringResource(Res.string.web_review_hours, (seconds / 3600).toInt())
                    else -> stringResource(Res.string.web_review_days, (seconds / 86_400).toInt())
                }
            }
                ?: stringResource(Res.string.web_privacy_hidden),
            stringResource(Res.string.web_review_private_help),
            Modifier.width(240.dp),
        )
    }
    DataCard {
        Column(Modifier.fillMaxWidth()) {
            TableHeader(listOf(stringResource(Res.string.web_table_status) to 2f,
                stringResource(Res.string.web_table_count) to 1f,
                stringResource(Res.string.web_table_privacy) to 2f))
            aggregate.statusCounts.forEach { count ->
                TableRow {
                    TableCell(stringResource(driverApplicationStatusResource(count.status)), 2f)
                    TableCell(count.value?.let { ltrIsolate(it.toString()) } ?: "—", 1f)
                    TableCell(
                        if (count.suppressed) stringResource(Res.string.web_privacy_hidden_threshold, aggregate.minimumCellSize)
                            else stringResource(Res.string.web_privacy_visible_total),
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
    val taxiColors = TaxiTheme.colors
    val versions = state.snapshot?.driverRequirementVersions
    var editing by remember(state.scope.cityId) { mutableStateOf<DriverRequirementVersionRecord?>(null) }
    var pendingTransition by remember { mutableStateOf<Pair<DriverRequirementVersionRecord, String>?>(null) }
    SectionHeading(
        stringResource(Res.string.web_req_versions),
        stringResource(Res.string.web_req_versions_help),
        action = { TextButton(onClick = { editing = NEW_REQUIREMENT_VERSION }, enabled = !state.interactionLocked) { Text(stringResource(Res.string.web_req_new_draft)) } },
    )
    if (versions == null) {
        EmptyState(stringResource(Res.string.web_req_unavailable), stringResource(Res.string.web_req_unavailable_help))
    } else if (versions.items.isEmpty()) {
        EmptyState(stringResource(Res.string.web_req_empty), stringResource(Res.string.web_req_empty_help))
    } else {
        versions.items.forEach { version ->
            DataCard {
                Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically) {
                        Column {
                            Text(stringResource(Res.string.web_req_version, ltrIsolate(version.version)), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                            Text(stringResource(Res.string.web_req_revision_items, version.optimisticVersion, version.items.size),
                                color = taxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                        }
                        StatusBadge(version.status, label = recruitmentLabel(version.status))
                    }
                    Text(stringResource(Res.string.web_req_period, ltrIsolate(version.effectiveFrom),
                        version.effectiveUntil?.let(::ltrIsolate) ?: stringResource(Res.string.web_req_no_end)))
                    version.items.sortedBy { it.displayOrder }.forEach { item ->
                        Text("${ltrIsolate("${item.displayOrder}. ${item.requirementCode}")} · ${recruitmentLabel(item.evidenceType)} · ${recruitmentLabel(item.validityRuleCode)}",
                            color = taxiColors.Ink700, style = MaterialTheme.typography.bodySmall)
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                        if (version.status == "DRAFT") {
                            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { editing = version }, enabled = !state.interactionLocked) { Text(stringResource(Res.string.web_req_edit_draft)) }
                            Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { pendingTransition = version to "IN_REVIEW" }, enabled = !state.interactionLocked) {
                                Text(stringResource(Res.string.web_req_submit_review))
                            }
                        }
                        if (version.status == "IN_REVIEW") {
                            Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { pendingTransition = version to "ACTIVE" }, enabled = !state.interactionLocked) {
                                Text(stringResource(Res.string.web_req_review_activation))
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
    val taxiColors = TaxiTheme.colors
    val codeTextStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr)
    var version by remember(existing?.id) { mutableStateOf(existing?.version.orEmpty()) }
    var effectiveFrom by remember(existing?.id) { mutableStateOf(existing?.effectiveFrom.orEmpty()) }
    var effectiveUntil by remember(existing?.id) { mutableStateOf(existing?.effectiveUntil.orEmpty()) }
    var items by remember(existing?.id) {
        mutableStateOf(existing?.items?.map(RequirementItemDraft::fromRecord) ?: listOf(RequirementItemDraft()))
    }
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(if (existing == null) stringResource(Res.string.web_req_create_title) else stringResource(Res.string.web_req_edit_title, ltrIsolate(existing.version)),
                    style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                TextButton(onClick = onClose, enabled = !locked) { Text(stringResource(Res.string.web_recruit_close)) }
            }
            Text(stringResource(Res.string.web_req_date_help, ltrIsolate(shortId(cityId)), ltrIsolate("2026-08-24T12:00:00Z")),
                color = taxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
            OutlinedTextField(version, { version = it.take(64) }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.web_req_version_label)) },
                enabled = !locked && existing == null, singleLine = true, textStyle = codeTextStyle)
            OutlinedTextField(effectiveFrom, { effectiveFrom = it.take(40) }, Modifier.fillMaxWidth(),
                label = { Text(stringResource(Res.string.web_req_from)) }, enabled = !locked, singleLine = true, textStyle = codeTextStyle)
            OutlinedTextField(effectiveUntil, { effectiveUntil = it.take(40) }, Modifier.fillMaxWidth(),
                label = { Text(stringResource(Res.string.web_req_until)) }, enabled = !locked, singleLine = true, textStyle = codeTextStyle)
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
            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { items = items + RequirementItemDraft(displayOrder = items.size) }, enabled = !locked) {
                Text(stringResource(Res.string.web_req_add_item))
            }
            val inputs = items.mapNotNull(RequirementItemDraft::toInputOrNull)
            val valid = version.matches(Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")) &&
                effectiveFrom.hasTimezone() && inputs.size == items.size && inputs.isNotEmpty() &&
                inputs.map { it.requirementCode }.distinct().size == inputs.size &&
                inputs.map { it.displayOrder }.distinct().size == inputs.size
            Button(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
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
            ) { Text(if (existing == null) stringResource(Res.string.web_req_create) else stringResource(Res.string.web_req_save)) }
            if (!valid) Text(stringResource(Res.string.web_req_invalid),
                color = taxiColors.Warning600, style = MaterialTheme.typography.bodySmall)
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val codeTextStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr)
    Surface(color = taxiColors.Surface1, shape = RoundedCornerShape(taxiRadii.Md),
        border = BorderStroke(1.dp, taxiColors.StrokeSubtle)) {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(stringResource(Res.string.web_req_item, index + 1), fontWeight = FontWeight.Bold)
                if (allowRemove) TextButton(onClick = onRemove, enabled = !locked) { Text(stringResource(Res.string.web_recruit_remove)) }
            }
            OutlinedTextField(item.requirementCode, { onChange(item.copy(requirementCode = it.uppercase().take(64))) },
                Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.web_req_code)) }, enabled = !locked, singleLine = true, textStyle = codeTextStyle)
            OutlinedTextField(item.copyKey, { onChange(item.copy(copyKey = it.lowercase().take(120))) },
                Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.web_req_copy_key)) }, enabled = !locked, singleLine = true, textStyle = codeTextStyle)
            Text(stringResource(Res.string.web_req_evidence_type), style = MaterialTheme.typography.labelMedium)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                EVIDENCE_TYPES.forEach { type ->
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
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
                            if (item.evidenceType == type) taxiColors.Accent500 else taxiColors.StrokeSubtle),
                    ) { Text(recruitmentLabel(type)) }
                }
            }
            Text(stringResource(Res.string.web_req_validity_rule), style = MaterialTheme.typography.labelMedium)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                VALIDITY_RULES.getValue(item.evidenceType).forEach { rule ->
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = { onChange(item.copy(validityRule = rule)) },
                        enabled = !locked,
                        border = BorderStroke(if (item.validityRule == rule) 2.dp else 1.dp,
                            if (item.validityRule == rule) taxiColors.Accent500 else taxiColors.StrokeSubtle),
                    ) { Text(recruitmentLabel(rule)) }
                }
            }
            if (item.evidenceType == "CREDENTIAL") {
                OutlinedTextField(item.referenceType, { onChange(item.copy(referenceType = it.uppercase().take(64))) },
                    Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.web_req_credential_code)) }, enabled = !locked, singleLine = true, textStyle = codeTextStyle)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(item.required, { onChange(item.copy(required = it)) }, enabled = !locked)
                Text(stringResource(Res.string.web_req_required))
            }
            OutlinedTextField(item.displayOrder.toString(), { value ->
                value.filter(Char::isDigit).toIntOrNull()?.let { onChange(item.copy(displayOrder = it.coerceAtMost(1000))) }
            }, Modifier.fillMaxWidth(), label = { Text(stringResource(Res.string.web_req_order)) }, enabled = !locked, singleLine = true, textStyle = codeTextStyle)
            LocalizedCopyFields(stringResource(Res.string.web_req_label), item.label, locked) { onChange(item.copy(label = it)) }
            LocalizedCopyFields(stringResource(Res.string.web_req_description), item.description, locked) { onChange(item.copy(description = it)) }
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
        label = { Text(stringResource(Res.string.web_req_locale_field, prefix, "English")) }, enabled = !locked, textStyle = recruitmentTextStyle(value.en))
    OutlinedTextField(value.fr, { onChange(value.copy(fr = it.take(500))) }, Modifier.fillMaxWidth(),
        label = { Text(stringResource(Res.string.web_req_locale_field, prefix, "Français")) }, enabled = !locked, textStyle = recruitmentTextStyle(value.fr))
    OutlinedTextField(value.ar, { onChange(value.copy(ar = it.take(500))) }, Modifier.fillMaxWidth(),
        label = { Text(stringResource(Res.string.web_req_locale_field, prefix, "العربية")) }, enabled = !locked, textStyle = recruitmentTextStyle(value.ar))
}

@Composable
private fun RequirementTransitionDialog(
    version: DriverRequirementVersionRecord,
    target: String,
    busy: Boolean,
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val taxiColors = TaxiTheme.colors
    var reason by remember(version.id, target) { mutableStateOf("") }
    var confirmed by remember(version.id, target) { mutableStateOf(false) }
    AlertDialog(
        shape = RoundedCornerShape(TaxiTheme.radii.Lg),
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(if (target == "ACTIVE") stringResource(Res.string.web_req_activate_question) else stringResource(Res.string.web_req_submit_question)) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(stringResource(Res.string.web_req_version, ltrIsolate(version.version)))
                Text(stringResource(Res.string.web_req_revision_items, version.optimisticVersion, version.items.size))
                Text(stringResource(Res.string.web_req_city_id, ltrIsolate(shortId(version.cityId))))
                Text(stringResource(Res.string.web_req_period, ltrIsolate(version.effectiveFrom),
                    version.effectiveUntil?.let(::ltrIsolate) ?: stringResource(Res.string.web_req_no_end)))
                Text(stringResource(Res.string.web_req_replace_notice), color = taxiColors.Warning600)
                OutlinedTextField(reason, { reason = it.take(240) }, Modifier.fillMaxWidth(),
                    label = { Text(stringResource(Res.string.web_recruit_review_reason)) }, textStyle = recruitmentTextStyle(reason))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(confirmed, { confirmed = it }, enabled = !busy)
                    Text(stringResource(Res.string.web_req_review_check))
                }
            }
        },
        confirmButton = {
            Button(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { onConfirm(reason) }, enabled = !busy && confirmed && reason.trim().length >= 3) {
                Text(if (target == "ACTIVE") stringResource(Res.string.web_req_confirm_activation) else stringResource(Res.string.web_req_confirm_submission))
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text(stringResource(Res.string.web_cancel)) } },
    )
}

@Composable
private fun DriverReviewSection(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val queue = state.snapshot?.driverApplications
    SectionHeading(stringResource(Res.string.web_recruit_queue), stringResource(Res.string.web_recruit_queue_help))
    if (queue == null || queue.items.isEmpty()) {
        EmptyState(stringResource(Res.string.web_recruit_empty_queue), stringResource(Res.string.web_recruit_empty_queue_help))
    } else {
        DataCard(tableMinWidth = 900.dp) {
            Column(Modifier.fillMaxWidth()) {
                TableHeader(listOf(stringResource(Res.string.web_recruit_applicant) to 1.5f, stringResource(Res.string.web_recruit_city) to 1f, stringResource(Res.string.web_table_status) to 1.3f, stringResource(Res.string.web_recruit_submitted) to 1.4f, stringResource(Res.string.web_recruit_action) to 1f))
                queue.items.forEach { application ->
                    TableRow(selected = application.id == state.selectedDriverApplication?.application?.id) {
                        TableCell(application.displayName, 1.5f, ltrIsolate(shortId(application.driverId)))
                        TableCell(application.cityName.preferred(Locale.current.language), 1f, stringResource(Res.string.requirement_version_value, ltrIsolate(application.requirementVersion)))
                        Box(Modifier.weight(1.3f)) { StatusBadge(application.status, label = recruitmentLabel(application.status)) }
                        TableCell(ltrIsolate(compactTimestamp(application.submittedAt)), 1.4f)
                        Box(Modifier.weight(1f)) {
                            OutlinedButton(shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),onClick = { coordinator.selectDriverApplication(application.id) },
                                enabled = !state.interactionLocked) { Text(stringResource(Res.string.web_recruit_review)) }
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val application = detail.application
    HorizontalDivider(color = taxiColors.StrokeSubtle)
    SectionHeading(stringResource(Res.string.web_recruit_review_title), stringResource(Res.string.web_recruit_review_help))
    Surface(color = taxiColors.Warning100, shape = RoundedCornerShape(taxiRadii.Md)) {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
            Text(stringResource(Res.string.web_recruit_private_data), fontWeight = FontWeight.Bold, color = taxiColors.Warning600)
            val person = stringResource(Res.string.web_recruit_person, detail.applicantDisplayName,
                detail.applicantEmail?.let(::ltrIsolate) ?: stringResource(Res.string.web_recruit_no_email),
                detail.applicantPhoneNumber?.let(::ltrIsolate) ?: stringResource(Res.string.web_recruit_no_phone))
            Text(person, style = recruitmentTextStyle(person))
            Text(stringResource(Res.string.web_recruit_private_notice), style = MaterialTheme.typography.bodySmall)
        }
    }
    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
        StatusBadge(application.status, label = recruitmentLabel(application.status))
        Text(stringResource(Res.string.web_recruit_app_revision, application.optimisticVersion, application.submissionRevision))
    }
    application.requirements.sortedBy { it.displayOrder }.forEach { requirement ->
        val answer = application.answers.firstOrNull { it.requirementItemId == requirement.id }
        val evidence = application.evidence.firstOrNull { it.requirementItemId == requirement.id }
        DataCard {
            Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    val label = requirement.localizedLabel.inLanguage(Locale.current.language)
                    Text(label, fontWeight = FontWeight.Bold, style = recruitmentTextStyle(label))
                    val evidenceStatus = evidence?.status ?: if (requirement.id in application.missingRequiredItemIds) "MISSING" else "PRESENT"
                    StatusBadge(evidenceStatus, label = recruitmentLabel(evidenceStatus))
                }
                Text("${ltrIsolate(requirement.requirementCode)} · ${recruitmentLabel(requirement.evidenceType)} · ${recruitmentLabel(requirement.validityRuleCode)}",
                    color = taxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                answer?.let {
                    val answerText = it.textValue ?: it.dateValue?.let(::ltrIsolate) ?: it.booleanValue?.let { value ->
                        stringResource(if (value) Res.string.web_recruit_yes else Res.string.web_recruit_no)
                    } ?: "—"
                    Text(stringResource(Res.string.web_recruit_answer, answerText), style = recruitmentTextStyle(answerText))
                }
                evidence?.let {
                    Text(stringResource(Res.string.web_recruit_evidence_reference, ltrIsolate(shortId(it.vehicleId ?: it.credentialId ?: it.profileId ?: it.documentId))))
                }
                application.documents.filter { it.requirementItemId == requirement.id }.forEach { document ->
                    Surface(color = taxiColors.Surface1, shape = RoundedCornerShape(taxiRadii.Sm)) {
                        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Sm)) {
                            Text(stringResource(Res.string.web_recruit_document, ltrIsolate(shortId(document.id)), recruitmentLabel(document.scanStatus)))
                            Text(stringResource(Res.string.web_recruit_document_size, ltrIsolate(document.mediaType), ltrIsolate(document.byteSize.toString())), style = MaterialTheme.typography.bodySmall)
                            OutlinedButton(
                                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                                onClick = {
                                    coordinator.downloadDriverApplicationDocument(application.id, document.id)
                                },
                                enabled = canDownloadProtectedDocument(
                                    browserAvailable = browserProtectedDocumentDownloadAvailable,
                                    scanStatus = document.scanStatus,
                                    interactionLocked = state.interactionLocked,
                                ),
                            ) { Text(stringResource(Res.string.web_recruit_download)) }
                            Text(
                                if (browserProtectedDocumentDownloadAvailable) {
                                    stringResource(Res.string.web_recruit_download_help)
                                } else {
                                    stringResource(Res.string.web_recruit_download_unavailable)
                                },
                                color = taxiColors.Warning600,
                                style = MaterialTheme.typography.bodySmall,
                            )
                        }
                    }
                }
            }
        }
    }
    if (detail.decisions.isNotEmpty()) {
        Text(stringResource(Res.string.web_recruit_history), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
        detail.decisions.forEach { decision ->
            val history = stringResource(Res.string.web_recruit_history_row, ltrIsolate(decision.createdAt),
                recruitmentLabel(decision.decision), recruitmentLabel(decision.reasonCode), decision.applicantSafeMessage)
            Text(history, style = recruitmentTextStyle(history))
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
    val taxiColors = TaxiTheme.colors
    val taxiRadii = TaxiTheme.radii
    val application = detail.application
    val decisions = when (application.status) {
        "SUBMITTED" -> listOf("START_REVIEW")
        "UNDER_REVIEW", "ADDITIONAL_INFORMATION_REQUIRED" -> listOf("REQUEST_ADDITIONAL_INFORMATION", "APPROVE", "REJECT")
        else -> emptyList()
    }
    if (decisions.isEmpty()) {
        Surface(color = taxiColors.Surface2, shape = RoundedCornerShape(taxiRadii.Md)) {
            Text(stringResource(Res.string.web_recruit_no_transition, recruitmentLabel(application.status)), Modifier.fillMaxWidth().padding(TaxiSpacing.Md))
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
            Text(stringResource(Res.string.web_recruit_decision_title), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text(stringResource(Res.string.web_recruit_decision_help), color = taxiColors.Ink500)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                decisions.forEach { candidate ->
                    OutlinedButton(
                        shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
                        onClick = { decision = candidate; reason = DECISION_REASONS.getValue(candidate).first(); confirmed = false },
                        enabled = !locked,
                        border = BorderStroke(if (candidate == decision) 2.dp else 1.dp,
                            if (candidate == decision) taxiColors.Accent500 else taxiColors.StrokeSubtle),
                    ) { Text(recruitmentLabel(candidate)) }
                }
            }
            ScopeMenu(
                label = stringResource(Res.string.web_recruit_reason),
                selected = recruitmentLabel(reason),
                options = DECISION_REASONS.getValue(decision).map { ScopeOption(it, recruitmentLabel(it)) },
                enabled = !locked,
                onSelected = { selected -> selected?.let { reason = it } },
            )
            OutlinedTextField(message, { message = it.take(500) }, Modifier.fillMaxWidth(),
                label = { Text(stringResource(Res.string.web_recruit_safe_message)) }, enabled = !locked,
                textStyle = recruitmentTextStyle(message))
            if (decision == "APPROVE") {
                Text(stringResource(Res.string.web_recruit_services), fontWeight = FontWeight.Bold)
                ServiceCheckbox(stringResource(Res.string.service_type_on_demand), onDemand, !locked) { onDemand = it }
                ServiceCheckbox(stringResource(Res.string.service_type_fixed_route), fixedRoute, !locked) { fixedRoute = it }
                ServiceCheckbox(stringResource(Res.string.service_type_scheduled), scheduled, !locked) { scheduled = it }
                val vehicleChoices = application.evidence.mapNotNull { it.vehicleId }.distinct()
                ScopeMenu(
                    label = stringResource(Res.string.web_recruit_vehicle),
                    selected = vehicleId?.let { ltrIsolate(shortId(it)) } ?: stringResource(Res.string.web_recruit_no_vehicle),
                    options = listOf(ScopeOption(null, stringResource(Res.string.web_recruit_no_vehicle))) + vehicleChoices.map { ScopeOption(it, ltrIsolate(shortId(it))) },
                    enabled = !locked,
                    onSelected = { vehicleId = it },
                )
                OutlinedTextField(validUntil, { validUntil = it.take(40) }, Modifier.fillMaxWidth(),
                    label = { Text(stringResource(Res.string.web_recruit_authorization_expiry)) }, enabled = !locked,
                    textStyle = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.Ltr))
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(confirmed, { confirmed = it }, enabled = !locked)
                Text(stringResource(Res.string.web_recruit_decision_check))
            }
            val serviceTypes = buildList {
                if (onDemand) add("ON_DEMAND")
                if (fixedRoute) add("FIXED_ROUTE")
                if (scheduled) add("SCHEDULED")
            }
            Button(
                shape = androidx.compose.foundation.shape.RoundedCornerShape(TaxiTheme.radii.Md),
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
            ) { Text(stringResource(Res.string.web_recruit_confirm_decision)) }
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
