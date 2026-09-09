package org.example.taximobile.feature.ui.components

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.v2.runComposeUiTest
import kotlin.test.Test

@OptIn(ExperimentalTestApi::class)
class TaxiArtworkUiTest {
    @Test
    fun landing_asset_and_canvas_fallback_keep_the_same_accessibility_description() = runComposeUiTest {
        var useBundledAsset by mutableStateOf(true)
        setContent {
            TaxiBrandArtwork(
                contentDescriptionText = "Branded taxi route",
                useBundledAsset = useBundledAsset,
            )
        }

        onNodeWithContentDescription("Branded taxi route").assertIsDisplayed()
        runOnIdle { useBundledAsset = false }
        onNodeWithContentDescription("Branded taxi route").assertIsDisplayed()
    }

    @Test
    fun vehicle_artwork_can_fall_back_to_a_labeled_geometric_placeholder() = runComposeUiTest {
        var useBundledAsset by mutableStateOf(true)
        setContent {
            VehicleAssetFallback(
                vehicleLabel = "Dacia Logan",
                useBundledAsset = useBundledAsset,
            )
        }

        onNodeWithContentDescription("Dacia Logan").assertIsDisplayed()
        runOnIdle { useBundledAsset = false }
        onNodeWithText("DA").assertIsDisplayed()
    }
}
