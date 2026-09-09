package org.example.taximobile.operations.ui

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.theme.TaxiColors
import org.example.taximobile.feature.ui.theme.TaxiRadii
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import org.example.taximobile.operations.model.FixedRouteCreateRequest
import org.example.taximobile.operations.model.FixedRouteDirectionDraftRequest
import org.example.taximobile.operations.model.FixedRouteFareOptionRecord
import org.example.taximobile.operations.model.FixedRouteRecord
import org.example.taximobile.operations.model.FixedRouteStopDraftRequest
import org.example.taximobile.operations.model.FixedRouteVersionCreateRequest
import org.example.taximobile.operations.model.FixedRouteVersionRecord
import org.example.taximobile.operations.model.LineStringRecord
import org.example.taximobile.operations.model.LocalizedName
import org.example.taximobile.operations.model.RouteCoordinateRecord
import org.example.taximobile.operations.model.fixedRouteTargetFor
import org.example.taximobile.operations.model.validLatitude
import org.example.taximobile.operations.model.validLongitude
import org.example.taximobile.operations.model.validPolicyVersion
import org.example.taximobile.operations.model.validRouteCode
import org.example.taximobile.operations.model.validZonedTimestamp
import org.example.taximobile.operations.state.OperationsCoordinator
import org.example.taximobile.operations.state.OperationsUiState

@Composable
internal fun FixedRoutesScreen(state: OperationsUiState, coordinator: OperationsCoordinator) {
    val snapshot = state.snapshot ?: return
    val city = snapshot.cities.items.firstOrNull { it.id == state.scope.cityId }
    val operator = snapshot.operators.items.firstOrNull { it.id == state.scope.operatorId }
    var creatingIdentity by remember(state.scope.cityId, state.scope.operatorId) { mutableStateOf(false) }
    var versionRouteId by remember(state.scope.cityId, state.scope.operatorId) { mutableStateOf<String?>(null) }
    var pendingVersion by remember { mutableStateOf<Pair<FixedRouteVersionRecord, String>?>(null) }
    var retiringRoute by remember { mutableStateOf<FixedRouteRecord?>(null) }

    ScreenColumn {
        SectionHeading(
            "Fixed routes",
            "Draft explicit directions, bind a separately reviewed complete-direction fare, review geometry, then publish immutable route content.",
            action = {
                TextButton(
                    onClick = { creatingIdentity = true },
                    enabled = city != null && operator != null && !state.interactionLocked,
                ) { Text("New route") }
            },
        )
        if (city == null || operator == null) {
            EmptyState(
                "Select one city and operator",
                "Route commands require one authorized city/operator conjunction and an active FIXED_ROUTE assignment.",
            )
            return@ScreenColumn
        }
        RouteScopeBanner(
            city.localizedName.preferred(),
            operator.name,
            snapshot.assignments.items.any {
                it.cityId == city.id && it.operatorId == operator.id &&
                    it.serviceType == "FIXED_ROUTE" && it.status == "ACTIVE"
            },
        )
        val page = snapshot.fixedRoutes
        if (page == null) {
            EmptyState("Route scope unavailable", "The backend returned no fixed-route module for this grant and scope.")
        } else if (page.items.isEmpty()) {
            EmptyState("No fixed routes", "Create a stable route identity, then add a reviewed direction version.")
        } else {
            page.items.forEach { route ->
                FixedRouteCard(
                    route = route,
                    locked = state.interactionLocked,
                    onNewVersion = { versionRouteId = route.id },
                    onTransition = { version, target -> pendingVersion = version to target },
                    onRetire = { retiringRoute = route },
                )
            }
            PageLimitNote(page.items.size, page.total)
        }
        if (creatingIdentity) {
            RouteIdentityEditor(
                operatorId = operator.id,
                locked = state.interactionLocked,
                onSave = { creatingIdentity = false; coordinator.createFixedRoute(it) },
                onClose = { creatingIdentity = false },
            )
        }
        versionRouteId?.let { id ->
            page?.items?.firstOrNull { it.id == id }?.let { route ->
                RouteVersionEditor(
                    route = route,
                    activeFares = snapshot.fixedRouteFareOptions,
                    locked = state.interactionLocked,
                    onSave = { versionRouteId = null; coordinator.createFixedRouteVersion(route, it) },
                    onClose = { versionRouteId = null },
                )
            }
        }
    }
    pendingVersion?.let { (version, target) ->
        RouteCommandDialog(
            title = when (target) {
                "PUBLISHED" -> "Publish ${version.routeCode}?"
                "RETIRED" -> "Retire ${version.routeCode} ${version.version}?"
                else -> "Submit ${version.routeCode} for review?"
            },
            detail = if (target == "PUBLISHED") {
                "The backend will revalidate the active assignment, service area, fare period, endpoint alignment, stops, and complete geometry before publication."
            } else {
                "This audited command changes lifecycle state only after backend confirmation."
            },
            busy = state.interactionLocked,
            onConfirm = { pendingVersion = null; coordinator.transitionFixedRouteVersion(version, target, it) },
            onDismiss = { pendingVersion = null },
        )
    }
    retiringRoute?.let { route ->
        RouteCommandDialog(
            title = "Retire route ${route.code}?",
            detail = "The identity and all non-retired versions become unavailable for new booking; historical rides remain intact.",
            busy = state.interactionLocked,
            onConfirm = { retiringRoute = null; coordinator.retireFixedRoute(route, it) },
            onDismiss = { retiringRoute = null },
        )
    }
}

