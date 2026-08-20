package org.example.taximobile.feature.connectivity

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertSame
import kotlin.test.assertTrue
import kotlinx.coroutines.runBlocking
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_network_unavailable

class ConnectivityTest {
    @Test
    fun recovery_refreshes_once_only_after_an_unavailable_to_available_edge() {
        val policy = ConnectivityRecoveryPolicy()

        assertFalse(policy.shouldRefresh(ConnectivityStatus.UNKNOWN))
        assertFalse(policy.shouldRefresh(ConnectivityStatus.AVAILABLE))
        assertFalse(policy.shouldRefresh(ConnectivityStatus.AVAILABLE))
        assertFalse(policy.shouldRefresh(ConnectivityStatus.UNAVAILABLE))
        assertFalse(policy.shouldRefresh(ConnectivityStatus.UNAVAILABLE))
        assertTrue(policy.shouldRefresh(ConnectivityStatus.AVAILABLE))
        assertFalse(policy.shouldRefresh(ConnectivityStatus.AVAILABLE))
    }

    @Test
    fun initial_network_failure_uses_the_dedicated_offline_state() {
        val failure = AppUiState.Offline(UiMessage(Res.string.message_network_unavailable))

        val result = AppStatePresentation(AppUiState.RestoringSession).accept(failure)

        assertSame(failure, result.state)
        assertNull(result.connectionIssue)
    }

    @Test
    fun network_failure_retains_backend_confirmed_passenger_content() {
        val ready = AppUiState.PassengerReady(activeRideId = "ride-1")
        val failure = AppUiState.Offline(UiMessage(Res.string.message_network_unavailable))

        val result = AppStatePresentation(ready).accept(failure)

        assertSame(ready, result.state)
        assertEquals(failure.message, result.connectionIssue)
    }

    @Test
    fun successful_refresh_replaces_retained_content_and_clears_issue() {
        val previous = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE)
        val failure = AppUiState.Offline(UiMessage(Res.string.message_network_unavailable))
        val refreshed = AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE)

        val result = AppStatePresentation(previous).accept(failure).accept(refreshed)

        assertIs<AppUiState.DriverReady>(result.state)
        assertEquals(DriverAvailabilityStatus.AVAILABLE, result.state.availability)
        assertNull(result.connectionIssue)
    }

    @Test
    fun uncertain_authenticated_action_runs_once_and_reloads_authoritative_state() = runBlocking {
        val previous = AppUiState.PassengerReady(activeRideId = "ride-before")
        val operationFailure = AppUiState.Offline(UiMessage(Res.string.message_network_unavailable))
        val authoritative = AppUiState.PassengerReady(activeRideId = "ride-after")
        var actionCalls = 0
        var restoreCalls = 0

        val result = AppStatePresentation(previous).performAuthenticatedAction(
            action = {
                actionCalls += 1
                operationFailure
            },
            restore = {
                restoreCalls += 1
                authoritative
            },
        )

        assertEquals(1, actionCalls)
        assertEquals(1, restoreCalls)
        assertSame(authoritative, result.state)
        assertEquals(operationFailure.message, result.connectionIssue)
    }

    @Test
    fun successful_authenticated_action_does_not_add_a_restore() = runBlocking {
        val previous = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE)
        val commandResult = AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE)
        var restoreCalls = 0

        val result = AppStatePresentation(previous).performAuthenticatedAction(
            action = { commandResult },
            restore = {
                restoreCalls += 1
                previous
            },
        )

        assertEquals(0, restoreCalls)
        assertSame(commandResult, result.state)
        assertNull(result.connectionIssue)
    }

    @Test
    fun only_a_non_error_authenticated_result_emits_backend_confirmation() = runBlocking {
        val previous = AppUiState.PassengerReady()
        var confirmations = 0

        AppStatePresentation(previous).performAuthenticatedAction(
            action = { AppUiState.PassengerReady(activeRideId = "ride-confirmed") },
            restore = { previous },
            onBackendConfirmed = { confirmations += 1 },
        )
        AppStatePresentation(previous).performAuthenticatedAction(
            action = { AppUiState.Offline(UiMessage(Res.string.message_network_unavailable)) },
            restore = { previous },
            onBackendConfirmed = { confirmations += 1 },
        )
        AppStatePresentation(previous).performAuthenticatedAction(
            action = { AppUiState.SignedOut() },
            restore = { previous },
            onBackendConfirmed = { confirmations += 1 },
        )

        assertEquals(1, confirmations)
    }

    @Test
    fun session_rejection_wins_over_authenticated_command_recovery() = runBlocking {
        val previous = AppUiState.PassengerReady(activeRideId = "ride-before")
        val operationFailure = AppUiState.Offline(UiMessage(Res.string.message_network_unavailable))
        val signedOut = AppUiState.SignedOut()

        val result = AppStatePresentation(previous).performAuthenticatedAction(
            action = { operationFailure },
            restore = { signedOut },
        )

        assertSame(signedOut, result.state)
        assertNull(result.connectionIssue)
    }

    @Test
    fun signed_out_action_failure_does_not_attempt_authenticated_recovery() = runBlocking {
        val operationFailure = AppUiState.Offline(UiMessage(Res.string.message_network_unavailable))
        var restoreCalls = 0

        val result = AppStatePresentation(AppUiState.SignedOut()).performAuthenticatedAction(
            action = { operationFailure },
            restore = {
                restoreCalls += 1
                AppUiState.PassengerReady()
            },
        )

        assertEquals(0, restoreCalls)
        assertSame(operationFailure, result.state)
        assertNull(result.connectionIssue)
    }

    @Test
    fun foreground_recovery_requires_a_real_background_transition() {
        val policy = ForegroundRecoveryPolicy()

        assertFalse(policy.shouldRefreshOnForeground())
        assertFalse(policy.shouldRefreshOnForeground())

        policy.onBackground()

        assertTrue(policy.shouldRefreshOnForeground())
        assertFalse(policy.shouldRefreshOnForeground())
    }

    @Test
    fun repeated_background_events_still_arm_only_one_foreground_refresh() {
        val policy = ForegroundRecoveryPolicy()

        policy.onBackground()
        policy.onBackground()

        assertTrue(policy.shouldRefreshOnForeground())
        assertFalse(policy.shouldRefreshOnForeground())
    }
}
