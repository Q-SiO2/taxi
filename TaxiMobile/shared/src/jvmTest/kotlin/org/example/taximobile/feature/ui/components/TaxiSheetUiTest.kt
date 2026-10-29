package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.material3.Text
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.SemanticsActions
import androidx.compose.ui.semantics.SemanticsProperties
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performTouchInput
import androidx.compose.ui.test.swipe
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@OptIn(ExperimentalTestApi::class)
class TaxiSheetUiTest {
    @Test
    fun header_drag_expands_and_collapses_a_long_scrollable_sheet() = runComposeUiTest {
        var snap by mutableStateOf(TaxiSheetSnap.Half)
        setContent {
            Box(Modifier.width(400.dp).height(600.dp)) {
                TaxiSheet(snap, { snap = it }, safeInsets = WindowInsets(0, 0, 0, 0),
                    keyboardInsets = WindowInsets(0, 0, 0, 0)) {
                    repeat(30) { Text("Row $it", Modifier.height(40.dp)) }
                }
            }
        }
        onNodeWithTag("taxi-sheet-scroll-content").performTouchInput {
            swipe(Offset(centerX, 14f), Offset(centerX, -116f), durationMillis = 400)
        }
        runOnIdle { assertEquals(TaxiSheetSnap.Expanded, snap) }
        onNodeWithTag("taxi-sheet").assertHeightIsEqualTo(468.dp)
        onNodeWithTag("taxi-sheet-scroll-content").performTouchInput {
            swipe(Offset(centerX, 14f), Offset(centerX, 144f), durationMillis = 400)
        }
        runOnIdle { assertEquals(TaxiSheetSnap.Half, snap) }
        onNodeWithTag("taxi-sheet").assertHeightIsEqualTo(288.dp)
    }

    @Test
    fun body_drag_scrolls_without_resizing_the_sheet() = runComposeUiTest {
        var snap by mutableStateOf(TaxiSheetSnap.Half)
        setContent {
            Box(Modifier.width(400.dp).height(600.dp)) {
                TaxiSheet(snap, { snap = it }, safeInsets = WindowInsets(0, 0, 0, 0),
                    keyboardInsets = WindowInsets(0, 0, 0, 0)) {
                    repeat(30) { Text("Row $it", Modifier.height(40.dp)) }
                }
            }
        }
        onNodeWithTag("taxi-sheet-scroll-content").performTouchInput {
            swipe(Offset(centerX, 180f), Offset(centerX, 80f), durationMillis = 400)
        }
        val range = onNodeWithTag("taxi-sheet-scroll-content").fetchSemanticsNode()
            .config[SemanticsProperties.VerticalScrollAxisRange]
        runOnIdle {
            assertEquals(TaxiSheetSnap.Half, snap)
            assertTrue(range.value() > 0f, "Body drag must keep the content scrollable")
        }
    }

    @Test
    fun header_region_tap_does_not_steal_a_child_action() = runComposeUiTest {
        var snap by mutableStateOf(TaxiSheetSnap.Half)
        var clicks = 0
        setContent {
            Box(Modifier.width(400.dp).height(600.dp)) {
                TaxiSheet(snap, { snap = it }, safeInsets = WindowInsets(0, 0, 0, 0),
                    keyboardInsets = WindowInsets(0, 0, 0, 0)) {
                    TaxiButton("Synthetic first action", { clicks++ })
                    repeat(30) { Text("Row $it", Modifier.height(40.dp)) }
                }
            }
        }
        onNodeWithTag("taxi-sheet-scroll-content").performTouchInput {
            down(Offset(centerX, 40f))
            up()
        }
        runOnIdle {
            assertEquals(1, clicks, "A tap must reach the child once without resizing")
            assertEquals(TaxiSheetSnap.Half, snap)
        }
    }

    @Test
    fun accessibility_actions_resize_in_both_directions() = runComposeUiTest {
        var snap by mutableStateOf(TaxiSheetSnap.Peek)
        setContent {
            Box(Modifier.width(400.dp).height(600.dp)) {
                TaxiSheet(snap, { snap = it }) { Text("Synthetic panel") }
            }
        }
        fun action(label: String) {
            val actions = onNodeWithTag("taxi-sheet").fetchSemanticsNode()
                .config[SemanticsActions.CustomActions]
            runOnIdle { assertTrue(actions.single { it.label == label }.action()) }
        }
        action("Expand panel")
        runOnIdle { assertEquals(TaxiSheetSnap.Half, snap) }
        action("Expand panel")
        runOnIdle { assertEquals(TaxiSheetSnap.Expanded, snap) }
        action("Collapse panel")
        runOnIdle { assertEquals(TaxiSheetSnap.Half, snap) }
        action("Collapse panel")
        runOnIdle { assertEquals(TaxiSheetSnap.Peek, snap) }
    }

    @Test
    fun large_text_does_not_offer_a_collapse_below_its_minimum() = runComposeUiTest {
        var changes = 0
        setContent {
            CompositionLocalProvider(LocalDensity provides Density(1f, 1.6f)) {
                Box(Modifier.width(400.dp).height(600.dp)) {
                    TaxiSheet(TaxiSheetSnap.Peek, { changes++ }) { Text("Synthetic panel") }
                }
            }
        }
        val actions = onNodeWithTag("taxi-sheet").fetchSemanticsNode()
            .config[SemanticsActions.CustomActions]
        runOnIdle {
            assertTrue(actions.isEmpty(), "A sheet already at its font minimum must not advertise resizing")
            assertEquals(0, changes)
        }
        onNodeWithTag("taxi-sheet").assertHeightIsEqualTo(468.dp)
    }

    @Test
    fun system_font_scale_promotes_a_peek_sheet_to_keep_controls_reachable() = runComposeUiTest {
        var fontScale by mutableStateOf(1.0f)
        setContent {
            CompositionLocalProvider(LocalDensity provides Density(density = 1.0f, fontScale = fontScale)) {
                Box(Modifier.width(400.dp).height(600.dp)) {
                    TaxiSheet(snap = TaxiSheetSnap.Peek, onSnapChange = {}) {}
                }
            }
        }

        onNodeWithTag("taxi-sheet").assertHeightIsEqualTo(168.dp)

        runOnIdle { fontScale = 1.6f }

        onNodeWithTag("taxi-sheet").assertHeightIsEqualTo(468.dp)
    }
}
