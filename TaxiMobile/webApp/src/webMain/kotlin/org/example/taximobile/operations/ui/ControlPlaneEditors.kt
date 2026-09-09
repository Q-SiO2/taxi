package org.example.taximobile.operations.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.CityConfigurationCreateRequest
import org.example.taximobile.operations.model.CityCreateRequest
import org.example.taximobile.operations.model.CityRecord
import org.example.taximobile.operations.model.ConfigurationRouteInput
import org.example.taximobile.operations.model.ConfigurationServiceInput
import org.example.taximobile.operations.model.Coordinate
import org.example.taximobile.operations.model.LocalizedName
import org.example.taximobile.operations.model.OperatorCityAssignment
import org.example.taximobile.operations.model.OperatorCityAssignmentCreateRequest
import org.example.taximobile.operations.model.OperatorCreateRequest
import org.example.taximobile.operations.model.OperatorRecord
import org.example.taximobile.operations.model.OperationsSnapshot
import org.example.taximobile.operations.model.ServiceAreaVersionCreateRequest
import org.example.taximobile.operations.model.parseServiceAreaBoundary
import org.example.taximobile.operations.model.validControlPlaneVersion
import org.example.taximobile.operations.model.validControlPlaneEffectiveRange

private val controlPlaneServices = listOf("ON_DEMAND", "FIXED_ROUTE")

@Composable
internal fun CreateCityDialog(
    marketId: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (CityCreateRequest) -> Unit,
) {
    var code by remember { mutableStateOf("") }
    var nameEn by remember { mutableStateOf("") }
    var nameFr by remember { mutableStateOf("") }
    var nameAr by remember { mutableStateOf("") }
    var timezone by remember { mutableStateOf("Africa/Casablanca") }
    var latitude by remember { mutableStateOf("") }
    var longitude by remember { mutableStateOf("") }
    val latitudeValue = latitude.trim().toDoubleOrNull()
    val longitudeValue = longitude.trim().toDoubleOrNull()
    val valid = code.matches(Regex("[a-z0-9]+(?:-[a-z0-9]+)*")) && code.length in 2..64 &&
        listOf(nameEn, nameFr, nameAr).all { it.trim().isNotEmpty() } &&
        Regex("^[A-Za-z_]+(?:/[A-Za-z0-9_+\\-]+)+$").matches(timezone.trim()) &&
        latitudeValue != null && latitudeValue in -90.0..90.0 &&
        longitudeValue != null && longitudeValue in -180.0..180.0

    EditorDialog(
        title = "Create city",
        explanation = "Creates a DRAFT city in the selected market. Names are passenger-facing; the centroid is for presentation, not the service boundary.",
        confirmLabel = "Create city",
        busy = busy,
        valid = valid,
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                CityCreateRequest(
                    marketId = marketId,
                    code = code.trim(),
                    localizedName = LocalizedName(nameEn.trim(), nameFr.trim(), nameAr.trim()),
                    timezone = timezone.trim(),
                    presentationCentroid = Coordinate(latitudeValue!!, longitudeValue!!),
                )
            )
        },
    ) {
        EditorField(code, { code = it.lowercase().take(64) }, "City code", "lowercase-slug")
        EditorField(nameEn, { nameEn = it.take(120) }, "Name · English")
        EditorField(nameFr, { nameFr = it.take(120) }, "Name · French")
        EditorField(nameAr, { nameAr = it.take(120) }, "Name · Arabic")
        EditorField(timezone, { timezone = it.take(64) }, "IANA timezone", "Africa/Casablanca")
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
            EditorField(latitude, { latitude = it.take(24) }, "Centroid latitude", modifier = Modifier.weight(1f))
            EditorField(longitude, { longitude = it.take(24) }, "Centroid longitude", modifier = Modifier.weight(1f))
        }
    }
}

