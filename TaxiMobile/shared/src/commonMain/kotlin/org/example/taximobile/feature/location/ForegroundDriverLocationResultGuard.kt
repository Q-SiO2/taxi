package org.example.taximobile.feature.location

import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus

/**
 * Binds an automatic OS lookup to the foreground operational context that
 * started it. A callback is not authorization to upload under a later session.
 *
 * Platform roots invalidate immediately on background, connectivity changes,
 * and admission of any ordinary command (including logout). The context also
 * catches server refreshes that changed vehicle, city, service, ride or status.
 * All calls belong to the platform root's UI thread. This guard stores no
 * coordinates, credentials or location history and does not cancel OS work.
 */
class ForegroundDriverLocationResultGuard {
    private var generation = 0L

    class Request internal constructor(
        internal val generation: Long,
        internal val context: Context,
    )

    internal data class Context(
        val availability: DriverAvailabilityStatus,
        val vehicleId: String?,
        val cityId: String?,
        val serviceType: String?,
        val rideId: String?,
    )

    fun capture(state: AppUiState.DriverReady): Request = Request(generation, state.context())

    fun invalidate() {
        generation += 1
    }

    /** Applies equally to success and failure; obsolete failures must not warn a new session. */
    fun canApply(
        request: Request,
        state: AppUiState,
        appInForeground: Boolean,
        networkUsable: Boolean,
        appActionInFlight: Boolean,
    ): Boolean = request.generation == generation &&
        appInForeground && networkUsable && !appActionInFlight &&
        state is AppUiState.DriverReady &&
        state.availability in ForegroundDriverLocationPolicy.OPERATIONAL_LOCATION_STATES &&
        request.context == state.context()

    private fun AppUiState.DriverReady.context() = Context(
        availability, activeVehicleId, onlineCityId, onlineServiceType, activeRideId,
    )
}
