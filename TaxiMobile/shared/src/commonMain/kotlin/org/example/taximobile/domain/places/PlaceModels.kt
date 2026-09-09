package org.example.taximobile.domain.places

import org.example.taximobile.domain.rides.Coordinates

enum class PlaceKind { ADDRESS, STREET, LOCALITY, POI, OTHER, UNKNOWN }

data class PlaceAttribution(
    val text: String,
    val url: String,
)

data class PlaceResult(
    val id: String,
    val primaryText: String,
    val secondaryText: String?,
    val coordinate: Coordinates,
    val kind: PlaceKind,
    /** Exact backend/PostGIS decision for using this point as a pickup. */
    val pickupServiceable: Boolean,
) {
    fun selectedCoordinates(): Coordinates = coordinate.copy(
        address = listOfNotNull(primaryText, secondaryText?.takeIf { it.isNotBlank() })
            .joinToString(", "),
    )
}

data class PlaceSearch(
    val cityId: String,
    val query: String,
    val items: List<PlaceResult>,
    val attribution: PlaceAttribution,
)

data class ReversePlace(
    val cityId: String,
    val item: PlaceResult?,
    val attribution: PlaceAttribution,
)

interface PlaceDiscoveryGateway {
    suspend fun search(cityId: String, query: String): PlaceSearch
    suspend fun reverse(cityId: String, coordinate: Coordinates): ReversePlace
}
