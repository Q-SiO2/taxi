package org.example.taximobile.feature.app

import androidx.compose.ui.test.*
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.App
import org.example.taximobile.app.AppRole
import org.example.taximobile.data.scheduling.bookingFixture
import org.example.taximobile.data.scheduling.scheduledOfferFixture
import org.example.taximobile.data.scheduling.commitmentFixture
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.scheduling.ScheduledBookingPage
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.dp
import androidx.compose.ui.graphics.asSkiaBitmap
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import java.util.Locale
import java.nio.file.Files
import java.nio.file.Path
import org.jetbrains.skia.Image
import org.jetbrains.skia.EncodedImageFormat

@OptIn(ExperimentalTestApi::class)
class ScheduledCityTimeUiTest {
    @Test fun passenger_booking_uses_the_city_time_and_offset_instead_of_raw_utc() = runComposeUiTest {
        setContent { App(state = AppUiState.PassengerReady(scheduledBookingPage = ScheduledBookingPage(listOf(bookingFixture()),1,20,1)),placeSearchEnabled = false) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("2026-11-01 · 09:30 (UTC+01:00)",substring = true).performScrollTo().assertIsDisplayed()
        onAllNodesWithText("2026-11-01T08:30:00Z").assertCountEquals(0)
    }

    @Test fun driver_offer_uses_the_city_time_and_offset() = runComposeUiTest {
        val offer = scheduledOfferFixture()
        setContent { App(appRole = AppRole.DRIVER,state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE,scheduledOffers = listOf(offer))) }
        onNodeWithText("Scheduled work",substring = true).performScrollTo().performClick()
        onNodeWithText("2026-11-01 · 09:30 (UTC+01:00)",substring = true).performScrollTo().assertIsDisplayed()
    }

