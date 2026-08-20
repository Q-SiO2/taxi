package org.example.taximobile.feature.maps

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import org.example.taximobile.domain.rides.Coordinates

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
    Box(modifier.background(Color(0xFFE7F0EF)).fillMaxSize(), contentAlignment = Alignment.Center) {
        Text("Interactive MapLibre selection is available in the Android and iOS apps.")
    }
}
