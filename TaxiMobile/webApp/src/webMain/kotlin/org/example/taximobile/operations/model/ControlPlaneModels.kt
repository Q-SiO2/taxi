package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlin.time.Instant

const val MANAGE_OPERATORS = "manage_operators"
const val MANAGE_OPERATOR_ASSIGNMENTS = "manage_operator_assignments"
const val MANAGE_CITY_CONFIGURATION = "manage_city_configuration"
const val MANAGE_SERVICE_AREAS = "manage_service_areas"

@Serializable
data class CityCreateRequest(
    @SerialName("market_id") val marketId: String,
    val code: String,
    @SerialName("localized_name") val localizedName: LocalizedName,
    val timezone: String,
    @SerialName("presentation_centroid") val presentationCentroid: Coordinate,
)

@Serializable
data class OperatorCreateRequest(
    @SerialName("market_id") val marketId: String,
    @SerialName("cooperative_id") val cooperativeId: String? = null,
    val name: String,
    @SerialName("operator_type") val operatorType: String,
)

@Serializable
data class OperatorStatusUpdateRequest(val status: String)

@Serializable
data class OperatorCityAssignmentCreateRequest(
    @SerialName("operator_id") val operatorId: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("service_type") val serviceType: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
)

@Serializable
data class OperatorCityAssignmentRetireRequest(val reason: String)

@Serializable
data class ServiceAreaVersionCreateRequest(
    val version: String,
    val boundary: MultiPolygonGeometry,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
)

@Serializable
data class ServiceAreaTransitionRequest(
    @SerialName("target_status") val targetStatus: String,
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

@Serializable
data class ConfigurationServiceInput(
    @SerialName("service_type") val serviceType: String,
    @SerialName("operator_city_assignment_id") val operatorCityAssignmentId: String,
    @SerialName("tariff_version_id") val tariffVersionId: String? = null,
    @SerialName("operator_fee_policy_version_id") val operatorFeePolicyVersionId: String? = null,
    @SerialName("scheduling_policy_version_id") val schedulingPolicyVersionId: String? = null,
    @SerialName("payment_capability_version_id") val paymentCapabilityVersionId: String? = null,
    val enabled: Boolean = true,
)

@Serializable
data class ConfigurationRouteInput(
    @SerialName("fixed_route_version_id") val fixedRouteVersionId: String,
    @SerialName("immediate_booking_enabled") val immediateBookingEnabled: Boolean = true,
    @SerialName("scheduled_booking_enabled") val scheduledBookingEnabled: Boolean = false,
)

@Serializable
data class CityConfigurationCreateRequest(
    val version: String,
    @SerialName("service_area_version_id") val serviceAreaVersionId: String,
    @SerialName("driver_requirement_version_id") val driverRequirementVersionId: String? = null,
    val services: List<ConfigurationServiceInput>,
    val routes: List<ConfigurationRouteInput> = emptyList(),
)

@Serializable
data class ConfigurationCommandRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

fun serviceAreaTargetFor(status: String): String? = when (status) {
    "DRAFT" -> "IN_REVIEW"
    "IN_REVIEW" -> "APPROVED"
    else -> null
}

fun configurationTargetFor(status: String): String? = when (status) {
    "DRAFT" -> "IN_REVIEW"
    "IN_REVIEW" -> "APPROVED"
    "APPROVED" -> "ACTIVE"
    else -> null
}

fun operatorStatusTargetsFor(status: String): List<String> = when (status) {
    "DRAFT" -> listOf("ACTIVE", "INACTIVE")
    "ACTIVE" -> listOf("INACTIVE")
    "INACTIVE" -> listOf("ACTIVE")
    else -> emptyList()
}

data class BoundaryParseResult(
    val boundary: MultiPolygonGeometry? = null,
    val error: String? = null,
)

/**
 * Converts one user-entered WGS84 polygon into the GeoJSON-shaped multi-polygon
 * required by the backend. Each non-empty line must be `longitude,latitude`.
 * The closing point is added automatically so operators never have to edit JSON.
 */
fun parseServiceAreaBoundary(value: String): BoundaryParseResult {
    val points = mutableListOf<List<Double>>()
    value.lineSequence().forEachIndexed { index, rawLine ->
        val line = rawLine.trim()
        if (line.isEmpty()) return@forEachIndexed
        val parts = line.split(',').map(String::trim)
        if (parts.size != 2) {
            return BoundaryParseResult(error = "Line ${index + 1} must contain longitude,latitude.")
        }
        val longitude = parts[0].toDoubleOrNull()
            ?: return BoundaryParseResult(error = "Line ${index + 1} has an invalid longitude.")
        val latitude = parts[1].toDoubleOrNull()
            ?: return BoundaryParseResult(error = "Line ${index + 1} has an invalid latitude.")
        if (longitude !in -180.0..180.0 || latitude !in -90.0..90.0) {
            return BoundaryParseResult(error = "Line ${index + 1} is outside WGS84 coordinate bounds.")
        }
        points += listOf(longitude, latitude)
    }
    val distinct = points.distinct()
    if (distinct.size < 3) {
        return BoundaryParseResult(error = "Enter at least three distinct boundary points.")
    }
    val signedArea = distinct.indices.sumOf { index ->
        val current = distinct[index]
        val next = distinct[(index + 1) % distinct.size]
        current[0] * next[1] - next[0] * current[1]
    }
    if (kotlin.math.abs(signedArea) < 0.000000000001) {
        return BoundaryParseResult(error = "Boundary points must form a polygon with a non-zero area.")
    }
    val ring = points.toMutableList().apply {
        if (first() != last()) add(first())
    }
    return BoundaryParseResult(
        boundary = MultiPolygonGeometry(
            type = "MultiPolygon",
            coordinates = listOf(listOf(ring)),
        )
    )
}

fun validControlPlaneVersion(value: String): Boolean =
    Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$").matches(value.trim())

fun validControlPlaneEffectiveRange(effectiveFrom: String, effectiveUntil: String): Boolean {
    if (!validZonedTimestamp(effectiveFrom)) return false
    if (effectiveUntil.isBlank()) return true
    if (!validZonedTimestamp(effectiveUntil)) return false
    return runCatching {
        Instant.parse(normalizeControlPlaneInstant(effectiveUntil)) >
            Instant.parse(normalizeControlPlaneInstant(effectiveFrom))
    }.getOrDefault(false)
}

private fun normalizeControlPlaneInstant(value: String): String {
    val normalized = value.trim()
    return if (Regex("T\\d{2}:\\d{2}(Z|[+-]\\d{2}:\\d{2})$").containsMatchIn(normalized)) {
        normalized.replace(Regex("(Z|[+-]\\d{2}:\\d{2})$")) { match -> ":00${match.value}" }
    } else normalized
}
