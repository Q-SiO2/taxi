package org.example.taximobile.feature.app

import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.test.*
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.App
import org.example.taximobile.data.scheduling.bookingFixture
import org.example.taximobile.domain.scheduling.ScheduledBookingPage
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import java.util.Locale
import kotlin.test.Test
import kotlin.test.assertEquals

@OptIn(ExperimentalTestApi::class)
class ScheduledBookingPaginationUiTest {
    @Test fun page_navigation_is_reachable_in_every_style_and_all_three_languages() {
        val original = Locale.getDefault()
        try {
            for ((language, choose, schedule, next) in listOf(
                listOf("en", "Choose on the map", "Schedule", "Next bookings"),
                listOf("fr", "Choisir sur la carte", "Planifier", "Réservations suivantes"),
                listOf("ar", "اختر على الخريطة", "جدولة", "الحجوزات التالية"),
            )) {
                for (style in TaxiStyle.entries) {
                    Locale.setDefault(Locale.forLanguageTag(language))
                    val preferences = TaxiStylePreferences(object : TaxiStyleStore {
                        override fun read() = style.storageValue
                        override fun write(value: String) = Unit
                    })
                    runComposeUiTest {
                        var requested: Int? = null
                        setContent { App(state = state(), stylePreferences = preferences, placeSearchEnabled = false,
                            onLoadPassengerScheduledBookings = { requested = it }) }
                        onNodeWithText(choose).performScrollTo().performClick()
                        onNodeWithText(schedule).performScrollTo().performClick()
                        onNodeWithText(next).performScrollTo().performClick()
                        assertEquals(2, requested)
                    }
                }
            }
        } finally { Locale.setDefault(original) }
    }

    private fun state(page: Int = 1, unavailable: Boolean = false) = AppUiState.PassengerReady(
        scheduledBookingPage = if (unavailable) null else ScheduledBookingPage(
            listOf(bookingFixture(if (page == 1) "booking-1" else "booking-21")), page, 20, 21,
        ), scheduledBookingsLoadFailed = unavailable, scheduledBookingRequestedPage = page,
    )

    @Test fun second_page_is_reachable_and_cancels_only_the_selected_backend_record_after_confirmation() = runComposeUiTest {
        val ui = mutableStateOf(state())
        val pages = mutableListOf<Int>()
        val cancellations = mutableListOf<String>()
        setContent { App(state = ui.value, placeSearchEnabled = false, onLoadPassengerScheduledBookings = { pages += it; ui.value = state(it) },
            onCancelScheduledBooking = { cancellations += it }) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Next bookings").performScrollTo().performClick()
        assertEquals(listOf(2), pages)
        assertEquals(emptyList(), cancellations)
        onNodeWithText("Page 2 · 21 bookings").performScrollTo().assertIsDisplayed()
        onNodeWithText("Cancel scheduled ride").performScrollTo().performClick()
        assertEquals(emptyList(), cancellations)
        onNodeWithText("Cancel booking").performClick()
        assertEquals(listOf("booking-21"), cancellations)
    }

    @Test fun failed_page_is_retryable_without_claiming_an_empty_collection_or_cancelling_a_booking() = runComposeUiTest {
        var requested: Int? = null
        var mutations = 0
        setContent { App(state = state(2, unavailable = true), placeSearchEnabled = false, onLoadPassengerScheduledBookings = { requested = it },
            onCancelScheduledBooking = { mutations++ }) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Reload bookings").performScrollTo().performClick()
        assertEquals(2, requested)
        assertEquals(0, mutations)
        onAllNodesWithText("No scheduled rides").assertCountEquals(0)
        onAllNodesWithText("Cancel scheduled ride").assertCountEquals(0)
    }

    @Test fun page_replacement_removes_an_open_stale_confirmation_without_a_command() = runComposeUiTest {
        val ui = mutableStateOf(state())
        var mutations = 0
        setContent { App(state = ui.value, placeSearchEnabled = false, onCancelScheduledBooking = { mutations++ }) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Cancel scheduled ride").performScrollTo().performClick()
        onNodeWithText("Cancel booking").assertIsDisplayed()
        runOnIdle { ui.value = state(2) }
        waitForIdle()
        onAllNodesWithText("Cancel booking").assertCountEquals(0)
        assertEquals(0, mutations)
    }

    @Test fun pending_page_read_disables_further_navigation() = runComposeUiTest {
        val pending = mutableStateOf<AppAction?>(null)
        var calls = 0
        setContent { App(state = state(), pendingAction = pending.value, placeSearchEnabled = false,
            onLoadPassengerScheduledBookings = { calls++ }) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        runOnIdle { pending.value = AppAction(AppActionKind.LOAD_PASSENGER_SCHEDULED_BOOKINGS, "2") }
        onNodeWithContentDescription("Next bookings").performScrollTo().assertIsNotEnabled()
        assertEquals(0, calls)
    }
}