@Composable
private fun RouteScopeBanner(city: String, operator: String, assignmentReady: Boolean) {
    Surface(
        color = if (assignmentReady) TaxiColors.Info100 else TaxiColors.Warning100,
        shape = RoundedCornerShape(TaxiRadii.Md),
        border = BorderStroke(
            1.dp,
            (if (assignmentReady) TaxiColors.Info600 else TaxiColors.Warning600).copy(alpha = 0.25f),
        ),
    ) {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md)) {
            Text("$city · $operator", fontWeight = FontWeight.Bold)
            Text(
                if (assignmentReady) "Active fixed-route assignment visible; publication still revalidates its effective period."
                else "No active fixed-route assignment is visible. The backend will reject route drafting or publication.",
                color = if (assignmentReady) TaxiColors.Info600 else TaxiColors.Warning600,
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}

@Composable
private fun FixedRouteCard(
    route: FixedRouteRecord,
    locked: Boolean,
    onNewVersion: () -> Unit,
    onTransition: (FixedRouteVersionRecord, String) -> Unit,
    onRetire: () -> Unit,
) {
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text(route.code, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text("Stable route identity · ${route.versions.size} visible version(s)", color = TaxiColors.Ink500)
                }
                StatusBadge(route.status)
            }
            route.versions.forEach { version ->
                Surface(
                    color = TaxiColors.Surface2,
                    shape = RoundedCornerShape(TaxiRadii.Md),
                    border = BorderStroke(1.dp, TaxiColors.StrokeSubtle),
                ) {
                    Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Md), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Column {
                                Text(version.localizedName.preferred(), fontWeight = FontWeight.Bold)
                                Text("${version.version} · backend revision ${version.optimisticVersion}", style = MaterialTheme.typography.bodySmall)
                            }
                            StatusBadge(version.status)
                        }
                        version.directions.forEach { direction ->
                            val fareLabel = if (direction.flatFare != null && direction.currency != null) {
                                "${direction.flatFare} ${direction.currency}"
                            } else {
                                "fare link pending · direction ${direction.id}"
                            }
                            Text(
                                "${direction.directionCode.replace('_', ' ')} · ${direction.startLocationName.preferred()} → ${direction.finishLocationName.preferred()} · $fareLabel",
                                color = if (direction.flatFare == null) TaxiColors.Warning600 else TaxiColors.Ink700,
                            )
                            GeometryPreview(direction.geometry.coordinates)
                            Text("${direction.stops.size} ordered stop(s) · booking ${if (direction.immediateBookingEnabled) "enabled" else "not enabled by active config"}", style = MaterialTheme.typography.bodySmall)
                        }
                        Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                            fixedRouteTargetFor(version.status)?.let { target ->
                                Button(onClick = { onTransition(version, target) }, enabled = !locked) {
                                    Text(if (target == "PUBLISHED") "Review publication" else "Submit for review")
                                }
                            }
                            if (version.status in setOf("IN_REVIEW", "PUBLISHED")) {
                                OutlinedButton(onClick = { onTransition(version, "RETIRED") }, enabled = !locked) { Text("Retire version") }
                            }
                        }
                    }
                }
            }
            if (route.status == "ACTIVE") {
                Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                    Button(onClick = onNewVersion, enabled = !locked) { Text("New content version") }
                    OutlinedButton(onClick = onRetire, enabled = !locked) { Text("Retire route") }
                }
            }
        }
    }
}

