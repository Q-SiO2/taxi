package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertHeightIsAtLeast
import androidx.compose.ui.test.assertIsFocused
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.getUnclippedBoundsInRoot
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.ui.components.TaxiButton
import org.example.taximobile.feature.ui.components.TaxiSheet
import org.example.taximobile.feature.ui.components.TaxiSheetSnap
import org.example.taximobile.App
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@OptIn(ExperimentalTestApi::class)
class MapSheetInsetsUiTest {
    @Test fun passenger_expansion_yields_map_shortcuts_to_the_toolbar() = checkMapShortcuts(false, 1f)
    @Test fun driver_expansion_yields_map_shortcuts_to_the_toolbar() = checkMapShortcuts(true, 1f)
    @Test fun passenger_large_text_uses_the_actual_promoted_sheet_for_map_chrome() = checkMapShortcuts(false, 1.6f)
    @Test fun driver_large_text_uses_the_actual_promoted_sheet_for_map_chrome() = checkMapShortcuts(true, 1.6f)

    private fun checkMapShortcuts(driver: Boolean, fontScale: Float) = runComposeUiTest {
        setContent {
            CompositionLocalProvider(LocalDensity provides Density(1f, fontScale)) {
                Box(Modifier.size(360.dp, 760.dp)) {
                    App(state = if (driver) AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE)
                        else AppUiState.PassengerReady())
                }
            }
        }
        mainClock.advanceTimeBy(1000)
        if (fontScale < 1.6f) {
            onNodeWithContentDescription("Recenter map").assertExists()
            repeat(2) {
                val expand = onNodeWithTag("taxi-sheet").fetchSemanticsNode()
                    .config[SemanticsActions.CustomActions].firstOrNull { it.label == "Expand panel" }
                if (expand != null) {
                    runOnIdle { assertTrue(expand.action()) }
                    mainClock.advanceTimeBy(1000)
                }
            }
        }
        onNodeWithContentDescription("Inbox").assertIsDisplayed()
        onNodeWithContentDescription("Recenter map").assertDoesNotExist()
        if (fontScale < 1.6f) {
            val collapse = onNodeWithTag("taxi-sheet").fetchSemanticsNode()
                .config[SemanticsActions.CustomActions].single { it.label == "Collapse panel" }
            runOnIdle { assertTrue(collapse.action()) }
            mainClock.advanceTimeBy(1000)
            onNodeWithContentDescription("Recenter map").assertExists()
        }
    }

    @Test
    fun peek_sheet_keeps_focused_field_visible_when_keyboard_is_larger_than_sheet() = runComposeUiTest {
        var keyboardBottom by mutableStateOf(0.dp)
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                TaxiSheet(
                    snap = TaxiSheetSnap.Peek,
                    onSnapChange = {},
                    safeInsets = WindowInsets(bottom = maxOf(24.dp, keyboardBottom)),
                    keyboardInsets = WindowInsets(bottom = keyboardBottom),
                ) {
                    Spacer(Modifier.height(400.dp))
                    BasicTextField(
                        value = "Synthetic coordinate", onValueChange = {},
                        modifier = Modifier.testTag("coordinate-input"),
                    )
                }
            }
        }
        onNodeWithTag("coordinate-input").performScrollTo().performClick().assertIsFocused()
        runOnIdle { keyboardBottom = 300.dp }
        mainClock.advanceTimeBy(1000)
        onNodeWithTag("coordinate-input").performScrollTo().assertIsFocused()
        val viewport = onNodeWithTag("taxi-sheet-scroll-content").getUnclippedBoundsInRoot()
        assertEquals(460.dp, viewport.bottom)
        assertTrue(viewport.bottom - viewport.top >= 100.dp, "IME must not erase the peek viewport")
        val input = onNodeWithTag("coordinate-input").getUnclippedBoundsInRoot()
        assertTrue(input.top >= viewport.top && input.bottom <= viewport.bottom)
        runOnIdle { keyboardBottom = 0.dp }
        mainClock.advanceTimeBy(1000)
        assertEquals(736.dp, onNodeWithTag("taxi-sheet-scroll-content").getUnclippedBoundsInRoot().bottom)
    }

    @Test
    fun long_sheet_action_scrolls_above_gesture_navigation_without_insetting_the_map() = runComposeUiTest {
        var clicks = 0
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                TaxiSheet(
                    snap = TaxiSheetSnap.Expanded,
                    onSnapChange = {},
                    safeInsets = WindowInsets(left = 7.dp, top = 48.dp, right = 9.dp, bottom = 24.dp),
                ) {
                    Spacer(Modifier.height(900.dp))
                    TaxiButton("Synthetic sheet action", { clicks++ })
                }
            }
        }
        mainClock.advanceTimeBy(1000)
        val scrollBounds = onNodeWithTag("taxi-sheet-scroll-content").getUnclippedBoundsInRoot()
        assertEquals(736.dp, scrollBounds.bottom)
        assertEquals(7.dp, scrollBounds.left)
        assertEquals(351.dp, scrollBounds.right)
        onNodeWithText("Synthetic sheet action").performScrollTo().assertHeightIsAtLeast(48.dp)
        assertTrue(onNodeWithText("Synthetic sheet action").getUnclippedBoundsInRoot().bottom <= 736.dp)
        onNodeWithText("Synthetic sheet action").performClick()
        assertEquals(1, clicks)
    }
}