@Composable
internal fun CreateOperatorDialog(
    marketId: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (OperatorCreateRequest) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var operatorType by remember { mutableStateOf("LOCAL_ENTITY") }
    var cooperativeId by remember { mutableStateOf("") }
    val valid = name.trim().isNotEmpty() &&
        (operatorType != "COOPERATIVE" || cooperativeId.trim().isNotEmpty())
    EditorDialog(
        title = "Create operator",
        explanation = "Creates a separate DRAFT operating entity. Service authority is granted later through a city assignment.",
        confirmLabel = "Create operator",
        busy = busy,
        valid = valid,
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                OperatorCreateRequest(
                    marketId = marketId,
                    cooperativeId = cooperativeId.trim().ifEmpty { null },
                    name = name.trim(),
                    operatorType = operatorType,
                )
            )
        },
    ) {
        EditorField(name, { name = it.take(200) }, "Operator name")
        ChoiceChips("Operator type", listOf("LOCAL_ENTITY", "PLATFORM", "COOPERATIVE"), operatorType) {
            operatorType = it
        }
        if (operatorType == "COOPERATIVE") {
            EditorField(
                cooperativeId,
                { cooperativeId = it.take(36) },
                "Existing cooperative ID",
                "Required because cooperative records remain independently governed",
            )
        }
    }
}