@Composable
private fun GeometryPreview(points: List<List<Double>>) {
    val valid = points.mapNotNull { point ->
        if (point.size == 2) point[0] to point[1] else null
    }
    Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Xs)) {
        Canvas(
            Modifier.fillMaxWidth().height(120.dp).background(Color(0xFFF3F4F6), RoundedCornerShape(TaxiRadii.Sm)),
        ) {
            if (valid.size < 2) return@Canvas
            val minX = valid.minOf { it.first }
            val maxX = valid.maxOf { it.first }
            val minY = valid.minOf { it.second }
            val maxY = valid.maxOf { it.second }
            fun offset(point: Pair<Double, Double>) = Offset(
                x = (size.width * (0.08f + 0.84f * ((point.first - minX) / (maxX - minX).takeIf { it != 0.0 }.orElse(1.0)).toFloat())),
                y = (size.height * (0.92f - 0.84f * ((point.second - minY) / (maxY - minY).takeIf { it != 0.0 }.orElse(1.0)).toFloat())),
            )
            valid.zipWithNext().forEach { (a, b) ->
                drawLine(Color.White, offset(a), offset(b), strokeWidth = 9f)
                drawLine(TaxiColors.Navy900, offset(a), offset(b), strokeWidth = 5f)
            }
            drawCircle(TaxiColors.Accent500, 8f, offset(valid.first()))
            drawCircle(TaxiColors.Navy900, 8f, offset(valid.last()))
        }
        Text("Neutral geometry preview · authoritative containment is validated by PostGIS", color = TaxiColors.Ink500, style = MaterialTheme.typography.labelSmall)
    }
}

private fun Double?.orElse(default: Double): Double = this ?: default

@Composable
private fun RouteIdentityEditor(
    operatorId: String,
    locked: Boolean,
    onSave: (FixedRouteCreateRequest) -> Unit,
    onClose: () -> Unit,
) {
    var code by remember(operatorId) { mutableStateOf("") }
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Text("Create stable route identity", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            OutlinedTextField(code, { code = it.uppercase().take(64) }, Modifier.fillMaxWidth(), label = { Text("Route code") }, enabled = !locked)
            Text(if (validRouteCode(code)) "Ready for backend validation." else "Use uppercase letters, numbers, underscore, or dash.", color = if (validRouteCode(code)) TaxiColors.Success600 else TaxiColors.Warning600)
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                Button(onClick = { onSave(FixedRouteCreateRequest(operatorId, code.trim())) }, enabled = validRouteCode(code) && !locked) { Text("Create identity") }
                TextButton(onClick = onClose, enabled = !locked) { Text("Close") }
            }
        }
    }
}

