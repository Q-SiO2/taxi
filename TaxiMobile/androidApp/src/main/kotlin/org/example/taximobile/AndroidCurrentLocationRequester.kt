package org.example.taximobile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.location.LocationManagerCompat
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.feature.location.OneShotLocationGate

/**
 * Performs one foreground-only location lookup.
 *
 * It intentionally does not subscribe to continuous updates or retain location
 * history. User-initiated requests may ask for when-in-use permission;
 * foreground online refreshes use [requestAuthorized] and never open permission
 * UI. A recent platform location is used only as a timeout fallback, and the
 * caller decides whether to submit the returned coordinate to the backend.
 */
internal class AndroidCurrentLocationRequester(
    private val activity: ComponentActivity,
) {
    // The requester must register its permission contract before onStart, but
    // Activity system services are not safe to resolve from the constructor.
    private val locationManager: LocationManager by lazy {
        activity.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    }
    private val mainHandler = Handler(Looper.getMainLooper())
    private val requestGate = OneShotLocationGate()
    private var pendingResult: ((Coordinates?) -> Unit)? = null
    private var cancellationSignal: CancellationSignal? = null
    private var fallbackLocation: Location? = null

    private val permissionLauncher = activity.registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { grants ->
        val granted = grants[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            grants[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (granted) loadCurrentLocation() else finish(null)
    }

    private val timeout = Runnable { finish(fallbackLocation?.toCoordinates()) }

    fun request(onResult: (Coordinates?) -> Unit) {
        if (!requestGate.tryStart()) return
        pendingResult = onResult
        if (hasLocationPermission()) {
            loadCurrentLocation()
        } else {
            permissionLauncher.launch(
                arrayOf(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                ),
            )
        }
    }

    fun requestAuthorized(onResult: (Coordinates?) -> Unit): Boolean {
        if (!hasLocationPermission()) {
            onResult(null)
            return true
        }
        if (!requestGate.tryStart()) return false
        pendingResult = onResult
        loadCurrentLocation()
        return true
    }

    private fun loadCurrentLocation() {
        if (!hasLocationPermission()) {
            finish(null)
            return
        }

        val provider = preferredEnabledProvider() ?: run {
            finish(null)
            return
        }

        try {
            fallbackLocation = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
                .mapNotNull { candidate -> runCatching { locationManager.getLastKnownLocation(candidate) }.getOrNull() }
                .filter { location -> System.currentTimeMillis() - location.time <= LAST_LOCATION_MAX_AGE_MILLIS }
                .maxByOrNull(Location::getTime)

            cancellationSignal = CancellationSignal()
            mainHandler.postDelayed(timeout, CURRENT_LOCATION_TIMEOUT_MILLIS)
            LocationManagerCompat.getCurrentLocation(
                locationManager,
                provider,
                cancellationSignal,
                ContextCompat.getMainExecutor(activity),
            ) { location -> finish(location?.toCoordinates() ?: fallbackLocation?.toCoordinates()) }
        } catch (_: SecurityException) {
            finish(null)
        } catch (_: IllegalArgumentException) {
            finish(null)
        }
    }

    private fun preferredEnabledProvider(): String? {
        val fineGranted = ContextCompat.checkSelfPermission(
            activity,
            Manifest.permission.ACCESS_FINE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED
        return when {
            fineGranted && locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            else -> null
        }
    }

    private fun hasLocationPermission(): Boolean =
        ContextCompat.checkSelfPermission(activity, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(activity, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun finish(location: Coordinates?) {
        mainHandler.removeCallbacks(timeout)
        cancellationSignal?.cancel()
        cancellationSignal = null
        fallbackLocation = null
        val result = pendingResult
        pendingResult = null
        requestGate.finish()
        result?.invoke(location)
    }

    private fun Location.toCoordinates(): Coordinates = Coordinates(latitude, longitude)

    private companion object {
        const val CURRENT_LOCATION_TIMEOUT_MILLIS = 15_000L
        const val LAST_LOCATION_MAX_AGE_MILLIS = 2 * 60_000L
    }
}