    @Test fun driver_commitment_and_both_protected_endpoints_use_the_city_timezone() = runComposeUiTest {
        val commitment = commitmentFixture(scheduledOfferFixture())
        setContent { App(appRole = AppRole.DRIVER,state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE,scheduledCommitments = listOf(commitment))) }
        onNodeWithText("Scheduled work",substring = true).performScrollTo().performClick()
        onNodeWithText("Protected",substring = true).performScrollTo().assertTextContains("09:30 (UTC+01:00)",substring = true)
        onNodeWithText("Protected",substring = true).assertTextContains("10:00 (UTC+01:00)",substring = true)
    }

    @Test fun quote_review_shows_the_server_city_time_and_keeps_the_original_request_instant() = runComposeUiTest {
        val b = bookingFixture()
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = b.pickup to b.destination))
        val requests = mutableListOf<String>()
        setContent { App(state = ui.value,placeSearchEnabled = false,
            onEstimateScheduledPointToPoint = { time,_,_,_ -> ui.value = ui.value.copy(scheduledBookingEstimate = ScheduledBookingEstimate(
                b.cityId,b.operatorId,b.serviceType,null,time,b.cityTimezone,b.pickup,b.destination,b.economics,b.cancellationTerms,"CASH")) },
            onSchedulePointToPoint = { time,_,_,_,_,_ -> requests += time }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Pickup time with timezone").performScrollTo().performTextInput(b.scheduledFor)
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("2026-11-01 · 09:30 (UTC+01:00)",substring = true).performScrollTo().assertIsDisplayed()
        onNodeWithText("Confirm scheduled ride").performScrollTo().performClick()
        assertEquals(listOf(b.scheduledFor),requests)
    }

    @Test fun unsupported_quote_time_is_visible_and_cannot_be_confirmed() = runComposeUiTest {
        val b = bookingFixture()
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = b.pickup to b.destination))
        var commands = 0
        setContent { App(state = ui.value,placeSearchEnabled = false,
            onEstimateScheduledPointToPoint = { time,_,_,_ -> ui.value = ui.value.copy(scheduledBookingEstimate = ScheduledBookingEstimate(
                b.cityId,b.operatorId,b.serviceType,null,time,"PRIVATE-invalid",b.pickup,b.destination,b.economics,b.cancellationTerms,"CASH")) },
            onSchedulePointToPoint = { _,_,_,_,_,_ -> commands++ }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Pickup time with timezone").performScrollTo().performTextInput(b.scheduledFor)
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Time unavailable. Refresh the booking details.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Confirm scheduled ride").performScrollTo().assertIsNotEnabled()
        onAllNodesWithText("PRIVATE-invalid",substring = true).assertCountEquals(0)
        assertEquals(0,commands)
    }

    @Test fun unavailable_existing_time_has_explicit_read_retry_and_preserves_known_policy_cancellation() = runComposeUiTest {
        val b = bookingFixture().copy(cityTimezone = "PRIVATE-invalid")
        val reads = mutableListOf<Int>()
        val cancelled = mutableListOf<String>()
        setContent { App(state = AppUiState.PassengerReady(scheduledBookingPage = ScheduledBookingPage(listOf(b),1,20,1)),placeSearchEnabled = false,
            onLoadPassengerScheduledBookings = { reads += it },onCancelScheduledBooking = { cancelled += it }) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Time unavailable. Refresh the booking details.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Reload bookings").performScrollTo().performClick()
        assertEquals(listOf(1),reads)
        assertTrue(cancelled.isEmpty())
        onNodeWithText("Cancel scheduled ride").performScrollTo().performClick()
        onNodeWithText("Cancel booking").assertIsEnabled().performClick()
        assertEquals(listOf(b.id),cancelled)
    }

    @Test fun driver_unknown_city_time_cannot_enable_acceptance() = runComposeUiTest {
        val offer = scheduledOfferFixture().copy(cityTimezone = "PRIVATE-invalid")
        var commands = 0
        setContent { App(appRole = AppRole.DRIVER,state = AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE,scheduledOffers = listOf(offer)),
            onRespondToScheduledOffer = { _,_ -> commands++ }) }
        onNodeWithText("Scheduled work",substring = true).performScrollTo().performClick()
        onNodeWithText("Time unavailable. Refresh the booking details.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Accept commitment").performScrollTo().assertIsNotEnabled()
        assertEquals(0,commands)
    }

    @Test fun city_time_wraps_inside_the_viewport_in_all_languages_and_styles_at_two_hundred_percent_text() {
        val original = Locale.getDefault()
        try {
            for ((language,choose,schedule) in listOf(listOf("en","Choose on the map","Schedule"),listOf("fr","Choisir sur la carte","Planifier"),listOf("ar","اختر على الخريطة","جدولة"))) {
                Locale.setDefault(Locale.forLanguageTag(language))
                for (style in TaxiStyle.entries) {
                    val preferences = TaxiStylePreferences(object : TaxiStyleStore {
                        override fun read() = style.storageValue
                        override fun write(value: String) = Unit
                    })
                    runComposeUiTest {
                        setContent { CompositionLocalProvider(LocalDensity provides Density(1f,2f)) {
                            Box(Modifier.size(360.dp,800.dp).testTag("city-time-viewport")) {
                                App(state = AppUiState.PassengerReady(scheduledBookingPage = ScheduledBookingPage(listOf(bookingFixture()),1,20,1)),
                                    placeSearchEnabled = false,stylePreferences = preferences)
                            }
                        } }
                        onNodeWithText(choose).performScrollTo().performClick()
                        onNodeWithText(schedule).performScrollTo().performClick()
                        val time = onNodeWithText("2026-11-01 · 09:30 (UTC+01:00)",substring = true)
                        time.performScrollTo().assertIsDisplayed()
                        val bounds = time.getUnclippedBoundsInRoot()
                        val viewport = onNodeWithTag("city-time-viewport").getUnclippedBoundsInRoot()
                        assertTrue(bounds.left >= viewport.left && bounds.right <= viewport.right)
                        System.getenv("TAXIMOBILE_CITY_TIME_EVIDENCE_DIR")?.let { directory ->
                            val path = Path.of(directory); Files.createDirectories(path)
                            val data = Image.makeFromBitmap(onRoot().captureToImage().asSkiaBitmap()).encodeToData(EncodedImageFormat.PNG)
                            assertTrue(data != null)
                            Files.write(path.resolve("${style.storageValue}-$language-large.png"),data.bytes)
                        }
                    }
                }
            }
        } finally { Locale.setDefault(original) }
    }
}
