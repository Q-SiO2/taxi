package org.example.taximobile.feature.ui.components

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import kotlin.test.Test

@OptIn(ExperimentalTestApi::class)
class TaxiSheetUiTest {
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
