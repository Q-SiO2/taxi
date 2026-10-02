package org.example.taximobile.feature.location

import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.feature.app.AppUiState

class ForegroundDriverLocationResultGuardTest {
    private val available = AppUiState.DriverReady(
        availability = DriverAvailabilityStatus.AVAILABLE,
        activeVehicleId = "vehicle-a",
        onlineCityId = "city-a",
        onlineServiceType = "ON_DEMAND",
    )

    @Test
    fun unchanged_foreground_context_accepts_success_or_failure_callback() {
        val guard = ForegroundDriverLocationResultGuard()
        val request = guard.capture(available)
        assertTrue(guard.canApply(request, available.copy(displayName = "Refreshed"), true, true, false))
    }

    @Test
    fun background_network_loss_and_commands_reject_completion() {
        val guard = ForegroundDriverLocationResultGuard()
        val request = guard.capture(available)
        assertFalse(guard.canApply(request, available, false, true, false))
        assertFalse(guard.canApply(request, available, true, false, false))
        assertFalse(guard.canApply(request, available, true, true, true))
    }

    @Test
    fun invalidation_prevents_old_result_after_foreground_or_network_return() {
        val guard = ForegroundDriverLocationResultGuard()
        val request = guard.capture(available)
        guard.invalidate()
        assertFalse(guard.canApply(request, available, true, true, false))
        assertTrue(guard.canApply(guard.capture(available), available, true, true, false))
    }

    @Test
    fun logout_or_account_switch_cannot_receive_old_location_or_warning() {
        val guard = ForegroundDriverLocationResultGuard()
        val request = guard.capture(available)
        assertFalse(guard.canApply(request, AppUiState.SignedOut(), true, true, false))
        // Logout's admitted command invalidates even when another account later
        // exposes exactly the same vehicle/city/status presentation fields.
        guard.invalidate()
        assertFalse(guard.canApply(request, available.copy(), true, true, false))
    }

    @Test
    fun changed_server_operational_context_rejects_observation() {
        val guard = ForegroundDriverLocationResultGuard()
        val request = guard.capture(available)
        val changedStates = listOf(
            available.copy(activeVehicleId = "vehicle-b"),
            available.copy(onlineCityId = "city-b"),
            available.copy(onlineServiceType = "FIXED_ROUTE"),
            available.copy(activeRideId = "ride-b"),
            available.copy(availability = DriverAvailabilityStatus.OFFERED_RIDE),
            available.copy(availability = DriverAvailabilityStatus.OFFLINE),
            available.copy(availability = DriverAvailabilityStatus.PAUSED),
        )
        for (state in changedStates) {
            assertFalse(guard.canApply(request, state, true, true, false), state.toString())
        }
    }

    @Test
    fun all_active_ride_states_can_accept_their_own_context() {
        for (availability in ForegroundDriverLocationPolicy.OPERATIONAL_LOCATION_STATES) {
            val guard = ForegroundDriverLocationResultGuard()
            val state = available.copy(availability = availability, activeRideId = "ride-a")
            assertTrue(guard.canApply(guard.capture(state), state, true, true, false))
        }
    }

    @Test
    fun multiple_invalidations_do_not_revalidate_an_old_request() {
        val guard = ForegroundDriverLocationResultGuard()
        val old = guard.capture(available)
        repeat(5) { guard.invalidate() }
        val current = guard.capture(available)
        assertFalse(guard.canApply(old, available, true, true, false))
        assertTrue(guard.canApply(current, available, true, true, false))
        guard.invalidate()
        assertFalse(guard.canApply(current, available, true, true, false))
    }
}
