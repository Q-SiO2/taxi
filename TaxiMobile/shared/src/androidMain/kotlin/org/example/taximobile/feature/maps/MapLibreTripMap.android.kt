package org.example.taximobile.feature.maps

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlin.time.Duration.Companion.milliseconds
import org.example.taximobile.domain.rides.Coordinates
import org.maplibre.compose.camera.CameraPosition
import org.maplibre.compose.camera.rememberCameraState
import org.maplibre.compose.expressions.dsl.const
import org.maplibre.compose.layers.CircleLayer
import org.maplibre.compose.layers.LineLayer
import org.maplibre.compose.map.MaplibreMap
import org.maplibre.compose.sources.GeoJsonData
import org.maplibre.compose.sources.rememberGeoJsonSource
import org.maplibre.compose.style.BaseStyle
import org.maplibre.compose.util.ClickResult
import org.maplibre.spatialk.geojson.BoundingBox
import org.maplibre.spatialk.geojson.Position
import org.example.taximobile.feature.ui.theme.TaxiColors

@Composable
actual fun MapLibreTripMap(
    pickup: Coordinates?,
    destination: Coordinates?,
    driverLocation: Coordinates?,
    routeGeometry: List<Coordinates>,
    styleUrl: String?,
    cameraFocusRequest: Int,
    onMapAvailabilityChanged: (Boolean) -> Unit,
    onCoordinateSelected: (Coordinates) -> Unit,
    modifier: Modifier,
) {
    val initialTarget = driverLocation ?: pickup ?: destination ?: DefaultTaxiMobileMapCenter
    val cameraState = rememberCameraState(
        firstPosition = CameraPosition(
            target = Position(latitude = initialTarget.latitude, longitude = initialTarget.longitude),
            zoom = 12.0,
        ),
    )
    val focusPoints = mapCameraFocusPoints(pickup, destination, driverLocation, routeGeometry)
    var usingFallbackStyle by remember(styleUrl) { mutableStateOf(styleUrl.isNullOrBlank()) }

    LaunchedEffect(usingFallbackStyle) {
        if (usingFallbackStyle) onMapAvailabilityChanged(false)
    }

    LaunchedEffect(cameraFocusRequest, focusPoints) {
        cameraState.awaitProjection()
        val bounds = mapCameraBounds(focusPoints)
        if (bounds != null && (bounds.west != bounds.east || bounds.south != bounds.north)) {
            cameraState.animateTo(
                boundingBox = BoundingBox(bounds.west, bounds.south, bounds.east, bounds.north),
                padding = PaddingValues(48.dp),
                duration = 300.milliseconds,
            )
        } else {
            focusPoints.firstOrNull()?.let { point ->
                cameraState.animateTo(
                    CameraPosition(
                        target = Position(latitude = point.latitude, longitude = point.longitude),
                        zoom = 15.0,
                    ),
                    duration = 300.milliseconds,
                )
            }
        }
    }

    MaplibreMap(
        modifier = modifier,
        baseStyle = if (usingFallbackStyle) {
            BaseStyle.Json(TaxiMobileFallbackMapStyleJson)
        } else {
            BaseStyle.Uri(requireNotNull(styleUrl))
        },
        cameraState = cameraState,
        onMapLoadFailed = {
            if (!usingFallbackStyle) usingFallbackStyle = true
            onMapAvailabilityChanged(false)
        },
        onMapLoadFinished = {
            if (!usingFallbackStyle) onMapAvailabilityChanged(true)
        },
        onMapClick = { position, _ ->
            onCoordinateSelected(Coordinates(position.latitude, position.longitude))
            ClickResult.Consume
        },
    ) {
        val pickupSource = rememberGeoJsonSource(GeoJsonData.JsonString(pointGeoJson(pickup)))
        val destinationSource = rememberGeoJsonSource(GeoJsonData.JsonString(pointGeoJson(destination)))
        val driverLocationSource = rememberGeoJsonSource(GeoJsonData.JsonString(pointGeoJson(driverLocation)))
        val routeSource = rememberGeoJsonSource(GeoJsonData.JsonString(routeGeoJson(routeGeometry)))

        LineLayer(
            id = "taximobile-route-halo",
            source = routeSource,
            color = const(TaxiColors.Surface0),
            width = const(8.dp),
        )
        LineLayer(
            id = "taximobile-route",
            source = routeSource,
            color = const(TaxiColors.Navy900),
            width = const(5.dp),
        )
        CircleLayer(
            id = "taximobile-pickup",
            source = pickupSource,
            color = const(TaxiColors.Accent500),
            radius = const(7.dp),
            strokeColor = const(TaxiColors.Surface0),
            strokeWidth = const(2.dp),
        )
        CircleLayer(
            id = "taximobile-destination",
            source = destinationSource,
            color = const(TaxiColors.Navy900),
            radius = const(7.dp),
            strokeColor = const(TaxiColors.Surface0),
            strokeWidth = const(2.dp),
        )
        CircleLayer(
            id = "taximobile-last-known-driver",
            source = driverLocationSource,
            color = const(TaxiColors.Navy900),
            radius = const(9.dp),
            strokeColor = const(TaxiColors.Accent500),
            strokeWidth = const(3.dp),
        )
    }
}

private fun pointGeoJson(point: Coordinates?): String = if (point == null) {
    """{"type":"FeatureCollection","features":[]}"""
} else {
    """{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"Point","coordinates":[${point.longitude},${point.latitude}]}}]}"""
}

private fun routeGeoJson(route: List<Coordinates>): String {
    if (route.size < 2) return """{"type":"FeatureCollection","features":[]}"""
    val coordinates = route.joinToString(",") { "[${it.longitude},${it.latitude}]" }
    return """{"type":"FeatureCollection","features":[{"type":"Feature","properties":{},"geometry":{"type":"LineString","coordinates":[$coordinates]}}]}"""
}
