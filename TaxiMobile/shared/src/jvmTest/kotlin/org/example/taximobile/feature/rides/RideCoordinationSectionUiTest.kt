package org.example.taximobile.feature.rides

import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.domain.rides.RideCoordinationCode
import org.example.taximobile.domain.rides.RideCoordinationMessage
import org.example.taximobile.domain.rides.RideCoordinationSenderRole
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import kotlin.test.Test
import kotlin.test.assertEquals

@OptIn(ExperimentalTestApi::class)
class RideCoordinationSectionUiTest {
    @Test
    fun passenger_sees_only_passenger_coordination_actions() = runComposeUiTest {
        var selected: RideCoordinationCode? = null
        setContent {
            RideCoordinationActions(
                rideId = "ride-1",
                senderRole = RideCoordinationSenderRole.PASSENGER,
                pendingAction = null,
                onSend = { _, code -> selected = code },
            )
        }

        onNodeWithText("I am at the pickup point").assertIsDisplayed().performClick()
        onNodeWithText("I need a little more time").assertIsDisplayed()
        onNodeWithText("I cannot find the taxi").assertIsDisplayed()
        assertEquals(RideCoordinationCode.PASSENGER_AT_PICKUP, selected)
    }

    @Test
    fun pending_coordination_disables_every_alternative_signal() = runComposeUiTest {
        setContent {
            RideCoordinationActions(
                rideId = "ride-1",
                senderRole = RideCoordinationSenderRole.DRIVER,
                pendingAction = AppAction(
                    AppActionKind.SEND_RIDE_COORDINATION,
                    "ride-1:DRIVER_ON_MY_WAY",
                ),
                onSend = { _, _ -> error("Disabled control must not submit") },
            )
        }

        onNodeWithText("I am at the pickup point").assertIsNotEnabled()
        onNodeWithText("I cannot find the passenger").assertIsNotEnabled()
    }

    @Test
    fun driver_sees_only_driver_coordination_actions() = runComposeUiTest {
        setContent {
            RideCoordinationActions(
                rideId = "ride-1",
                senderRole = RideCoordinationSenderRole.DRIVER,
                pendingAction = null,
                onSend = { _, _ -> },
            )
        }

        onNodeWithText("I am on my way").assertIsDisplayed()
        onNodeWithText("I cannot find the passenger").assertIsDisplayed()
        onAllNodesWithText("I need a little more time").assertCountEquals(0)
        onAllNodesWithText("I cannot find the taxi").assertCountEquals(0)
    }

    @Test
    fun unknown_latest_code_uses_generic_copy_without_exposing_raw_value() = runComposeUiTest {
        setContent {
            RideLatestCoordinationMessage(
                RideCoordinationMessage(
                    id = "message-1",
                    rideId = "ride-1",
                    senderRole = RideCoordinationSenderRole.UNKNOWN,
                    code = RideCoordinationCode.UNKNOWN,
                    createdAt = "2026-09-03T10:15:00Z",
                )
            )
        }

        onNodeWithText("Latest ride update").assertIsDisplayed()
        onNodeWithText("Ride update unavailable").assertIsDisplayed()
        onAllNodesWithText("FUTURE_CODE").assertCountEquals(0)
    }
}