@Composable
internal fun CreateAssignmentDialog(
    city: CityRecord,
    operator: OperatorRecord,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (OperatorCityAssignmentCreateRequest) -> Unit,
) {
    var serviceType by remember { mutableStateOf("ON_DEMAND") }
    var effectiveFrom by remember { mutableStateOf("") }
    var effectiveUntil by remember { mutableStateOf("") }
    val valid = validControlPlaneEffectiveRange(effectiveFrom, effectiveUntil)
    EditorDialog(
        title = "Assign city service",
        explanation = "Grants ${operator.name} authority for one service in ${city.localizedName.preferred()}. The backend rejects overlapping active assignments.",
        confirmLabel = "Create assignment",
        busy = busy,
        valid = valid,
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                OperatorCityAssignmentCreateRequest(
                    operatorId = operator.id,
                    cityId = city.id,
                    serviceType = serviceType,
                    effectiveFrom = effectiveFrom.trim(),
                    effectiveUntil = effectiveUntil.trim().ifEmpty { null },
                )
            )
        },
    ) {
        ChoiceChips("Service", controlPlaneServices, serviceType) { serviceType = it }
        EditorField(effectiveFrom, { effectiveFrom = it.take(40) }, "Effective from", "2026-09-01T00:00:00Z")
        EditorField(effectiveUntil, { effectiveUntil = it.take(40) }, "Effective until · optional", "2027-09-01T00:00:00Z")
        Text("Timestamps must include Z or an explicit UTC offset.", color = TaxiColors.Ink500, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
internal fun CreateServiceAreaDialog(
    city: CityRecord,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (ServiceAreaVersionCreateRequest) -> Unit,
) {
    var version by remember { mutableStateOf("") }
    var effectiveFrom by remember { mutableStateOf("") }
    var effectiveUntil by remember { mutableStateOf("") }
    var points by remember { mutableStateOf("") }
    val parsed = parseServiceAreaBoundary(points)
    val valid = validControlPlaneVersion(version) &&
        validControlPlaneEffectiveRange(effectiveFrom, effectiveUntil) && parsed.boundary != null
    EditorDialog(
        title = "Create service-area version",
        explanation = "Creates an immutable DRAFT boundary for ${city.localizedName.preferred()}. Enter one polygon as longitude,latitude points; closure is automatic.",
        confirmLabel = "Create boundary draft",
        busy = busy,
        valid = valid,
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                ServiceAreaVersionCreateRequest(
                    version = version.trim(),
                    boundary = parsed.boundary!!,
                    effectiveFrom = effectiveFrom.trim(),
                    effectiveUntil = effectiveUntil.trim().ifEmpty { null },
                )
            )
        },
    ) {
        EditorField(version, { version = it.take(64) }, "Version", "casablanca-core-v1")
        EditorField(effectiveFrom, { effectiveFrom = it.take(40) }, "Effective from", "2026-09-01T00:00:00Z")
        EditorField(effectiveUntil, { effectiveUntil = it.take(40) }, "Effective until · optional")
        OutlinedTextField(
            value = points,
            onValueChange = { points = it.take(8000) },
            label = { Text("Boundary points") },
            placeholder = { Text("-7.70,33.50\n-7.50,33.50\n-7.50,33.65\n-7.70,33.65") },
            supportingText = { Text(parsed.error ?: "${parsed.boundary?.coordinates?.firstOrNull()?.firstOrNull()?.size?.minus(1) ?: 0} points · WGS84") },
            minLines = 6,
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

private data class ResolvedService(
    val assignment: OperatorCityAssignment,
    val input: ConfigurationServiceInput,
    val missing: List<String>,
)

@Composable
internal fun CreateConfigurationDialog(
    city: CityRecord,
    snapshot: OperationsSnapshot,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (CityConfigurationCreateRequest) -> Unit,
) {
    val areas = snapshot.serviceAreas?.items.orEmpty().filter { it.status in setOf("APPROVED", "ACTIVE") }
    val requirements = snapshot.driverRequirementVersions?.items.orEmpty().filter { it.status == "ACTIVE" }
    val assignments = snapshot.assignments.items.filter {
        it.cityId == city.id && it.status == "ACTIVE" && it.serviceType in controlPlaneServices
    }.distinctBy { it.serviceType }
    val resolved = assignments.map { resolveService(it, city.id, snapshot) }
    var version by remember { mutableStateOf("") }
    var areaId by remember(areas) { mutableStateOf(areas.firstOrNull()?.id) }
    var requirementId by remember(requirements) { mutableStateOf(requirements.firstOrNull()?.id) }
    var selectedServices by remember(resolved) {
        mutableStateOf(resolved.filter { it.missing.isEmpty() }.map { it.assignment.serviceType }.toSet())
    }
    val fixedService = resolved.firstOrNull { it.assignment.serviceType == "FIXED_ROUTE" }
    val routeVersions = snapshot.fixedRoutes?.items.orEmpty()
        .filter { route -> route.cityId == city.id && route.operatorId == fixedService?.assignment?.operatorId && route.status == "ACTIVE" }
        .flatMap { route -> route.versions }
        .filter { it.status == "PUBLISHED" }
    var routeIds by remember(routeVersions) { mutableStateOf(routeVersions.map { it.id }.toSet()) }
    val fixedSchedulingAvailable = fixedService?.input?.schedulingPolicyVersionId != null
    var scheduledRoutes by remember { mutableStateOf(false) }
    val chosen = resolved.filter { it.assignment.serviceType in selectedServices }
    val missing = buildList {
        if (areas.isEmpty()) add("approved service area")
        if (!city.isLegacyCompatibility && requirements.isEmpty()) add("active driver requirements")
        chosen.forEach { service -> addAll(service.missing.map { "${service.assignment.serviceType}: $it" }) }
        if ("FIXED_ROUTE" in selectedServices && routeIds.isEmpty()) add("published fixed-route version")
    }
    val valid = validControlPlaneVersion(version) && areaId != null && chosen.isNotEmpty() &&
        missing.isEmpty() && (city.isLegacyCompatibility || requirementId != null)

    EditorDialog(
        title = "Create coherent configuration",
        explanation = "Builds one reviewed city bundle from existing authoritative versions. Only active compatible financial, payment, recruitment, and route components are offered.",
        confirmLabel = "Create configuration draft",
        busy = busy,
        valid = valid,
        onDismiss = onDismiss,
        onConfirm = {
            onConfirm(
                CityConfigurationCreateRequest(
                    version = version.trim(),
                    serviceAreaVersionId = areaId!!,
                    driverRequirementVersionId = requirementId,
                    services = chosen.map { it.input },
                    routes = if ("FIXED_ROUTE" in selectedServices) {
                        routeIds.map { ConfigurationRouteInput(it, true, scheduledRoutes) }
                    } else emptyList(),
                )
            )
        },
    ) {
        EditorField(version, { version = it.take(64) }, "Bundle version", "casablanca-pilot-v1")
        RecordChoice(
            label = "Approved service area",
            options = areas.map { it.id to "${it.version} · ${it.status}" },
            selectedId = areaId,
            onSelect = { areaId = it },
        )
        if (requirements.isNotEmpty()) {
            RecordChoice(
                label = "Active driver requirements",
                options = requirements.map { it.id to it.version },
                selectedId = requirementId,
                onSelect = { requirementId = it },
            )
        }
        Text("Enabled services", color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
        if (resolved.isEmpty()) {
            Text("No active on-demand or fixed-route assignment is loaded for this city.", color = TaxiColors.Danger600)
        }
        resolved.forEach { service ->
            val type = service.assignment.serviceType
            FilterChip(
                selected = type in selectedServices,
                onClick = {
                    selectedServices = if (type in selectedServices) selectedServices - type else selectedServices + type
                },
                enabled = !busy,
                label = { Text(type.replace('_', ' ')) },
            )
            Text(
                if (service.missing.isEmpty()) "Compatible active policy and payment versions resolved."
                else "Missing ${service.missing.joinToString()}",
                color = if (service.missing.isEmpty()) TaxiColors.Ink500 else TaxiColors.Danger600,
                style = MaterialTheme.typography.bodySmall,
            )
        }
        if ("FIXED_ROUTE" in selectedServices) {
            Text("Published route versions", color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
            routeVersions.forEach { route ->
                FilterChip(
                    selected = route.id in routeIds,
                    onClick = { routeIds = if (route.id in routeIds) routeIds - route.id else routeIds + route.id },
                    enabled = !busy,
                    label = { Text("${route.routeCode} · ${route.version}") },
                )
            }
            if (fixedSchedulingAvailable) {
                FilterChip(
                    selected = scheduledRoutes,
                    onClick = { scheduledRoutes = !scheduledRoutes },
                    enabled = !busy,
                    label = { Text("Allow scheduled fixed-route booking") },
                )
            }
        }
        if (missing.isNotEmpty()) {
            Text("Resolve before creating: ${missing.joinToString()}.", color = TaxiColors.Danger600, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
internal fun ControlPlaneReviewDialog(
    title: String,
    explanation: String,
    confirmLabel: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit,
) {
    var reason by remember(title, explanation) { mutableStateOf("") }
    EditorDialog(
        title = title,
        explanation = explanation,
        confirmLabel = confirmLabel,
        busy = busy,
        valid = reason.trim().length in 3..240,
        onDismiss = onDismiss,
        onConfirm = { onConfirm(reason.trim()) },
    ) {
        OutlinedTextField(
            value = reason,
            onValueChange = { reason = it.take(240) },
            label = { Text("Audit reason") },
            supportingText = { Text("3–240 characters; no secrets or participant data") },
            minLines = 2,
            enabled = !busy,
            modifier = Modifier.fillMaxWidth(),
        )
    }
}

@Composable
internal fun ControlPlaneConfirmDialog(
    title: String,
    explanation: String,
    confirmLabel: String,
    busy: Boolean,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(title) },
        text = { Text(explanation, color = TaxiColors.Ink700) },
        confirmButton = {
            Button(onClick = onConfirm, enabled = !busy) {
                Text(if (busy) "Waiting for backend…" else confirmLabel)
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}

private fun resolveService(
    assignment: OperatorCityAssignment,
    cityId: String,
    snapshot: OperationsSnapshot,
): ResolvedService {
    val economics = snapshot.pricingEconomics
    val operator = snapshot.operators.items.firstOrNull { it.id == assignment.operatorId }
    val existing = snapshot.configurations?.items.orEmpty()
        .filter { it.status == "ACTIVE" }
        .sortedByDescending { it.activatedAt ?: it.updatedAt }
        .flatMap { it.services }
        .firstOrNull {
            it.serviceType == assignment.serviceType &&
                it.operatorCityAssignmentId == assignment.id
        }
    val tariff = economics?.pricingRules?.items?.firstOrNull {
        it.cityId == cityId && it.operatorId == assignment.operatorId &&
            it.serviceType == assignment.serviceType && it.bookingType == "IMMEDIATE" && it.status == "ACTIVE"
    }
    val fee = economics?.operatorFeePolicies?.items?.firstOrNull {
        it.cityId == cityId && it.operatorId == assignment.operatorId &&
            it.serviceType == assignment.serviceType && it.status == "ACTIVE"
    }
    val scheduling = economics?.schedulingPolicies?.items?.firstOrNull {
        it.cityId == cityId && it.operatorId == assignment.operatorId &&
            it.serviceType == assignment.serviceType && it.status == "ACTIVE"
    }
    val payment = snapshot.paymentOperations?.capabilities?.items?.firstOrNull {
        it.cityId == cityId && it.operatorId == assignment.operatorId &&
            it.serviceType == assignment.serviceType && it.status == "ACTIVE"
    }
    val missing = buildList {
        if (operator?.status != "ACTIVE") add("active operator")
        if (assignment.serviceType == "ON_DEMAND" && tariff == null) add("active immediate tariff")
        if (fee == null) add("active operator-fee policy")
        if (payment == null) add("active payment capability")
    }
    return ResolvedService(
        assignment = assignment,
        input = ConfigurationServiceInput(
            serviceType = assignment.serviceType,
            operatorCityAssignmentId = assignment.id,
            tariffVersionId = if (assignment.serviceType == "ON_DEMAND") tariff?.id ?: existing?.tariffVersionId else null,
            operatorFeePolicyVersionId = fee?.id ?: existing?.operatorFeePolicyVersionId,
            schedulingPolicyVersionId = scheduling?.id ?: existing?.schedulingPolicyVersionId,
            paymentCapabilityVersionId = payment?.id ?: existing?.paymentCapabilityVersionId,
        ),
        missing = missing.filterNot { component ->
            when (component) {
                "active immediate tariff" -> existing?.tariffVersionId != null
                "active operator-fee policy" -> existing?.operatorFeePolicyVersionId != null
                "active payment capability" -> existing?.paymentCapabilityVersionId != null
                else -> false
            }
        },
    )
}

@Composable
private fun EditorDialog(
    title: String,
    explanation: String,
    confirmLabel: String,
    busy: Boolean,
    valid: Boolean,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
    content: @Composable () -> Unit,
) {
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(title) },
        text = {
            Column(
                Modifier.fillMaxWidth().heightIn(max = 560.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md),
            ) {
                Text(explanation, color = TaxiColors.Ink700, style = MaterialTheme.typography.bodyMedium)
                content()
            }
        },
        confirmButton = {
            Button(onClick = onConfirm, enabled = !busy && valid) {
                Text(if (busy) "Waiting for backend…" else confirmLabel)
            }
        },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}

@Composable
private fun EditorField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    placeholder: String = "",
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        placeholder = if (placeholder.isBlank()) null else ({ Text(placeholder) }),
        singleLine = true,
        modifier = modifier.fillMaxWidth(),
    )
}

@Composable
private fun ChoiceChips(label: String, options: List<String>, selected: String, onSelect: (String) -> Unit) {
    Text(label, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        options.forEach { option ->
            FilterChip(
                selected = option == selected,
                onClick = { onSelect(option) },
                label = { Text(option.replace('_', ' ')) },
            )
        }
    }
}

@Composable
private fun RecordChoice(
    label: String,
    options: List<Pair<String, String>>,
    selectedId: String?,
    onSelect: (String) -> Unit,
) {
    Text(label, color = TaxiColors.Navy900, fontWeight = FontWeight.Bold)
    if (options.isEmpty()) {
        Text("No compatible version is loaded.", color = TaxiColors.Danger600, style = MaterialTheme.typography.bodySmall)
    } else {
        Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
            options.forEach { (id, text) ->
                FilterChip(selected = selectedId == id, onClick = { onSelect(id) }, label = { Text(text) })
            }
        }
    }
}
