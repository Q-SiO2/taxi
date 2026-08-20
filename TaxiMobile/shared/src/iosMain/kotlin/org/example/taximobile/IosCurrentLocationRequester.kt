package org.example.taximobile

import kotlinx.cinterop.ExperimentalForeignApi
import kotlinx.cinterop.useContents
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.feature.location.OneShotLocationGate
import platform.CoreLocation.CLAuthorizationStatus
import platform.CoreLocation.CLLocation
import platform.CoreLocation.CLLocationManager
import platform.CoreLocation.CLLocationManagerDelegateProtocol
import platform.CoreLocation.kCLAuthorizationStatusAuthorizedAlways
import platform.CoreLocation.kCLAuthorizationStatusAuthorizedWhenInUse
import platform.CoreLocation.kCLAuthorizationStatusDenied
import platform.CoreLocation.kCLAuthorizationStatusNotDetermined
import platform.CoreLocation.kCLAuthorizationStatusRestricted
import platform.CoreLocation.kCLLocationAccuracyBest
import platform.Foundation.NSError
import platform.darwin.NSObject

/** One-shot, foreground iOS location access. The app never starts background updates. */
@OptIn(ExperimentalForeignApi::class)
internal class IosCurrentLocationRequester : NSObject(), CLLocationManagerDelegateProtocol {
    private val manager = CLLocationManager().apply {
        desiredAccuracy = kCLLocationAccuracyBest
        delegate = this@IosCurrentLocationRequester
    }
    private val requestGate = OneShotLocationGate()
    private var pendingResult: ((Coordinates?) -> Unit)? = null

    fun request(onResult: (Coordinates?) -> Unit) {
        if (!requestGate.tryStart()) return
        pendingResult = onResult
        when (CLLocationManager.authorizationStatus()) {
            kCLAuthorizationStatusAuthorizedAlways,
            kCLAuthorizationStatusAuthorizedWhenInUse -> manager.requestLocation()
            kCLAuthorizationStatusNotDetermined -> manager.requestWhenInUseAuthorization()
            kCLAuthorizationStatusDenied,
            kCLAuthorizationStatusRestricted -> finish(null)
            else -> finish(null)
        }
    }

    override fun locationManager(
        manager: CLLocationManager,
        didChangeAuthorizationStatus: CLAuthorizationStatus,
    ) {
        when (didChangeAuthorizationStatus) {
            kCLAuthorizationStatusAuthorizedAlways,
            kCLAuthorizationStatusAuthorizedWhenInUse -> manager.requestLocation()
            kCLAuthorizationStatusDenied,
            kCLAuthorizationStatusRestricted -> finish(null)
            else -> Unit
        }
    }

    override fun locationManager(manager: CLLocationManager, didUpdateLocations: List<*>) {
        val location = didUpdateLocations.lastOrNull() as? CLLocation
        finish(location?.coordinate?.useContents { Coordinates(latitude, longitude) })
    }

    override fun locationManager(manager: CLLocationManager, didFailWithError: NSError) {
        finish(null)
    }

    private fun finish(location: Coordinates?) {
        val result = pendingResult
        pendingResult = null
        requestGate.finish()
        result?.invoke(location)
    }
}