private data class RouteVersionDraft(
    val version: String = "",
    val nameEn: String = "",
    val nameFr: String = "",
    val nameAr: String = "",
    val descriptionEn: String = "",
    val descriptionFr: String = "",
    val descriptionAr: String = "",
    val effectiveFrom: String = "",
    val effectiveUntil: String = "",
    val directionCode: String = "OUTBOUND",
    val startEn: String = "",
    val startFr: String = "",
    val startAr: String = "",
    val finishEn: String = "",
    val finishFr: String = "",
    val finishAr: String = "",
    val startLatitude: String = "",
    val startLongitude: String = "",
    val finishLatitude: String = "",
    val finishLongitude: String = "",
    val geometry: String = "",
    val farePolicyId: String = "",
    val stops: String = "",
) {
    fun validation(): String? = when {
        !validPolicyVersion(version) -> "Enter a valid immutable content version."
        listOf(nameEn, nameFr, nameAr, startEn, startFr, startAr, finishEn, finishFr, finishAr).any { it.isBlank() } -> "Enter English, French, and Arabic route/start/finish labels."
        !validZonedTimestamp(effectiveFrom) -> "Effective from requires a zoned ISO 8601 timestamp."
        effectiveUntil.isNotBlank() && !validZonedTimestamp(effectiveUntil) -> "Effective until must be blank or zoned ISO 8601."
        directionCode !in setOf("OUTBOUND", "INBOUND") -> "Choose OUTBOUND or INBOUND."
        !validLatitude(startLatitude) || !validLatitude(finishLatitude) -> "Latitude must be between -90 and 90."
        !validLongitude(startLongitude) || !validLongitude(finishLongitude) -> "Longitude must be between -180 and 180."
        parseGeometry() == null -> "Geometry needs 2–500 lines formatted longitude,latitude with valid distinct points."
        parseStops() == null -> "Each stop line must be en|fr|ar|latitude|longitude; at most 50 stops."
        else -> null
    }

    fun toRequest(): FixedRouteVersionCreateRequest? {
        if (validation() != null) return null
        val geometryPoints = parseGeometry() ?: return null
        return FixedRouteVersionCreateRequest(
            version = version.trim(),
            localizedName = LocalizedName(nameEn.trim(), nameFr.trim(), nameAr.trim()),
            localizedDescription = if (listOf(descriptionEn, descriptionFr, descriptionAr).all { it.isBlank() }) null else
                LocalizedName(descriptionEn.trim(), descriptionFr.trim(), descriptionAr.trim()),
            effectiveFrom = effectiveFrom.trim(),
            effectiveUntil = effectiveUntil.trim().ifBlank { null },
            directions = listOf(
                FixedRouteDirectionDraftRequest(
                    directionCode = directionCode,
                    startLocationName = LocalizedName(startEn.trim(), startFr.trim(), startAr.trim()),
                    finishLocationName = LocalizedName(finishEn.trim(), finishFr.trim(), finishAr.trim()),
                    start = RouteCoordinateRecord(startLatitude.toDouble(), startLongitude.toDouble()),
                    finish = RouteCoordinateRecord(finishLatitude.toDouble(), finishLongitude.toDouble()),
                    geometry = LineStringRecord(coordinates = geometryPoints.map { listOf(it.first, it.second) }),
                    flatFarePolicyVersionId = farePolicyId.ifBlank { null },
                    stops = parseStops().orEmpty(),
                )
            ),
        )
    }

    fun parseGeometry(): List<Pair<Double, Double>>? {
        val points = geometry.lines().filter { it.isNotBlank() }.map { line ->
            val values = line.split(',').map(String::trim)
            if (values.size != 2 || !validLongitude(values[0]) || !validLatitude(values[1])) return null
            values[0].toDouble() to values[1].toDouble()
        }
        return points.takeIf { it.size in 2..500 && it.distinct().size >= 2 }
    }

    fun parseStops(): List<FixedRouteStopDraftRequest>? {
        val lines = stops.lines().filter { it.isNotBlank() }
        if (lines.size > 50) return null
        return lines.map { line ->
            val values = line.split('|').map(String::trim)
            if (values.size != 5 || values.take(3).any(String::isBlank) ||
                !validLatitude(values[3]) || !validLongitude(values[4])
            ) return null
            FixedRouteStopDraftRequest(
                localizedName = LocalizedName(values[0], values[1], values[2]),
                location = RouteCoordinateRecord(values[3].toDouble(), values[4].toDouble()),
            )
        }
    }
}

