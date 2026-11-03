package org.example.taximobile

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.location.LocationManagerCompat
import androidx.core.location.LocationListenerCompat
import androidx.core.location.LocationRequestCompat
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.drivers.DriverLocationObservation
import org.example.taximobile.feature.location.OneShotLocationGate
import org.example.taximobile.feature.location.nativeFixAcquiredAfterRequest

/**
 * Performs one foreground-only location lookup.
 *
 * Driver observations wait for one newly acquired fix with a bounded listener;
 * it is removed on success, timeout or foreground exit. No location history or
 * background service is retained. User requests may ask for when-in-use permission;
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
    private var pendingResult: ((DriverLocationObservation?) -> Unit)? = null
    private var cancellationSignal: CancellationSignal? = null
    private var fallbackLocation: Location? = null
    private var requiresFreshFix = true
    private var freshLocationListener: LocationListenerCompat? = null

    private val permissionLauncher = activity.registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { grants ->
        val granted = grants[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            grants[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        if (pendingResult != null) {
            if (granted) loadCurrentLocation() else finish(null)
        }
    }

    private val timeout = Runnable { finish(fallbackLocation?.toObservation()) }

    fun request(onResult: (Coordinates?) -> Unit) {
        startObservation(requireFresh = false) { onResult(it?.coordinates) }
    }

    fun requestObservation(onResult: (DriverLocationObservation?) -> Unit) {
        startObservation(requireFresh = true, onResult)
    }

    private fun startObservation(requireFresh: Boolean, onResult: (DriverLocationObservation?) -> Unit) {
        if (!requestGate.tryStart()) {
            onResult(null)
            return
        }
        pendingResult = onResult
        requiresFreshFix = requireFresh
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

    fun requestAuthorized(onResult: (DriverLocationObservation?) -> Unit): Boolean {
        if (!hasLocationPermission()) {
            onResult(null)
            return true
        }
        if (!requestGate.tryStart()) return false
        pendingResult = onResult
        requiresFreshFix = true
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
            mainHandler.postDelayed(timeout, CURRENT_LOCATION_TIMEOUT_MILLIS)
            if (requiresFreshFix) {
                fallbackLocation = null
                val requestStartedNanos = SystemClock.elapsedRealtimeNanos()
                val listener = object : LocationListenerCompat {
                    override fun onLocationChanged(location: Location) {
                        if (freshLocationListener !== this || !nativeFixAcquiredAfterRequest(
                                requestStartedNanos, location.elapsedRealtimeNanos, SystemClock.elapsedRealtimeNanos(),
                            )) return
                        val observation = location.toObservation()
                        if (observation.isUsableAt(System.currentTimeMillis())) finish(observation)
                    }
                }
                freshLocationListener = listener
                LocationManagerCompat.requestLocationUpdates(
                    locationManager, provider,
                    LocationRequestCompat.Builder(1_000L)
                        .setQuality(LocationRequestCompat.QUALITY_HIGH_ACCURACY)
                        .setMinUpdateIntervalMillis(0L)
                        .setDurationMillis(CURRENT_LOCATION_TIMEOUT_MILLIS)
                        .build(),
                    ContextCompat.getMainExecutor(activity), listener,
                )
                return
            }
            fallbackLocation = listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)
                .mapNotNull { candidate -> runCatching { locationManager.getLastKnownLocation(candidate) }.getOrNull() }
                .filter { location -> System.currentTimeMillis() - location.time <= LAST_LOCATION_MAX_AGE_MILLIS }
                .maxByOrNull(Location::getTime)

            val requestCancellation = CancellationSignal()
            cancellationSignal = requestCancellation
            LocationManagerCompat.getCurrentLocation(
                locationManager,
                provider,
                requestCancellation,
                ContextCompat.getMainExecutor(activity),
            ) { location ->
                if (cancellationSignal === requestCancellation) {
                    finish(location?.toObservation() ?: fallbackLocation?.toObservation())
                }
            }
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

    private fun finish(location: DriverLocationObservation?) {
        mainHandler.removeCallbacks(timeout)
        cancellationSignal?.cancel()
        cancellationSignal = null
        val listener = freshLocationListener
        freshLocationListener = null
        if (listener != null) {
            try {
                LocationManagerCompat.removeUpdates(locationManager, listener)
            } catch (_: SecurityException) {
                // Permission revocation has already removed authorization.
            }
        }
        fallbackLocation = null
        val result = pendingResult
        pendingResult = null
        requestGate.finish()
        result?.invoke(location)
    }

    fun cancelPending() = finish(null)

    private fun Location.toObservation(): DriverLocationObservation {
        // elapsedRealtimeNanos is monotonic: a cached fix cannot inherit the
        // wall-clock time at which a delayed callback happens to be delivered.
        val ageNanos = SystemClock.elapsedRealtimeNanos() - elapsedRealtimeNanos
        return DriverLocationObservation(
            coordinates = Coordinates(latitude, longitude),
            observedAtEpochMillis = System.currentTimeMillis() - ageNanos / 1_000_000L,
            accuracyMeters = if (hasAccuracy()) accuracy.toDouble() else Double.NaN,
        )
    }

    private companion object {
        const val CURRENT_LOCATION_TIMEOUT_MILLIS = 15_000L
        const val LAST_LOCATION_MAX_AGE_MILLIS = 2 * 60_000L
    }
}
