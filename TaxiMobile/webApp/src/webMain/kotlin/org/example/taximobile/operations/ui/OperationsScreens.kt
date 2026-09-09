package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.feature.ui.theme.taxiArabicFontFamily
import org.example.taximobile.operations.model.CityRecord
import org.example.taximobile.operations.model.CityConfigurationRecord
import org.example.taximobile.operations.model.CityConfigurationCreateRequest
import org.example.taximobile.operations.model.CityCreateRequest
import org.example.taximobile.operations.model.MANAGE_CITY_LIFECYCLE
import org.example.taximobile.operations.model.MANAGE_CITY_CONFIGURATION
import org.example.taximobile.operations.model.MANAGE_OPERATORS
import org.example.taximobile.operations.model.MANAGE_OPERATOR_ASSIGNMENTS
import org.example.taximobile.operations.model.MANAGE_SERVICE_AREAS
import org.example.taximobile.operations.model.OperatorCityAssignment
import org.example.taximobile.operations.model.OperatorCityAssignmentCreateRequest
import org.example.taximobile.operations.model.OperatorCreateRequest
import org.example.taximobile.operations.model.OperatorRecord
import org.example.taximobile.operations.model.OperationsScope
import org.example.taximobile.operations.model.OperationsSnapshot
import org.example.taximobile.operations.model.PILOT_ENTRY_READINESS_GATES
import org.example.taximobile.operations.model.POST_LAUNCH_REVIEW_GATE
import org.example.taximobile.operations.model.PUBLIC_ACTIVATION_READINESS_GATES
import org.example.taximobile.operations.model.ServiceAreaVersionCreateRequest
import org.example.taximobile.operations.model.ServiceAreaVersionRecord
import org.example.taximobile.operations.model.configurationTargetFor
import org.example.taximobile.operations.model.lifecycleTargetsFor
import org.example.taximobile.operations.model.operatorStatusTargetsFor
import org.example.taximobile.operations.model.serviceAreaTargetFor
import org.example.taximobile.operations.state.OperationsUiState

