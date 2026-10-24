package org.example.taximobile.feature.ui.components

import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.v2.runComposeUiTest
import kotlin.test.Test

@OptIn(ExperimentalTestApi::class)
class FarePresentationUiTest {
    @Test
    fun fare_keeps_amount_visible_without_internal_tariff_version() = runComposeUiTest {
        setContent {
            FareBlock(
                amount = "35.00",
                currency = "MAD",
                pricingRuleVersion = "internal-v17",
                finalFare = false,
            )
        }
        onNodeWithText("35.00").assertIsDisplayed()
        onAllNodesWithText("internal-v17", substring = true).assertCountEquals(0)
    }
}
