package org.example.taximobile.feature.app

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.*
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.App
import org.example.taximobile.app.AppRole
import org.example.taximobile.domain.drivers.*
import kotlin.test.Test
import kotlin.test.assertEquals

@OptIn(ExperimentalTestApi::class)
class PendingCashRecoveryUiTest {
    private fun payment(id: String, amount: String) = PendingCashPayment("payment-$id", id, amount, "MAD", "2026-10-05T12:00:00Z")
    private fun state(items: List<PendingCashPayment>, page: Int = 1, total: Int = items.size) = AppUiState.DriverReady(
        availability = DriverAvailabilityStatus.OFFLINE,
        pendingCashPayments = PendingCashPaymentsPage(items, page, 20, total),
    )

    @Test fun recovered_cash_card_shows_context_and_confirms_only_selected_ride() = runComposeUiTest {
        var settled: String? = null
        setContent { App(AppRole.DRIVER, state = state(listOf(payment("old-ride", "35.00"), payment("second-ride", "42.00"))), onSettleDriverCash = { settled = it }) }
        onNodeWithText("Cash awaiting confirmation").assertIsDisplayed()
        onNodeWithText("2 cash payments to confirm").assertIsDisplayed()
        onNodeWithText("35.00", substring = true).performScrollTo().assertIsDisplayed()
        onAllNodesWithText("Confirm cash received")[0].performScrollTo().performClick()
        assertEquals(null, settled)
        onNodeWithText("Confirm cash received?").assertIsDisplayed()
        onNode(hasText("35.00 MAD", substring = true) and hasAnyAncestor(isDialog())).assertIsDisplayed()
        onAllNodes(hasText("old-ride", substring = true) and hasAnyAncestor(isDialog())).assertCountEquals(0)
        onNodeWithText("Cash received").performClick()
        assertEquals("old-ride", settled)
    }

    @Test fun empty_backend_queue_has_no_cash_control_even_with_completed_history() = runComposeUiTest {
        setContent { App(AppRole.DRIVER, state = state(emptyList()).copy(rideHistory = listOf(DriverRideSummary("history", org.example.taximobile.domain.rides.RideStatus.COMPLETED)))) }
        onAllNodesWithText("Confirm cash received").assertCountEquals(0)
    }

    @Test fun unavailable_queue_is_actionable_and_cannot_confirm_cash() = runComposeUiTest {
        var requested: Int? = null
        setContent { App(AppRole.DRIVER, state = state(emptyList()).copy(pendingCashPayments = null, pendingCashLoadFailed = true), onLoadPendingCashPayments = { requested = it }) }
        onNodeWithText("Reload pending cash").performScrollTo().performClick()
        assertEquals(1, requested)
        onAllNodesWithText("Confirm cash received").assertCountEquals(0)
    }

    @Test fun queue_pagination_reaches_work_beyond_history_without_settling_it() = runComposeUiTest {
        var requested: Int? = null
        setContent { App(AppRole.DRIVER, state = state(listOf(payment("oldest", "35.00")), total = 23), onLoadPendingCashPayments = { requested = it }) }
        onNodeWithText("23 cash payments to confirm").performScrollTo().assertIsDisplayed()
        onNodeWithText("Next cash payments").performScrollTo().performClick()
        assertEquals(2, requested)
    }

    @Test fun a_settled_or_failed_read_removes_open_confirmation_without_a_command() = runComposeUiTest {
        val ui = mutableStateOf(state(listOf(payment("old-ride", "35.00"))))
        var calls = 0
        setContent { App(AppRole.DRIVER, state = ui.value, onSettleDriverCash = { calls++ }) }
        onNodeWithText("Confirm cash received").performScrollTo().performClick()
        runOnIdle { ui.value = state(emptyList()) }
        waitForIdle()
        onAllNodesWithText("Cash received").assertCountEquals(0)
        assertEquals(0, calls)
    }
}
