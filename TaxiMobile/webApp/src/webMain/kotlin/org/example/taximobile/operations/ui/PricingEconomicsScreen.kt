package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.MANAGE_CITY_TARIFFS
import org.example.taximobile.operations.model.MANAGE_OPERATOR_FEE_POLICIES
import org.example.taximobile.operations.model.MANAGE_SCHEDULING_POLICY
import org.example.taximobile.operations.model.OperatorFeePolicyRecord
import org.example.taximobile.operations.model.PricingRuleRecord
import org.example.taximobile.operations.model.SchedulingPolicyRecord
import org.example.taximobile.operations.model.pricingPolicyTargetFor
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState

private const val NEW_POLICY = "__new_policy__"

@Composable
internal fun PricingEconomicsScreen(
    state: OperationsUiState,
    coordinator: OperationsCoordinator,
) {
    val snapshot = state.snapshot ?: return
    val city = snapshot.cities.items.firstOrNull { it.id == state.scope.cityId }
    val operator = snapshot.operators.items.firstOrNull { it.id == state.scope.operatorId }
    val permissions = state.session?.permissions.orEmpty()
    ScreenColumn {
        SectionHeading(
            "Pricing & operator economics",
            "Create immutable city/operator policy versions, review them, and activate only coherent backend-validated rules.",
        )
        if (city == null || operator == null) {
            EmptyState(
                "Select one city and operator",
                "Pricing commands require an explicit city/operator conjunction. Choose both in the scope bar; browser selection never grants authority.",
            )
            return@ScreenColumn
        }
        PricingScopeBanner(
            cityName = city.localizedName.preferred(),
            cityCode = city.code,
            operatorName = operator.name,
            currency = snapshot.markets.items.firstOrNull { it.id == city.marketId }?.defaultCurrency ?: "MAD",
            assignmentReady = snapshot.assignments.items.any {
                it.cityId == city.id && it.operatorId == operator.id &&
                    it.serviceType == "ON_DEMAND" && it.status == "ACTIVE"
            },
        )
        val pricing = snapshot.pricingEconomics
        if (pricing == null) {
            EmptyState("Pricing scope unavailable", "The backend returned no pricing module for these active grants and city scope.")
            return@ScreenColumn
        }
        PricingMetrics(state)
        val currency = snapshot.markets.items.firstOrNull { it.id == city.marketId }?.defaultCurrency ?: "MAD"
        if (MANAGE_CITY_TARIFFS in permissions) {
            TariffSection(state, operator.id, currency, coordinator)
        }
        if (MANAGE_OPERATOR_FEE_POLICIES in permissions) {
            OperatorFeeSection(state, operator.id, currency, coordinator)
        }
        if (MANAGE_SCHEDULING_POLICY in permissions) {
            SchedulingPolicySection(state, operator.id, currency, coordinator)
        }
    }
}

