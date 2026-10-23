package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.SemanticsMatcher
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.App
import org.example.taximobile.app.AppRole
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverLocationObservation
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideStatus
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@OptIn(ExperimentalTestApi::class)
class DriverCompletionLocationUiTest {
    @Test
    fun board_completion_requires_a_location_without_exposing_manual_coordinates() = runComposeUiTest {
        val location = Coordinates(33.5731, -7.5898)
        var legacyCoordinateCalls = 0
        var completed: Pair<String, Coordinates>? = null
        setContent {
            Box(Modifier.size(400.dp, 800.dp)) {
                App(
                    appRole = AppRole.DRIVER,
                    state = AppUiState.DriverReady(
                        availability = DriverAvailabilityStatus.ON_RIDE,
                        activeRideId = "board-trip",
                        activeRide = RideStatus.IN_PROGRESS,
                    ),
                    showManualCoordinateEntry = false,
                    onRequestCurrentLocation = { legacyCoordinateCalls += 1; it(null) },
                    onRequestDriverObservation = { it(DriverLocationObservation(location, System.currentTimeMillis(), 5.0)) },
                    onCompleteDriverRide = { rideId, coordinates -> completed = rideId to coordinates },
                )
            }
        }
        onAllNodesWithText("Completion latitude").assertCountEquals(0)
        onAllNodesWithText("Completion longitude").assertCountEquals(0)
        onAllNodesWithText("Scheduled work (0 offers · 0 commitments)").assertCountEquals(0)
        onNodeWithText("Complete ride").performScrollTo().assertIsNotEnabled()
        onNodeWithText("Load completion location").performScrollTo().performClick()
        assertEquals(0, legacyCoordinateCalls, "Driver completion must use the guarded driver observation lookup")
        onNodeWithText("Complete ride").performScrollTo().performClick()
        assertEquals("board-trip" to location, completed)
    }

    @Test
    fun completion_waits_for_one_observation_and_never_completes_automatically() = runComposeUiTest {
        var callback: ((DriverLocationObservation?) -> Unit)? = null
        var requests = 0
        var completions = 0
        setContent {
            Box(Modifier.size(400.dp, 800.dp)) {
                App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.ON_RIDE,
                    activeRideId = "board-trip", activeRide = RideStatus.IN_PROGRESS,
                ), showManualCoordinateEntry = false,
                    onRequestDriverObservation = { requests += 1; callback = it },
                    onCompleteDriverRide = { _, _ -> completions += 1 },
                )
            }
        }
        onNodeWithText("Load completion location").performScrollTo().performClick()
        assertEquals(1, requests)
        val busyControls = onAllNodes(SemanticsMatcher.expectValue(SemanticsProperties.StateDescription, "Loading"))
            .fetchSemanticsNodes()
        assertTrue(busyControls.isNotEmpty(), "Acquisition must expose its loading state")
        assertTrue(busyControls.all { it.config.contains(SemanticsProperties.Disabled) },
            "Every loading location control must reject duplicate acquisition")
        onNodeWithText("Complete ride").performScrollTo().assertIsNotEnabled()
        runOnIdle { requireNotNull(callback)(DriverLocationObservation(Coordinates(33.5731, -7.5898), System.currentTimeMillis(), 5.0)) }
        onNodeWithText("Complete ride").performScrollTo().assertIsEnabled()
        assertEquals(0, completions, "Location acquisition is not a completion command")
    }

    @Test
    fun failed_lookup_can_be_explicitly_retried_without_replaying_completion() = runComposeUiTest {
        var requests = 0
        var completions = 0
        val location = Coordinates(33.5731, -7.5898)
        setContent {
            Box(Modifier.size(400.dp, 800.dp)) {
                App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.ON_RIDE,
                    activeRideId = "board-trip", activeRide = RideStatus.IN_PROGRESS,
                ), showManualCoordinateEntry = false,
                    onRequestDriverObservation = {
                        requests += 1
                        it(if (requests == 1) null else DriverLocationObservation(location, System.currentTimeMillis(), 5.0))
                    },
                    onCompleteDriverRide = { _, coordinates -> assertEquals(location, coordinates); completions += 1 },
                )
            }
        }
        onNodeWithText("Load completion location").performScrollTo().performClick()
        onNodeWithText("Location unavailable. Enable location and try again.").performScrollTo().assertIsEnabled()
        onNodeWithText("Complete ride").performScrollTo().assertIsNotEnabled()
        onNodeWithText("Load completion location").performScrollTo().performClick()
        assertEquals(2, requests)
        assertEquals(0, completions, "A successful retry remains a read, never a completion command")
        onNodeWithText("Complete ride").performScrollTo().assertIsEnabled().performClick()
        assertEquals(1, completions)
    }

    @Test
    fun map_only_completion_failure_does_not_instruct_hidden_manual_entry() = runComposeUiTest {
        var completions = 0
        setContent {
            Box(Modifier.size(400.dp, 800.dp)) {
                App(appRole = AppRole.DRIVER, state = AppUiState.DriverReady(
                    availability = DriverAvailabilityStatus.ON_RIDE,
                    activeRideId = "board-trip", activeRide = RideStatus.IN_PROGRESS,
                ), showManualCoordinateEntry = false,
                    onRequestDriverObservation = { it(null) },
                    onCompleteDriverRide = { _, _ -> completions += 1 },
                )
            }
        }
        onNodeWithText("Load completion location").performScrollTo().performClick()
        onNodeWithText("Location unavailable. Enable location and try again.").performScrollTo().assertIsEnabled()
        onAllNodesWithText("Completion latitude").assertCountEquals(0)
        onAllNodesWithText("Completion longitude").assertCountEquals(0)
        onNodeWithText("Complete ride").performScrollTo().assertIsNotEnabled()
        assertEquals(0, completions)
    }
}
