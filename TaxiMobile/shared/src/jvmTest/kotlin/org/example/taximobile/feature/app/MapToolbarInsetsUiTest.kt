package org.example.taximobile.feature.app

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertLeftPositionInRootIsEqualTo
import androidx.compose.ui.test.assertTopPositionInRootIsEqualTo
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.v2.runComposeUiTest
import androidx.compose.ui.unit.dp
import org.example.taximobile.feature.driver.DriverToolbar
import org.example.taximobile.feature.passenger.PassengerToolbar
import org.example.taximobile.feature.ui.theme.TaxiSpacing
import kotlin.test.Test
import kotlin.test.assertEquals

@OptIn(ExperimentalTestApi::class)
class MapToolbarInsetsUiTest {
    @Test
    fun passenger_account_action_clears_cutout_and_is_identified_by_purpose() = runComposeUiTest {
        var accountClicks = 0
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                PassengerToolbar(
                    displayName = "Synthetic passenger",
                    unreadCount = 0,
                    onAccount = { accountClicks++ },
                    onSafety = {},
                    onInbox = {},
                    safeInsets = WindowInsets(left = 7.dp, top = 48.dp, right = 9.dp, bottom = 24.dp),
                )
            }
        }
        onNodeWithContentDescription("Account")
            .assertTopPositionInRootIsEqualTo(48.dp + TaxiSpacing.Sm)
            .assertLeftPositionInRootIsEqualTo(7.dp + TaxiSpacing.Md)
            .performClick()
        assertEquals(1, accountClicks)
    }

    @Test
    fun driver_account_action_clears_cutout_and_is_identified_by_purpose() = runComposeUiTest {
        var accountClicks = 0
        setContent {
            Box(Modifier.size(360.dp, 760.dp)) {
                DriverToolbar(
                    displayName = "Synthetic driver",
                    unreadCount = 0,
                    onAccount = { accountClicks++ },
                    onSafety = {},
                    onInbox = {},
                    safeInsets = WindowInsets(left = 7.dp, top = 48.dp, right = 9.dp, bottom = 24.dp),
                )
            }
        }
        onNodeWithContentDescription("Driver account")
            .assertTopPositionInRootIsEqualTo(48.dp + TaxiSpacing.Sm)
            .assertLeftPositionInRootIsEqualTo(7.dp + TaxiSpacing.Md)
            .performClick()
        assertEquals(1, accountClicks)
    }

    @Test
    fun compact_passenger_actions_keep_safety_and_inbox_accessible_on_narrow_map() = runComposeUiTest {
        var safetyClicks = 0
        var inboxClicks = 0
        setContent {
            Box(Modifier.size(320.dp, 700.dp)) {
                PassengerToolbar(
                    displayName = "A long synthetic passenger account name",
                    unreadCount = 12,
                    onAccount = {},
                    onSafety = { safetyClicks++ },
                    onInbox = { inboxClicks++ },
                    safeInsets = WindowInsets(0.dp),
                )
            }
        }
        onNodeWithContentDescription("Safety").performClick()
        onNodeWithContentDescription("Inbox 12").performClick()
        assertEquals(1, safetyClicks)
        assertEquals(1, inboxClicks)
    }
}