@Composable
private fun RouteVersionEditor(
    route: FixedRouteRecord,
    activeFares: List<FixedRouteFareOptionRecord>,
    locked: Boolean,
    onSave: (FixedRouteVersionCreateRequest) -> Unit,
    onClose: () -> Unit,
) {
    var draft by remember(route.id) { mutableStateOf(RouteVersionDraft()) }
    DataCard {
        Column(Modifier.fillMaxWidth().padding(TaxiSpacing.Lg), verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
            Text("New immutable version · ${route.code}", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            EditorField("Version", draft.version, locked) { draft = draft.copy(version = it.take(64)) }
            LocalizedFields("Route name", draft.nameEn, draft.nameFr, draft.nameAr, locked) { en, fr, ar -> draft = draft.copy(nameEn = en, nameFr = fr, nameAr = ar) }
            LocalizedFields("Description (all blank or all supplied)", draft.descriptionEn, draft.descriptionFr, draft.descriptionAr, locked) { en, fr, ar -> draft = draft.copy(descriptionEn = en, descriptionFr = fr, descriptionAr = ar) }
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                EditorField("Effective from", draft.effectiveFrom, locked, Modifier.weight(1f)) { draft = draft.copy(effectiveFrom = it) }
                EditorField("Effective until (optional)", draft.effectiveUntil, locked, Modifier.weight(1f)) { draft = draft.copy(effectiveUntil = it) }
            }
            ScopeMenu(
                label = "Direction",
                selected = draft.directionCode,
                options = listOf(ScopeOption("OUTBOUND", "Outbound"), ScopeOption("INBOUND", "Inbound")),
                enabled = !locked,
                onSelected = { it?.let { value -> draft = draft.copy(directionCode = value) } },
            )
            LocalizedFields("Start", draft.startEn, draft.startFr, draft.startAr, locked) { en, fr, ar -> draft = draft.copy(startEn = en, startFr = fr, startAr = ar) }
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                EditorField("Start latitude", draft.startLatitude, locked, Modifier.weight(1f)) { draft = draft.copy(startLatitude = it) }
                EditorField("Start longitude", draft.startLongitude, locked, Modifier.weight(1f)) { draft = draft.copy(startLongitude = it) }
            }
            LocalizedFields("Finish", draft.finishEn, draft.finishFr, draft.finishAr, locked) { en, fr, ar -> draft = draft.copy(finishEn = en, finishFr = fr, finishAr = ar) }
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                EditorField("Finish latitude", draft.finishLatitude, locked, Modifier.weight(1f)) { draft = draft.copy(finishLatitude = it) }
                EditorField("Finish longitude", draft.finishLongitude, locked, Modifier.weight(1f)) { draft = draft.copy(finishLongitude = it) }
            }
            OutlinedTextField(
                draft.geometry,
                { draft = draft.copy(geometry = it.take(12_000)) },
                Modifier.fillMaxWidth(),
                label = { Text("Geometry · one longitude,latitude point per line") },
                minLines = 4,
                enabled = !locked,
            )
            draft.parseGeometry()?.let { GeometryPreview(it.map { point -> listOf(point.first, point.second) }) }
            ScopeMenu(
                label = "Complete-direction fare",
                selected = activeFares.firstOrNull { it.id == draft.farePolicyId }?.let {
                    "${it.fixedAmount} ${it.currency} · ${it.version} · ${it.status.replace('_', ' ')}"
                } ?: "Link fare after geometry",
                options = listOf(ScopeOption("", "Link fare after geometry")) + activeFares.map {
                    ScopeOption(it.id, "${it.fixedAmount} ${it.currency} · ${it.version} · ${it.status.replace('_', ' ')}")
                },
                enabled = !locked,
                onSelected = { draft = draft.copy(farePolicyId = it.orEmpty()) },
            )
            Text(
                if (activeFares.isEmpty()) {
                    "No unbound fare draft is available. Create geometry now, then use its direction ID in Pricing & economics."
                } else {
                    "Only unbound draft/in-review fares appear here. Activation is separate and requires this one-to-one link."
                },
                color = TaxiColors.Ink500,
                style = MaterialTheme.typography.bodySmall,
            )
            OutlinedTextField(
                draft.stops,
                { draft = draft.copy(stops = it.take(12_000)) },
                Modifier.fillMaxWidth(),
                label = { Text("Stops (optional) · en|fr|ar|latitude|longitude per line") },
                minLines = 3,
                enabled = !locked,
            )
            val validation = draft.validation()
            Text(validation ?: "Ready for backend PostGIS and scope validation.", color = if (validation == null) TaxiColors.Success600 else TaxiColors.Warning600)
            Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
                Button(onClick = { draft.toRequest()?.let(onSave) }, enabled = validation == null && !locked) { Text("Create draft version") }
                TextButton(onClick = onClose, enabled = !locked) { Text("Close") }
            }
        }
    }
}

@Composable
private fun LocalizedFields(
    label: String,
    en: String,
    fr: String,
    ar: String,
    locked: Boolean,
    onChange: (String, String, String) -> Unit,
) {
    Text(label, fontWeight = FontWeight.Bold)
    Row(horizontalArrangement = Arrangement.spacedBy(TaxiSpacing.Sm)) {
        EditorField("English", en, locked, Modifier.weight(1f)) { onChange(it.take(120), fr, ar) }
        EditorField("French", fr, locked, Modifier.weight(1f)) { onChange(en, it.take(120), ar) }
        EditorField("Arabic", ar, locked, Modifier.weight(1f)) { onChange(en, fr, it.take(120)) }
    }
}

@Composable
private fun EditorField(
    label: String,
    value: String,
    locked: Boolean,
    modifier: Modifier = Modifier.fillMaxWidth(),
    onChange: (String) -> Unit,
) {
    OutlinedTextField(value, onChange, modifier, label = { Text(label) }, enabled = !locked, singleLine = true)
}

@Composable
private fun RouteCommandDialog(
    title: String,
    detail: String,
    busy: Boolean,
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    var reason by remember(title) { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = { if (!busy) onDismiss() },
        title = { Text(title) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(TaxiSpacing.Md)) {
                Text(detail)
                OutlinedTextField(reason, { reason = it.take(240) }, Modifier.fillMaxWidth(), label = { Text("Audited reason") }, enabled = !busy)
            }
        },
        confirmButton = { Button(onClick = { onConfirm(reason) }, enabled = reason.trim().length in 3..240 && !busy) { Text("Confirm") } },
        dismissButton = { TextButton(onClick = onDismiss, enabled = !busy) { Text("Cancel") } },
    )
}