@Composable
internal fun RolloutScreen(state: OperationsUiState) {
    val snapshot = state.snapshot ?: return
    val visibleCities = rolloutCitiesForScope(snapshot, state.scope)
    val activeCities = visibleCities.count { it.lifecycleStatus == "ACTIVE" }
    val readyCities = visibleCities.count {
        it.publicActivationRequired > 0 &&
            it.publicActivationPassed == it.publicActivationRequired
    }
    ScreenColumn {
        SectionHeading(
            title = "Rollout overview",
            supportingText = "Backend-authorized visibility and readiness for gradual city deployment.",
        )
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
        ) {
            MetricCard(
                label = "Visible cities",
                value = visibleCities.size.toString(),
                supportingText = "${snapshot.rollout.visibleCityCount} across all active grants",
                modifier = Modifier.width(220.dp),
            )
            MetricCard(
                label = "Active",
                value = activeCities.toString(),
                supportingText = "Publicly operating in this presentation scope",
                modifier = Modifier.width(220.dp),
            )
            MetricCard(
                label = "Readiness complete",
                value = readyCities.toString(),
                supportingText = "Cities ready for audited public activation",
                modifier = Modifier.width(220.dp),
            )
            MetricCard(
                label = "Operators",
                value = snapshot.operators.total.toString(),
                supportingText = "Scoped operator records in the selected market",
                modifier = Modifier.width(220.dp),
            )
        }
        SectionHeading(
            title = "City readiness",
            supportingText = "A lifecycle label never substitutes for the configuration and evidence gates below.",
        )
        if (visibleCities.isEmpty()) {
            EmptyState("No cities in scope", "The backend returned no city visible to the active grants and selected scope.")
        } else {
            DataCard(tableMinWidth = 820.dp) {
                Column(Modifier.fillMaxWidth().widthIn(min = 820.dp)) {
                    TableHeader(listOf("City" to 1.5f, "Lifecycle" to 0.9f, "Pilot" to 0.8f, "Public" to 0.8f, "Post-launch" to 0.9f, "Next blocker" to 2f))
                    visibleCities.forEach { city ->
                        TableRow {
                            TableCell(city.localizedName.preferred(), 1.5f, supporting = city.code)
                            Box(Modifier.weight(0.9f)) { StatusBadge(city.lifecycleStatus) }
                            TableCell("${city.pilotEntryPassed} / ${city.pilotEntryRequired}", 0.8f)
                            TableCell("${city.publicActivationPassed} / ${city.publicActivationRequired}", 0.8f)
                            Box(Modifier.weight(0.9f)) { StatusBadge(city.postLaunchReviewStatus) }
                            TableCell(
                                when {
                                    city.missingPilotEntryGates.isNotEmpty() -> city.missingPilotEntryGates.first().replace('_', ' ')
                                    city.missingPublicActivationGates.isNotEmpty() -> city.missingPublicActivationGates.first().replace('_', ' ')
                                    city.postLaunchReviewStatus != "PASSED" -> "POST LAUNCH REVIEW"
                                    else -> "Rollout evidence complete"
                                },
                                2f,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
internal fun CitiesScreen(
    state: OperationsUiState,
    onSelectCity: (String?) -> Unit,
    onCreateCity: (CityCreateRequest) -> Unit,
    onCreateServiceArea: (ServiceAreaVersionCreateRequest) -> Unit,
    onTransitionServiceArea: (ServiceAreaVersionRecord, String, String) -> Unit,
    onCreateConfiguration: (CityConfigurationCreateRequest) -> Unit,
    onTransitionConfiguration: (CityConfigurationRecord, String, String) -> Unit,
    onTransition: (CityRecord, String, String) -> Unit,
    onReadinessDecision: (CityConfigurationRecord, String, String, String) -> Unit,
) {
    val snapshot = state.snapshot ?: return
    val cities = snapshot.cities.items.filter { city ->
        state.scope.marketId == null || city.marketId == state.scope.marketId
    }
    val selected = cities.firstOrNull { it.id == state.scope.cityId }
    var pendingTransition by remember { mutableStateOf<Pair<CityRecord, String>?>(null) }
    var pendingReadiness by remember { mutableStateOf<PendingReadinessReview?>(null) }
    var showCreateCity by remember { mutableStateOf(false) }
    var showCreateArea by remember(selected?.id) { mutableStateOf(false) }
    var showCreateConfiguration by remember(selected?.id) { mutableStateOf(false) }
    var pendingAreaTransition by remember { mutableStateOf<Pair<ServiceAreaVersionRecord, String>?>(null) }
    var pendingConfigurationTransition by remember { mutableStateOf<Pair<CityConfigurationRecord, String>?>(null) }

    ScreenColumn {
        SectionHeading(
            title = "Cities and activation readiness",
            supportingText = "Inspect city scope, active configuration, service boundary, and allowed lifecycle commands.",
            action = when {
                selected != null -> ({ TextButton(onClick = { onSelectCity(null) }) { Text("View all cities") } })
                state.scope.marketId != null && state.session?.hasPermission(MANAGE_CITY_LIFECYCLE) == true ->
                    ({ Button(onClick = { showCreateCity = true }, enabled = !state.interactionLocked) { Text("Create city") } })
                else -> null
            },
        )
        if (cities.isEmpty()) {
            EmptyState("No city records", "Create and grant a city through the protected backend workflow before it can appear here.")
        } else {
            DataCard(tableMinWidth = 800.dp) {
                Column(Modifier.fillMaxWidth().widthIn(min = 800.dp)) {
                    TableHeader(listOf("City" to 1.5f, "Timezone" to 1.2f, "Lifecycle" to 1f, "Config" to 1.2f, "Action" to 1f))
                    cities.forEach { city ->
                        TableRow(selected = city.id == selected?.id) {
                            TableCell(city.localizedName.preferred(), 1.5f, supporting = city.code)
                            TableCell(city.timezone, 1.2f)
                            Box(Modifier.weight(1f)) { StatusBadge(city.lifecycleStatus) }
                            TableCell(shortId(city.activeConfigurationVersionId), 1.2f)
                            Box(Modifier.weight(1f), contentAlignment = Alignment.CenterStart) {
                                OutlinedButton(onClick = { onSelectCity(city.id) }, enabled = !state.interactionLocked) {
                                    Text("Inspect", maxLines = 1, softWrap = false)
                                }
                            }
                        }
                    }
                }
            }
            PageLimitNote(cities.size, snapshot.cities.total)
        }

        if (selected != null) {
            CityDetail(
                city = selected,
                state = state,
                snapshot = snapshot,
                onRequestTransition = { target -> pendingTransition = selected to target },
                onRequestReadinessReview = { configuration, gate ->
                    pendingReadiness = PendingReadinessReview(configuration, gate)
                },
                onCreateServiceArea = { showCreateArea = true },
                onTransitionServiceArea = { area, target -> pendingAreaTransition = area to target },
                onCreateConfiguration = { showCreateConfiguration = true },
                onTransitionConfiguration = { configuration, target ->
                    pendingConfigurationTransition = configuration to target
                },
            )
        } else {
            Text(
                "Select a city to load its configuration and service-area versions through a scoped backend request.",
                color = TaxiColors.Ink500,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }

    pendingTransition?.let { (city, target) ->
        LifecycleReviewDialog(
            city = city,
            target = target,
            busy = state.mutationLabel != null,
            onDismiss = { if (state.mutationLabel == null) pendingTransition = null },
            onConfirm = { reason ->
                pendingTransition = null
                onTransition(city, target, reason)
            },
        )
    }
    pendingReadiness?.let { review ->
        ReadinessReviewDialog(
            review = review,
            busy = state.mutationLabel != null,
            onDismiss = { if (state.mutationLabel == null) pendingReadiness = null },
            onConfirm = { status, evidence ->
                pendingReadiness = null
                onReadinessDecision(review.configuration, review.gateCode, status, evidence)
            },
        )
    }
    state.scope.marketId?.let { marketId ->
        if (showCreateCity) {
            CreateCityDialog(
                marketId = marketId,
                busy = state.mutationLabel != null,
                onDismiss = { showCreateCity = false },
                onConfirm = { showCreateCity = false; onCreateCity(it) },
            )
        }
    }
    selected?.let { city ->
        if (showCreateArea) {
            CreateServiceAreaDialog(
                city = city,
                busy = state.mutationLabel != null,
                onDismiss = { showCreateArea = false },
                onConfirm = { showCreateArea = false; onCreateServiceArea(it) },
            )
        }
        if (showCreateConfiguration) {
            CreateConfigurationDialog(
                city = city,
                snapshot = snapshot,
                busy = state.mutationLabel != null,
                onDismiss = { showCreateConfiguration = false },
                onConfirm = { showCreateConfiguration = false; onCreateConfiguration(it) },
            )
        }
    }
    pendingAreaTransition?.let { (area, target) ->
        ControlPlaneReviewDialog(
            title = "Review service-area transition",
            explanation = "${area.version} will move from ${area.status} to $target using backend version ${area.optimisticVersion}.",
            confirmLabel = "Confirm $target",
            busy = state.mutationLabel != null,
            onDismiss = { pendingAreaTransition = null },
            onConfirm = { reason -> pendingAreaTransition = null; onTransitionServiceArea(area, target, reason) },
        )
    }
    pendingConfigurationTransition?.let { (configuration, target) ->
        ControlPlaneReviewDialog(
            title = "Review configuration transition",
            explanation = "${configuration.version} will move from ${configuration.status} to $target. The backend will revalidate every referenced component.",
            confirmLabel = "Confirm $target",
            busy = state.mutationLabel != null,
            onDismiss = { pendingConfigurationTransition = null },
            onConfirm = { reason ->
                pendingConfigurationTransition = null
                onTransitionConfiguration(configuration, target, reason)
            },
        )
    }
}

@Composable
private fun CityDetail(
    city: CityRecord,
    state: OperationsUiState,
    snapshot: OperationsSnapshot,
    onRequestTransition: (String) -> Unit,
    onRequestReadinessReview: (CityConfigurationRecord, String) -> Unit,
    onCreateServiceArea: () -> Unit,
    onTransitionServiceArea: (ServiceAreaVersionRecord, String) -> Unit,
    onCreateConfiguration: () -> Unit,
    onTransitionConfiguration: (CityConfigurationRecord, String) -> Unit,
) {
    SectionHeading(
        title = city.localizedName.preferred(),
        supportingText = "${city.localizedName.fr} · optimistic version ${city.optimisticVersion}",
    )
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text("AR · ", color = TaxiColors.Ink500, style = MaterialTheme.typography.bodyMedium)
        Text(
            text = city.localizedName.ar,
            color = TaxiColors.Ink500,
            style = MaterialTheme.typography.bodyMedium,
            fontFamily = taxiArabicFontFamily(),
        )
    }
    DataCard {
        Column(Modifier.padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Lg)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Xl)) {
                KeyValue("City code", city.code, Modifier.weight(1f))
                KeyValue("Timezone", city.timezone, Modifier.weight(1f))
                KeyValue(
                    "Centroid",
                    "${city.presentationCentroid.latitude}, ${city.presentationCentroid.longitude}",
                    Modifier.weight(1f),
                )
                Column(Modifier.weight(1f)) {
                    Text("LIFECYCLE", style = MaterialTheme.typography.labelSmall, color = TaxiColors.Ink500)
                    Spacer(Modifier.height(TaxiSpacing.Xxs))
                    StatusBadge(city.lifecycleStatus)
                }
            }
            if (city.isLegacyCompatibility) {
                Text(
                    "Compatibility city: preserves the proven single-city data plane while national ownership is introduced.",
                    color = TaxiColors.Info600,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(TaxiColors.Info100, RoundedCornerShape(TaxiRadii.Sm))
                        .padding(TaxiSpacing.Sm),
                )
            }
            val targets = lifecycleTargetsFor(city.lifecycleStatus)
            if (state.session?.hasPermission(MANAGE_CITY_LIFECYCLE) == true && targets.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
                    Text("REVIEWED LIFECYCLE COMMANDS", style = MaterialTheme.typography.labelSmall, color = TaxiColors.Ink500)
                    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                        targets.forEach { target ->
                            OutlinedButton(
                                onClick = { onRequestTransition(target) },
                                enabled = !state.interactionLocked,
                                border = BorderStroke(
                                    1.dp,
                                    if (target == "RETIRED" || target == "PAUSED") TaxiColors.Danger600 else TaxiColors.Navy400,
                                ),
                            ) {
                                Text("Review ${target.replace('_', ' ').lowercase()}")
                            }
                        }
                    }
                    Text(
                        when (city.lifecycleStatus) {
                            "CONFIGURING" -> "PILOT requires the active bundle's pre-pilot evidence. It remains bounded and non-public."
                            "PILOT" -> "ACTIVE remains blocked until pilot service and fairness evidence is reviewed."
                            "ACTIVE" -> "Emergency PAUSED remains available without changing the approved configuration."
                            else -> "The backend revalidates the active bundle and stage-specific evidence on every launch command."
                        },
                        color = TaxiColors.Ink500,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }

    val configurations = snapshot.configurations
    SectionHeading(
        title = "Configuration versions",
        supportingText = "Draft, review, approval, and activation remain separate backend commands.",
        action = if (state.session?.hasPermission(MANAGE_CITY_CONFIGURATION) == true) {
            { Button(onClick = onCreateConfiguration, enabled = !state.interactionLocked) { Text("Create bundle") } }
        } else null,
    )
    if (configurations == null || configurations.items.isEmpty()) {
        EmptyState("No configuration versions", "No coherent configuration bundle exists for this city yet.")
    } else {
        DataCard(tableMinWidth = 820.dp) {
            Column(Modifier.fillMaxWidth().widthIn(min = 820.dp)) {
                TableHeader(listOf("Version" to 1.1f, "Status" to 1f, "Services" to 0.8f, "Readiness" to 1f, "Activated" to 1.2f, "Action" to 1.2f))
                configurations.items.forEach { configuration ->
                    val target = configurationTargetFor(configuration.status)
                    TableRow(selected = configuration.id == city.activeConfigurationVersionId) {
                        TableCell(configuration.version, 1.1f, supporting = shortId(configuration.id))
                        Box(Modifier.weight(1f)) { StatusBadge(configuration.status) }
                        TableCell(configuration.services.count { it.enabled }.toString(), 1f)
                        TableCell(
                            if (configuration.missingReadinessGates.isEmpty()) "Complete" else "${configuration.missingReadinessGates.size} missing",
                            1f,
                        )
                        TableCell(compactTimestamp(configuration.activatedAt), 1.2f)
                        Box(Modifier.weight(1.2f), contentAlignment = Alignment.CenterStart) {
                            if (target != null && state.session?.hasPermission(MANAGE_CITY_CONFIGURATION) == true) {
                                OutlinedButton(
                                    onClick = { onTransitionConfiguration(configuration, target) },
                                    enabled = !state.interactionLocked,
                                ) { Text("Review ${target.replace('_', ' ').lowercase()}") }
                            } else Text("—", color = TaxiColors.Ink500)
                        }
                    }
                }
            }
        }
        PageLimitNote(configurations.items.size, configurations.total)

        val readinessConfiguration = configurations.items.firstOrNull { it.status == "APPROVED" }
            ?: configurations.items.firstOrNull { it.id == city.activeConfigurationVersionId }
        if (readinessConfiguration != null) {
            val isActiveBundle = readinessConfiguration.id == city.activeConfigurationVersionId
            SectionHeading(
                title = "Staged rollout evidence · ${readinessConfiguration.version}",
                supportingText = if (isActiveBundle) {
                    "Active bundle. References are non-secret audit pointers; documents and participant data do not belong here."
                } else {
                    "Approved replacement bundle. It must pass independent stage evidence before activation; no evidence is inherited."
                },
            )
            ReadinessGateGroup(
                title = "1 · Pilot entry",
                supportingText = "Configuration, staffing, safety, payment, localization, and routing checks required before PILOT.",
                gates = PILOT_ENTRY_READINESS_GATES,
                configuration = readinessConfiguration,
                canManage = state.session?.hasPermission(MANAGE_CITY_LIFECYCLE) == true,
                locked = state.interactionLocked,
                onReview = { onRequestReadinessReview(readinessConfiguration, it) },
            )
            ReadinessGateGroup(
                title = "2 · Public activation",
                supportingText = "Measured pilot service and fairness evidence is required before ACTIVE.",
                gates = PUBLIC_ACTIVATION_READINESS_GATES - PILOT_ENTRY_READINESS_GATES.toSet(),
                configuration = readinessConfiguration,
                canManage = state.session?.hasPermission(MANAGE_CITY_LIFECYCLE) == true,
                locked = state.interactionLocked,
                onReview = { onRequestReadinessReview(readinessConfiguration, it) },
            )
            ReadinessGateGroup(
                title = "3 · Post-launch closeout",
                supportingText = "Record the reviewed launch outcome before advancing the next city rollout plan.",
                gates = listOf(POST_LAUNCH_REVIEW_GATE),
                configuration = readinessConfiguration,
                canManage = isActiveBundle &&
                    state.session?.hasPermission(MANAGE_CITY_LIFECYCLE) == true,
                locked = state.interactionLocked,
                onReview = { onRequestReadinessReview(readinessConfiguration, it) },
            )
        }
    }

    val serviceAreas = snapshot.serviceAreas
    SectionHeading(
        title = "Service-area versions",
        supportingText = "Only reviewed geometry can be activated as part of a coherent city bundle.",
        action = if (state.session?.hasPermission(MANAGE_SERVICE_AREAS) == true) {
            { Button(onClick = onCreateServiceArea, enabled = !state.interactionLocked) { Text("Create boundary") } }
        } else null,
    )
    if (serviceAreas == null || serviceAreas.items.isEmpty()) {
        EmptyState("No service boundaries", "A reviewed PostGIS service-area version is required before activation.")
    } else {
        DataCard(tableMinWidth = 760.dp) {
            Column(Modifier.fillMaxWidth().widthIn(min = 760.dp)) {
                TableHeader(listOf("Version" to 1.2f, "Status" to 1f, "Effective from" to 1.4f, "Vertices/polygons" to 1.1f, "Action" to 1.2f))
                serviceAreas.items.forEach { area ->
                    val target = serviceAreaTargetFor(area.status)
                    val vertexCount = area.boundary.coordinates.sumOf { polygon ->
                        polygon.sumOf { ring -> ring.size }
                    }
                    TableRow {
                        TableCell(area.version, 1.2f, supporting = shortId(area.id))
                        Box(Modifier.weight(1f)) { StatusBadge(area.status) }
                        TableCell(compactTimestamp(area.effectiveFrom), 1.5f)
                        TableCell("$vertexCount / ${area.boundary.coordinates.size}", 1.1f)
                        Box(Modifier.weight(1.2f), contentAlignment = Alignment.CenterStart) {
                            if (target != null && state.session?.hasPermission(MANAGE_SERVICE_AREAS) == true) {
                                OutlinedButton(
                                    onClick = { onTransitionServiceArea(area, target) },
                                    enabled = !state.interactionLocked,
                                ) { Text("Review ${target.replace('_', ' ').lowercase()}") }
                            } else Text("—", color = TaxiColors.Ink500)
                        }
                    }
                }
            }
        }
    }
}

private data class PendingReadinessReview(
    val configuration: CityConfigurationRecord,
    val gateCode: String,
)

@Composable
private fun ReadinessGateGroup(
    title: String,
    supportingText: String,
    gates: List<String>,
    configuration: CityConfigurationRecord,
    canManage: Boolean,
    locked: Boolean,
    onReview: (String) -> Unit,
) {
    val checks = configuration.readinessChecks.associateBy { it.gateCode }
    DataCard {
        Column(
            Modifier.fillMaxWidth().padding(TaxiSpacing.Lg),
            verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
            Text(supportingText, style = MaterialTheme.typography.bodySmall, color = TaxiColors.Ink500)
            gates.forEach { gate ->
                val check = checks[gate]
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(Modifier.weight(1f)) {
                        Text(gate.replace('_', ' '), style = MaterialTheme.typography.labelMedium, color = TaxiColors.Ink700)
                        Text(
                            check?.nonSecretEvidenceReference ?: "No evidence reference recorded",
                            style = MaterialTheme.typography.bodySmall,
                            color = TaxiColors.Ink500,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                    StatusBadge(check?.status ?: "PENDING")
                    if (canManage && configuration.status in setOf("APPROVED", "ACTIVE")) {
                        OutlinedButton(onClick = { onReview(gate) }, enabled = !locked) {
                            Text(if (check == null) "Review" else "Revise")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReadinessReviewDialog(
    review: PendingReadinessReview,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String, String) -> Unit,
) {
    var decision by remember(review.configuration.optimisticVersion, review.gateCode) { mutableStateOf("PASSED") }
    var evidence by remember(review.configuration.optimisticVersion, review.gateCode) { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Review rollout gate") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(review.gateCode.replace('_', ' '), fontWeight = FontWeight.Bold, color = TaxiColors.Navy900)
                Text(
                    "The backend records this decision against configuration ${review.configuration.version} version ${review.configuration.optimisticVersion}. Use a non-secret ticket, runbook, test-run, or analytics-review reference.",
                    color = TaxiColors.Ink700,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    listOf("PASSED", "FAILED").forEach { option ->
                        if (decision == option) {
                            Button(onClick = { decision = option }, enabled = !busy) { Text(option) }
                        } else {
                            OutlinedButton(onClick = { decision = option }, enabled = !busy) { Text(option) }
                        }
                    }
                }
                OutlinedTextField(
                    value = evidence,
                    onValueChange = { if (it.length <= 240) evidence = it },
                    label = { Text("Evidence reference") },
                    supportingText = { Text("No secrets, documents, names, or participant identifiers") },
                    singleLine = true,
                    enabled = !busy,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onConfirm(decision, evidence.trim()) },
                enabled = !busy && evidence.trim().length >= 3,
            ) { Text("Record decision") }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}

@Composable
internal fun OperatorsScreen(
    state: OperationsUiState,
    onSelectOperator: (String?) -> Unit,
    onCreateOperator: (OperatorCreateRequest) -> Unit,
    onUpdateOperatorStatus: (OperatorRecord, String) -> Unit,
    onCreateAssignment: (OperatorCityAssignmentCreateRequest) -> Unit,
    onRetireAssignment: (OperatorCityAssignment, String) -> Unit,
) {
    val snapshot = state.snapshot ?: return
    val operators = snapshot.operators.items
    val selected = operators.firstOrNull { it.id == state.scope.operatorId }
    val cityNames = snapshot.cities.items.associate { it.id to it.localizedName.preferred() }
    val operatorNames = operators.associate { it.id to it.name }
    val selectedCity = snapshot.cities.items.firstOrNull { it.id == state.scope.cityId }
    var showCreateOperator by remember { mutableStateOf(false) }
    var showCreateAssignment by remember(selected?.id, selectedCity?.id) { mutableStateOf(false) }
    var pendingOperatorStatus by remember { mutableStateOf<Pair<OperatorRecord, String>?>(null) }
    var pendingAssignmentRetirement by remember { mutableStateOf<OperatorCityAssignment?>(null) }
    ScreenColumn {
        SectionHeading(
            title = "Operators and service authority",
            supportingText = "Operators remain separate from city assignments and cooperative membership.",
            action = when {
                selected != null -> ({ TextButton(onClick = { onSelectOperator(null) }) { Text("View all operators") } })
                state.scope.marketId != null && state.session?.hasPermission(MANAGE_OPERATORS) == true ->
                    ({ Button(onClick = { showCreateOperator = true }, enabled = !state.interactionLocked) { Text("Create operator") } })
                else -> null
            },
        )
        if (operators.isEmpty()) {
            EmptyState("No operators in scope", "No operator record is visible to the active grants and selected market.")
        } else {
            DataCard(tableMinWidth = 820.dp) {
                Column(Modifier.fillMaxWidth().widthIn(min = 820.dp)) {
                    TableHeader(listOf("Operator" to 1.8f, "Type" to 1f, "Status" to 1f, "Cooperative" to 1.2f, "Action" to 0.8f))
                    operators.forEach { operator ->
                        TableRow(selected = operator.id == selected?.id) {
                            TableCell(operator.name, 1.8f, supporting = shortId(operator.id))
                            TableCell(operator.operatorType.replace('_', ' '), 1f)
                            Box(Modifier.weight(1f)) { StatusBadge(operator.status) }
                            TableCell(shortId(operator.cooperativeId), 1.2f)
                            Box(Modifier.weight(0.8f), contentAlignment = Alignment.CenterStart) {
                                OutlinedButton(onClick = { onSelectOperator(operator.id) }, enabled = !state.interactionLocked) {
                                    Text("Inspect")
                                }
                            }
                        }
                    }
                }
            }
            PageLimitNote(operators.size, snapshot.operators.total)
        }
        if (selected != null) {
            DataCard {
                Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                    Text(selected.name, style = MaterialTheme.typography.titleLarge, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
                    Text(
                        "${selected.operatorType.replace('_', ' ')} · ${selected.status} · ${shortId(selected.id)}",
                        color = TaxiColors.Ink500,
                    )
                    val targets = operatorStatusTargetsFor(selected.status)
                    if (state.session?.hasPermission(MANAGE_OPERATORS) == true && targets.isNotEmpty()) {
                        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                            targets.forEach { target ->
                                OutlinedButton(
                                    onClick = { pendingOperatorStatus = selected to target },
                                    enabled = !state.interactionLocked,
                                ) { Text("Review ${target.lowercase()}") }
                            }
                        }
                    }
                }
            }
        }
        SectionHeading(
            title = "City assignments",
            supportingText = "One active operator authority is allowed per city, service type, and effective time.",
            action = if (
                selected != null && selectedCity != null &&
                state.session?.hasPermission(MANAGE_OPERATOR_ASSIGNMENTS) == true
            ) {
                { Button(onClick = { showCreateAssignment = true }, enabled = !state.interactionLocked) { Text("Assign service") } }
            } else null,
        )
        if (snapshot.assignments.items.isEmpty()) {
            EmptyState("No assignments", "No operator-city service assignment matches the active scope.")
        } else {
            DataCard(tableMinWidth = 900.dp) {
                Column(Modifier.fillMaxWidth().widthIn(min = 900.dp)) {
                    TableHeader(listOf("Operator" to 1.5f, "City" to 1.3f, "Service" to 1f, "Status" to 0.9f, "Effective" to 1.3f, "Action" to 1f))
                    snapshot.assignments.items.forEach { assignment ->
                        TableRow {
                            TableCell(operatorNames[assignment.operatorId] ?: shortId(assignment.operatorId), 1.5f)
                            TableCell(cityNames[assignment.cityId] ?: shortId(assignment.cityId), 1.3f)
                            TableCell(assignment.serviceType.replace('_', ' '), 1f)
                            Box(Modifier.weight(0.9f)) { StatusBadge(assignment.status) }
                            TableCell(compactTimestamp(assignment.effectiveFrom), 1.3f)
                            Box(Modifier.weight(1f), contentAlignment = Alignment.CenterStart) {
                                if (
                                    assignment.status == "ACTIVE" && assignment.operatorId == selected?.id &&
                                    assignment.cityId == selectedCity?.id &&
                                    state.session?.hasPermission(MANAGE_OPERATOR_ASSIGNMENTS) == true
                                ) {
                                    OutlinedButton(
                                        onClick = { pendingAssignmentRetirement = assignment },
                                        enabled = !state.interactionLocked,
                                    ) { Text("Retire") }
                                } else Text("—", color = TaxiColors.Ink500)
                            }
                        }
                    }
                }
            }
            PageLimitNote(snapshot.assignments.items.size, snapshot.assignments.total)
        }
    }

    state.scope.marketId?.let { marketId ->
        if (showCreateOperator) {
            CreateOperatorDialog(
                marketId = marketId,
                busy = state.mutationLabel != null,
                onDismiss = { showCreateOperator = false },
                onConfirm = { showCreateOperator = false; onCreateOperator(it) },
            )
        }
    }
    if (showCreateAssignment && selected != null && selectedCity != null) {
        CreateAssignmentDialog(
            city = selectedCity,
            operator = selected,
            busy = state.mutationLabel != null,
            onDismiss = { showCreateAssignment = false },
            onConfirm = { showCreateAssignment = false; onCreateAssignment(it) },
        )
    }
    pendingOperatorStatus?.let { (operator, target) ->
        ControlPlaneConfirmDialog(
            title = "Review operator status",
            explanation = "${operator.name} will move from ${operator.status} to $target. Inactive operators cannot satisfy a live city configuration.",
            confirmLabel = "Confirm $target",
            busy = state.mutationLabel != null,
            onDismiss = { pendingOperatorStatus = null },
            onConfirm = { pendingOperatorStatus = null; onUpdateOperatorStatus(operator, target) },
        )
    }
    pendingAssignmentRetirement?.let { assignment ->
        ControlPlaneReviewDialog(
            title = "Retire service assignment",
            explanation = "This retires ${assignment.serviceType.replace('_', ' ')} authority for the selected city/operator. Existing historical records remain unchanged.",
            confirmLabel = "Retire assignment",
            busy = state.mutationLabel != null,
            onDismiss = { pendingAssignmentRetirement = null },
            onConfirm = { reason -> pendingAssignmentRetirement = null; onRetireAssignment(assignment, reason) },
        )
    }
}

@Composable
internal fun AuditScreen(state: OperationsUiState) {
    val logs = state.snapshot?.auditLogs
    ScreenColumn {
        SectionHeading(
            title = "Scoped audit activity",
            supportingText = "Newest-first backend events filtered before pagination and counts.",
        )
        if (logs == null) {
            EmptyState("Audit access not authorized", "The active grants do not include scoped audit visibility.")
        } else if (logs.items.isEmpty()) {
            EmptyState("No audit events", "No event matches the current authorized operator/city presentation scope.")
        } else {
            DataCard(tableMinWidth = 980.dp) {
                Column(Modifier.fillMaxWidth().widthIn(min = 980.dp)) {
                    TableHeader(listOf("When" to 1.2f, "Action" to 1.7f, "Resource" to 1.3f, "Actor" to 1.1f, "Recorded change" to 2.2f))
                    logs.items.forEach { entry ->
                        val changeSummary = entry.changes.toString().let {
                            if (it.length > 180) "${it.take(177)}…" else it
                        }
                        TableRow {
                            TableCell(compactTimestamp(entry.createdAt), 1.2f)
                            TableCell(entry.action.replace('_', ' '), 1.7f)
                            TableCell(entry.resourceType, 1.3f, supporting = shortId(entry.resourceId))
                            TableCell(shortId(entry.actorUserId), 1.1f)
                            TableCell(changeSummary, 2.2f)
                        }
                    }
                }
            }
            PageLimitNote(logs.items.size, logs.total)
        }
    }
}

@Composable
private fun LifecycleReviewDialog(
    city: CityRecord,
    target: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var reason by remember(city.id, target) { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Review city lifecycle change") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(
                    "${city.localizedName.preferred()} will move from ${city.lifecycleStatus} to $target. " +
                        "The backend will validate version ${city.optimisticVersion}, readiness, configuration, and rollout safety before accepting it.",
                    color = TaxiColors.Ink700,
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = { if (it.length <= 240) reason = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Audit reason") },
                    supportingText = { Text("3–240 characters; do not include secrets or participant data.") },
                    minLines = 2,
                    enabled = !busy,
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onConfirm(reason.trim()) },
                enabled = !busy && reason.trim().length >= 3,
            ) {
                Text(if (busy) "Waiting for backend…" else "Confirm $target")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") }
        },
    )
}

@Composable
internal fun ScreenColumn(content: @Composable ColumnScope.() -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(TaxiSpacing.Xl),
        verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xl),
    ) {
        content()
        Spacer(Modifier.height(TaxiSpacing.Xl))
    }
}

@Composable
internal fun TableHeader(columns: List<Pair<String, Float>>) {
    Row(
        modifier = Modifier.fillMaxWidth().background(TaxiColors.Navy50).padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Sm),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        columns.forEach { (label, weight) ->
            Text(
                label.uppercase(),
                modifier = Modifier.weight(weight),
                color = TaxiColors.Ink500,
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold,
            )
        }
    }
}

@Composable
internal fun TableRow(
    selected: Boolean = false,
    content: @Composable RowScope.() -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (selected) TaxiColors.Accent100.copy(alpha = 0.55f) else Color.Transparent)
            .padding(horizontal = TaxiSpacing.Md, vertical = TaxiSpacing.Md),
        horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        content()
    }
}

@Composable
internal fun RowScope.TableCell(
    value: String,
    weight: Float,
    supporting: String? = null,
) {
    Column(Modifier.weight(weight), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xxs)) {
        Text(
            value,
            color = TaxiColors.Ink900,
            style = MaterialTheme.typography.bodyMedium,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
        supporting?.let {
            Text(
                it,
                color = TaxiColors.Ink500,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

private fun rolloutCitiesForScope(snapshot: OperationsSnapshot, scope: OperationsScope) =
    snapshot.rollout.cities.filter { summary ->
        val city = snapshot.cities.items.firstOrNull { it.id == summary.cityId }
        (scope.marketId == null || city?.marketId == scope.marketId) &&
            (scope.cityId == null || summary.cityId == scope.cityId)
    }
