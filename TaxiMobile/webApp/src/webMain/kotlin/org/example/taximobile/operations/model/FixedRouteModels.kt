package org.example.taximobile.operations.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

const val MANAGE_FIXED_ROUTES = "manage_fixed_routes"

@Serializable
data class RouteCoordinateRecord(
    val latitude: Double,
    val longitude: Double,
)

@Serializable
data class LineStringRecord(
    val type: String = "LineString",
    val coordinates: List<List<Double>>,
)

@Serializable
data class FixedRouteStopRecord(
    val id: String,
    val sequence: Int,
    @SerialName("localized_name") val localizedName: LocalizedName,
    val location: RouteCoordinateRecord,
)

@Serializable
data class FixedRouteDirectionRecord(
    val id: String,
    @SerialName("direction_code") val directionCode: String,
    @SerialName("start_location_name") val startLocationName: LocalizedName,
    @SerialName("finish_location_name") val finishLocationName: LocalizedName,
    val start: RouteCoordinateRecord,
    val finish: RouteCoordinateRecord,
    val geometry: LineStringRecord,
    @SerialName("flat_fare_policy_version_id") val flatFarePolicyVersionId: String? = null,
    @SerialName("flat_fare") val flatFare: String? = null,
    val currency: String? = null,
    @SerialName("immediate_booking_enabled") val immediateBookingEnabled: Boolean,
    @SerialName("scheduled_booking_enabled") val scheduledBookingEnabled: Boolean,
    val stops: List<FixedRouteStopRecord> = emptyList(),
)

@Serializable
data class FixedRouteVersionRecord(
    val id: String,
    @SerialName("fixed_route_id") val fixedRouteId: String,
    @SerialName("route_code") val routeCode: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    val version: String,
    @SerialName("localized_name") val localizedName: LocalizedName,
    @SerialName("localized_description") val localizedDescription: Map<String, String> = emptyMap(),
    val status: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    @SerialName("optimistic_version") val optimisticVersion: Int,
    val directions: List<FixedRouteDirectionRecord>,
    @SerialName("submitted_at") val submittedAt: String? = null,
    @SerialName("published_at") val publishedAt: String? = null,
    @SerialName("retired_at") val retiredAt: String? = null,
)

@Serializable
data class FixedRouteRecord(
    val id: String,
    @SerialName("city_id") val cityId: String,
    @SerialName("operator_id") val operatorId: String,
    val code: String,
    val status: String,
    val versions: List<FixedRouteVersionRecord> = emptyList(),
)

@Serializable
data class FixedRouteFareOptionRecord(
    val id: String,
    val version: String,
    val name: String,
    val status: String,
    @SerialName("fixed_amount") val fixedAmount: String,
    val currency: String,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
)

@Serializable
data class FixedRouteFareOptionList(val items: List<FixedRouteFareOptionRecord>)

@Serializable
data class FixedRouteCreateRequest(
    @SerialName("operator_id") val operatorId: String,
    val code: String,
)

@Serializable
data class FixedRouteStopDraftRequest(
    @SerialName("localized_name") val localizedName: LocalizedName,
    val location: RouteCoordinateRecord,
)

@Serializable
data class FixedRouteDirectionDraftRequest(
    @SerialName("direction_code") val directionCode: String,
    @SerialName("start_location_name") val startLocationName: LocalizedName,
    @SerialName("finish_location_name") val finishLocationName: LocalizedName,
    val start: RouteCoordinateRecord,
    val finish: RouteCoordinateRecord,
    val geometry: LineStringRecord,
    @SerialName("flat_fare_policy_version_id") val flatFarePolicyVersionId: String? = null,
    val stops: List<FixedRouteStopDraftRequest> = emptyList(),
)

@Serializable
data class FixedRouteVersionCreateRequest(
    val version: String,
    @SerialName("localized_name") val localizedName: LocalizedName,
    @SerialName("localized_description") val localizedDescription: LocalizedName? = null,
    @SerialName("effective_from") val effectiveFrom: String,
    @SerialName("effective_until") val effectiveUntil: String? = null,
    val directions: List<FixedRouteDirectionDraftRequest>,
)

@Serializable
data class FixedRouteCommandRequest(
    @SerialName("expected_version") val expectedVersion: Int,
    val reason: String,
)

@Serializable
data class FixedRouteRetireRequest(val reason: String)

fun fixedRouteTargetFor(status: String): String? = when (status) {
    "DRAFT" -> "IN_REVIEW"
    "IN_REVIEW" -> "PUBLISHED"
    else -> null
}

fun validRouteCode(value: String): Boolean =
    Regex("^[A-Z0-9][A-Z0-9_-]{0,63}$").matches(value.trim().uppercase())

fun validLatitude(value: String): Boolean = value.trim().toDoubleOrNull()?.let { it in -90.0..90.0 } == true

fun validLongitude(value: String): Boolean = value.trim().toDoubleOrNull()?.let { it in -180.0..180.0 } == true
