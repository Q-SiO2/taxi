package org.example.taximobile.feature.ui.components

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.width
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.test.assertWidthIsEqualTo
import androidx.compose.ui.test.assertHeightIsEqualTo
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.v2.runComposeUiTest
import kotlin.test.Test

@OptIn(ExperimentalTestApi::class)
class TaxiArtworkUiTest {
    @Test
    fun phone_portrait_shrinks_proportionally_on_narrow_screens() = runComposeUiTest {
        setContent {
            Box(Modifier.width(180.dp)) {
                TaxiBrandArtwork("Portrait artwork", useBundledAsset = false)
            }
        }
        onNodeWithContentDescription("Portrait artwork")
            .assertWidthIsEqualTo(180.dp).assertHeightIsEqualTo(320.dp)
    }

    @Test
    fun phone_portrait_is_capped_on_wide_screens() = runComposeUiTest {
        setContent {
            Box(Modifier.width(400.dp)) {
                TaxiBrandArtwork("Portrait artwork", useBundledAsset = false)
            }
        }
        onNodeWithContentDescription("Portrait artwork")
            .assertWidthIsEqualTo(216.dp).assertHeightIsEqualTo(384.dp)
    }

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