@Composable
private fun PricingScopeBanner(
    cityName: String,
    cityCode: String,
    operatorName: String,
    currency: String,
    assignmentReady: Boolean,
) {
    Surface(
        color = if (assignmentReady) TaxiColors.Info100 else TaxiColors.Warning100,
        shape = RoundedCornerShape(TaxiRadii.Md),
        border = BorderStroke(
            1.dp,
            (if (assignmentReady) TaxiColors.Info600 else TaxiColors.Warning600).copy(alpha = 0.25f),
        ),
    ) {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            Text("$cityName ($cityCode) · $operatorName · $currency", fontWeight = FontWeight.Bold)
            Text(
                if (assignmentReady) {
                    "An active on-demand assignment is visible. Activation still revalidates its effective interval and the complete policy."
                } else {
                    "No active on-demand assignment is visible in this snapshot. Drafts may be possible, but activation will fail closed."
                },
                color = if (assignmentReady) TaxiColors.Info600 else TaxiColors.Warning600,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun PricingMetrics(state: OperationsUiState) {
    val pricing = state.snapshot?.pricingEconomics ?: return
    val allStatuses = buildList {
        addAll(pricing.pricingRules?.items.orEmpty().map { it.status })
        addAll(pricing.operatorFeePolicies?.items.orEmpty().map { it.status })
        addAll(pricing.schedulingPolicies?.items.orEmpty().map { it.status })
    }
    Row(
        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
    ) {
        MetricCard("Active policies", allStatuses.count { it == "ACTIVE" }.toString(), "Across visible policy families", Modifier.width(210.dp))
        MetricCard("Awaiting review", allStatuses.count { it == "IN_REVIEW" }.toString(), "Activation requires an audited reason", Modifier.width(220.dp))
        MetricCard("Drafts", allStatuses.count { it == "DRAFT" }.toString(), "Only drafts remain editable", Modifier.width(200.dp))
    }
}

@Composable
private fun TariffSection(
    state: OperationsUiState,
    operatorId: String,
    currency: String,
    coordinator: OperationsCoordinator,
) {
    val page = state.snapshot?.pricingEconomics?.pricingRules
    var editorId by remember(state.scope.cityId, operatorId) { mutableStateOf<String?>(null) }
    var pending by remember(state.scope.cityId, operatorId) { mutableStateOf<Pair<PricingRuleRecord, String>?>(null) }
    SectionHeading(
        "Immediate tariffs",
        "Publish on-demand fares or complete-direction fixed-route fares. Replacement remains isolated by city, operator, service, and booking type.",
        action = { TextButton(onClick = { editorId = NEW_POLICY }, enabled = !state.interactionLocked) { Text("New tariff draft") } },
    )
    PolicyCollection(
        empty = page?.items.isNullOrEmpty(),
        emptyTitle = "No tariff versions",
        emptyDetail = "Create a fixed tariff draft before a city configuration can reference pricing.",
    ) {
        page?.items.orEmpty().forEach { record ->
            PolicyCard(
                title = record.name,
                version = record.version,
                status = record.status,
                revision = record.optimisticVersion,
                effectiveFrom = record.effectiveFrom,
                effectiveUntil = record.effectiveUntil,
                details = listOf(
                    "${record.fixedAmount ?: "—"} ${record.currency} · ${record.model}",
                    "${record.serviceType.replace('_', ' ')} · ${record.bookingType.replace('_', ' ')}",
                    if (record.serviceType == "FIXED_ROUTE") {
                        record.fixedRouteDirectionId?.let { "Direction $it" }
                            ?: "Unbound fare draft · activation is blocked"
                    } else {
                        "City/operator point-to-point scope"
                    },
                ),
                locked = state.interactionLocked,
                onEdit = { editorId = record.id },
                onTransition = { target -> pending = record to target },
            )
        }
        page?.let { PageLimitNote(it.items.size, it.total) }
    }
    editorId?.let { selectedId ->
        TariffEditor(
            existing = page?.items?.firstOrNull { it.id == selectedId },
            fixedRouteDirections = state.snapshot?.fixedRoutes?.items.orEmpty()
                .flatMap { it.versions }
                .filter { it.status == "DRAFT" }
                .flatMap { it.directions }
                .filter { it.flatFarePolicyVersionId == null },
            operatorId = operatorId,
            currencyHint = currency,
            locked = state.interactionLocked,
            onCreate = { editorId = null; coordinator.createPricingRule(it) },
            onUpdate = { record, request -> editorId = null; coordinator.updatePricingRule(record, request) },
            onClose = { editorId = null },
        )
    }
    pending?.let { (record, target) ->
        PolicyTransitionDialog("Tariff", record.version, target, state.interactionLocked,
            onConfirm = { reason -> pending = null; coordinator.transitionPricingRule(record, target, reason) },
            onDismiss = { pending = null })
    }
}

@Composable
private fun OperatorFeeSection(
    state: OperationsUiState,
    operatorId: String,
    currency: String,
    coordinator: OperationsCoordinator,
) {
    val page = state.snapshot?.pricingEconomics?.operatorFeePolicies
    var editorId by remember(state.scope.cityId, operatorId) { mutableStateOf<String?>(null) }
    var pending by remember(state.scope.cityId, operatorId) { mutableStateOf<Pair<OperatorFeePolicyRecord, String>?>(null) }
    SectionHeading(
        "Operator service-fee policies",
        "The calculation base, rounding, funding, and driver-net floor are explicit. Zero-fee versions are first-class policies.",
        action = { TextButton(onClick = { editorId = NEW_POLICY }, enabled = !state.interactionLocked) { Text("New fee draft") } },
    )
    PolicyCollection(page?.items.isNullOrEmpty(), "No operator-fee versions", "Create an explicit zero or non-zero fee policy before activation.") {
        page?.items.orEmpty().forEach { record ->
            val feeDisplay = if (record.calculationMode == "PERCENTAGE_OF_TRANSPORT_FARE") {
                "${record.percentageRate ?: "—"}% of ${record.eligibleBaseCode}"
            } else {
                "${record.flatAmount ?: "—"} ${record.currency} per completed booking"
            }
            PolicyCard(
                title = "Operator service fee",
                version = record.version,
                status = record.status,
                revision = record.optimisticVersion,
                effectiveFrom = record.effectiveFrom,
                effectiveUntil = record.effectiveUntil,
                details = listOf(
                    feeDisplay,
                    record.fundingMode.replace('_', ' '),
                    "Minimum driver net ${record.minimumDriverNet} ${record.currency} · ${record.roundingRule}",
                ),
                locked = state.interactionLocked,
                onEdit = { editorId = record.id },
                onTransition = { target -> pending = record to target },
            )
        }
        page?.let { PageLimitNote(it.items.size, it.total) }
    }
    editorId?.let { selectedId ->
        FeePolicyEditor(
            existing = page?.items?.firstOrNull { it.id == selectedId },
            operatorId = operatorId,
            currencyHint = currency,
            locked = state.interactionLocked,
            onCreate = { editorId = null; coordinator.createOperatorFeePolicy(it) },
            onUpdate = { record, request -> editorId = null; coordinator.updateOperatorFeePolicy(record, request) },
            onClose = { editorId = null },
        )
    }
    pending?.let { (record, target) ->
        PolicyTransitionDialog("Operator-fee policy", record.version, target, state.interactionLocked,
            onConfirm = { reason -> pending = null; coordinator.transitionOperatorFeePolicy(record, target, reason) },
            onDismiss = { pending = null })
    }
}

@Composable
private fun SchedulingPolicySection(
    state: OperationsUiState,
    operatorId: String,
    currency: String,
    coordinator: OperationsCoordinator,
) {
    val page = state.snapshot?.pricingEconomics?.schedulingPolicies
    var editorId by remember(state.scope.cityId, operatorId) { mutableStateOf<String?>(null) }
    var pending by remember(state.scope.cityId, operatorId) { mutableStateOf<Pair<SchedulingPolicyRecord, String>?>(null) }
    SectionHeading(
        "Scheduled booking policy",
        "Version the surcharge, offer windows, conflict protection, cancellation rules, and handoff fallback for one service scope.",
        action = { TextButton(onClick = { editorId = NEW_POLICY }, enabled = !state.interactionLocked) { Text("New schedule draft") } },
    )
    PolicyCollection(page?.items.isNullOrEmpty(), "No scheduling-policy versions", "Create an explicit zero-surcharge policy when scheduling carries no additional charge.") {
        page?.items.orEmpty().forEach { record ->
            PolicyCard(
                title = "Scheduling surcharge",
                version = record.version,
                status = record.status,
                revision = record.optimisticVersion,
                effectiveFrom = record.effectiveFrom,
                effectiveUntil = record.effectiveUntil,
                details = listOf(
                    "${record.surchargeAmount} ${record.currency}",
                    "Beneficiary ${record.beneficiary} · ${record.collectionTimingCode}",
                    "Lead ${record.minimumLeadMinutes} min · horizon ${record.maximumHorizonDays} days · offers ${record.offerOpenMinutesBefore} min before",
                    "Commit by ${record.commitmentDeadlineMinutesBefore} min · handoff ${record.handoffMinutesBefore} min · response ${record.offerResponseSeconds} sec",
                    "Protected ${record.protectedDurationMinutes} min (+${record.conflictBufferBeforeMinutes}/+${record.conflictBufferAfterMinutes} buffers)",
                    "Cancellation P${record.passengerCancelCutoffMinutes}/D${record.driverCancelCutoffMinutes} min · ${record.surchargeRefundMode}",
                    "Fallback matching ${if (record.fallbackMatchingEnabled) "enabled" else "disabled"}",
                ),
                locked = state.interactionLocked,
                onEdit = { editorId = record.id },
                onTransition = { target -> pending = record to target },
            )
        }
        page?.let { PageLimitNote(it.items.size, it.total) }
    }
    editorId?.let { selectedId ->
        SchedulingPolicyEditor(
            existing = page?.items?.firstOrNull { it.id == selectedId },
            operatorId = operatorId,
            currencyHint = currency,
            locked = state.interactionLocked,
            onCreate = { editorId = null; coordinator.createSchedulingPolicy(it) },
            onUpdate = { record, request -> editorId = null; coordinator.updateSchedulingPolicy(record, request) },
            onClose = { editorId = null },
        )
    }
    pending?.let { (record, target) ->
        PolicyTransitionDialog("Scheduling policy", record.version, target, state.interactionLocked,
            onConfirm = { reason -> pending = null; coordinator.transitionSchedulingPolicy(record, target, reason) },
            onDismiss = { pending = null })
    }
}

@Composable
private fun PolicyCollection(
    empty: Boolean,
    emptyTitle: String,
    emptyDetail: String,
    content: @Composable () -> Unit,
) {
    if (empty) EmptyState(emptyTitle, emptyDetail) else content()
}

@Composable
private fun PolicyCard(
    title: String,
    version: String,
    status: String,
    revision: Int,
    effectiveFrom: String,
    effectiveUntil: String?,
    details: List<String>,
    locked: Boolean,
    onEdit: () -> Unit,
    onTransition: (String) -> Unit,
) {
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("Version $version · backend revision $revision", color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
                }
                StatusBadge(status)
            }
            details.forEach { Text(it, color = TaxiColors.Ink700, style = MaterialTheme.typography.bodyMedium) }
            Text("Effective ${compactTimestamp(effectiveFrom)} to ${compactTimestamp(effectiveUntil)}", color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                if (status == "DRAFT") {
                    OutlinedButton(onClick = onEdit, enabled = !locked) { Text("Edit draft") }
                }
                pricingPolicyTargetFor(status)?.let { target ->
                    Button(onClick = { onTransition(target) }, enabled = !locked) {
                        Text(if (target == "IN_REVIEW") "Submit for review" else "Review activation")
                    }
                }
            }
        }
    }
}

@Composable
private fun PolicyTransitionDialog(
    policyType: String,
    version: String,
    target: String,
    busy: Boolean,
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    var reason by remember(policyType, version, target) { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(if (target == "ACTIVE") "Activate $policyType?" else "Submit $policyType for review?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(
                    if (target == "ACTIVE") {
                        "Version $version must be currently effective and may replace an overlapping active version in exactly this city/operator/service scope. Historical records remain unchanged."
                    } else {
                        "Version $version will become read-only while it awaits activation review."
                    }
                )
                OutlinedTextField(
                    reason,
                    { reason = it.take(240) },
                    Modifier.fillMaxWidth(),
                    label = { Text("Audited reason") },
                    enabled = !busy,
                )
            }
        },
        confirmButton = {
            Button(onClick = { onConfirm(reason.trim()) }, enabled = reason.trim().length in 3..240 && !busy) {
                Text(if (busy) "Waiting for backend…" else if (target == "ACTIVE") "Activate" else "Submit")
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}
