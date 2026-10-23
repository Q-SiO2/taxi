package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertTextContains
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextReplacement
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.App
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.FareEstimate
import kotlin.test.Test
import kotlin.test.assertEquals

/** Fresh native composition and subsequent local edits, not merely coordinator price retention. */
@OptIn(ExperimentalTestApi::class)
class PassengerQuoteRecreationUiTest {
    private val points = Coordinates(33.5731, -7.5898) to Coordinates(33.57561, -7.59063)
    private fun reviewed() = AppUiState.PassengerReady(
        reviewedPointQuoteInput = points,
        fareEstimate = FareEstimate("35.00", "MAD", "server-v1"),
    )

    @Test fun a_fresh_composition_recovers_reviewed_points_and_request_without_a_command() = runComposeUiTest {
        var commands = 0
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                App(state = reviewed(), placeSearchEnabled = false, showManualCoordinateEntry = false,
                    onRequestRide = { _, _, _ -> commands++ })
            }
        }
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Request taxi").performScrollTo().assertIsEnabled()
        onNodeWithText("35.00").assertExists()
        assertEquals(0, commands)
    }

    @Test fun refreshing_reviewed_terms_does_not_overwrite_an_existing_local_point_edit() = runComposeUiTest {
        val projection = mutableStateOf(reviewed())
        var commands = 0
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                App(state = projection.value, placeSearchEnabled = false, showManualCoordinateEntry = true,
                    onRequestRide = { _, _, _ -> commands++ })
            }
        }
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Request taxi").performScrollTo().assertIsEnabled()
        onNodeWithText("Destination latitude").performScrollTo().performTextReplacement("33.579")
        runOnIdle { projection.value = reviewed().copy(fareEstimate = FareEstimate("38.00", "MAD", "server-v2")) }
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Destination latitude").assertTextContains("33.579")
        onNodeWithText("Request taxi").assertDoesNotExist()
        onNodeWithText("Review fare").performScrollTo().assertIsEnabled()
        assertEquals(0, commands)
    }
}
