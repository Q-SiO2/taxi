package org.example.taximobile.feature.maps

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import org.example.taximobile.domain.rides.Coordinates

/** Platform MapLibre surface; shared state decides what a tap means. */
@Composable
expect fun MapLibreTripMap(
    pickup: Coordinates?,
    destination: Coordinates?,
    driverLocation: Coordinates? = null,
    routeGeometry: List<Coordinates>,
    styleUrl: String? = null,
    cameraFocusRequest: Int = 0,
    onMapAvailabilityChanged: (Boolean) -> Unit = {},
    onCoordinateSelected: (Coordinates) -> Unit,
    modifier: Modifier = Modifier,
)

/**
 * Network-independent fail-safe style. It deliberately contains no sprites,
 * glyphs, or remote sources: the route and markers remain usable over a calm
 * neutral canvas when the configured provider style cannot load.
 */
internal const val TaxiMobileFallbackMapStyleJson = """{
  "version": 8,
  "name": "TaxiMobile neutral fallback",
  "sources": {},
  "layers": [
    {
      "id": "taximobile-neutral-background",
      "type": "background",
      "paint": { "background-color": "#E9EDF2" }
    }
  ]
}"""
