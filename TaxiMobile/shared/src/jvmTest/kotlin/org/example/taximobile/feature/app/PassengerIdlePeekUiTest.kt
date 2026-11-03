package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import androidx.compose.ui.test.getUnclippedBoundsInRoot
import androidx.compose.ui.test.onNodeWithTag
import org.example.taximobile.domain.rides.RideSummary
import org.example.taximobile.domain.rides.RideStatus
import kotlin.test.assertTrue
import org.example.taximobile.App
import kotlin.test.Test

@OptIn(ExperimentalTestApi::class)
class PassengerIdlePeekUiTest {
    @Test
    fun no_supply_retry_keeps_the_whole_primary_action_visible_at_320dp() = checkNoSupplyRetry(320, 640, 1f)

    @Test
    fun no_supply_retry_keeps_the_whole_primary_action_visible_with_large_text() = checkNoSupplyRetry(360, 760, 1.6f)

    private fun checkNoSupplyRetry(width: Int, height: Int, fontScale: Float) = runComposeUiTest {
        setContent {
            CompositionLocalProvider(LocalDensity provides Density(1f, fontScale)) {
                Box(Modifier.size(width.dp, height.dp)) {
                    App(state = AppUiState.PassengerReady(rideHistory = listOf(RideSummary("unmatched", RideStatus.UNMATCHED))),
                        placeSearchEnabled = false, showManualCoordinateEntry = false)
                }
            }
        }
        mainClock.advanceTimeBy(1000)
        val viewport = onNodeWithTag("taxi-sheet-scroll-content").getUnclippedBoundsInRoot()
        val action = onNodeWithText("Choose on the map").getUnclippedBoundsInRoot()
        assertTrue(action.top >= viewport.top && action.bottom <= viewport.bottom,
            "The retry action must be wholly visible without discovering a scroll gesture")
        onNodeWithText("Choose on the map").performClick()
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Review fare").assertIsNotEnabled()
    }
    @Test
    fun map_only_alpha_opens_selection_without_unavailable_place_search() = runComposeUiTest {
        var searches = 0
        var reverseLookups = 0
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                App(state = AppUiState.PassengerReady(), placeSearchEnabled = false,
                    showManualCoordinateEntry = false,
                    onSearchPlaces = { _, _ -> searches++ },
                    onReversePlace = { _, _ -> reverseLookups++ })
            }
        }
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Choose on the map").assertIsDisplayed().performClick()
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Find a place").assertDoesNotExist()
        onNodeWithText("Review fare").assertIsNotEnabled()
        kotlin.test.assertEquals(0, searches)
        kotlin.test.assertEquals(0, reverseLookups)
    }
    @Test
    fun idle_map_has_a_primary_place_action_before_expanding_the_full_form() = runComposeUiTest {
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                App(state = AppUiState.PassengerReady())
            }
        }
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Find a place").assertIsDisplayed().performClick()
        mainClock.advanceTimeBy(1000)
        onNodeWithText("Review fare").assertIsNotEnabled()
    }
}
