package org.example.taximobile.feature.app

import androidx.compose.ui.test.*
import androidx.compose.ui.test.v2.runComposeUiTest
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
import org.example.taximobile.App
import org.example.taximobile.data.scheduling.bookingFixture
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import java.util.Locale
import java.nio.file.Files
import java.nio.file.Path
import org.jetbrains.skia.Image
import org.jetbrains.skia.EncodedImageFormat
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@OptIn(ExperimentalTestApi::class)
class ScheduledQuoteBindingUiTest {
    @Test fun an_old_estimate_cannot_be_presented_as_review_for_a_different_requested_time() = runComposeUiTest {
        val b = bookingFixture()
        val estimate = ScheduledBookingEstimate(b.cityId, b.operatorId, "ON_DEMAND", null, b.scheduledFor,
            b.cityTimezone, b.pickup, b.destination, b.economics, b.cancellationTerms, "CASH")
        val reads = mutableListOf<String>()
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = b.pickup to b.destination,
            scheduledBookingEstimate = estimate).withScheduledTestCity())
        setContent { App(state = ui.value, placeSearchEnabled = false, onResolveScheduledLocalTime = clockResponder(ui),
            onEstimateScheduledPointToPoint = { time, _, _, _, _ -> reads += time }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        chooseScheduledClock("2026-11-02", "09:30")
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        assertEquals(listOf("2026-11-02T08:30:00Z"), reads)
        onNodeWithText("Confirm scheduled ride").assertDoesNotExist()
    }

    @Test fun a_matching_retry_replaces_the_stale_review_and_confirms_only_the_current_time() = runComposeUiTest {
        val b = bookingFixture()
        val estimate = ScheduledBookingEstimate(b.cityId, b.operatorId, "ON_DEMAND", null, b.scheduledFor,
            b.cityTimezone, b.pickup, b.destination, b.economics, b.cancellationTerms, "CASH")
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = b.pickup to b.destination,
            scheduledBookingEstimate = estimate).withScheduledTestCity())
        var correctResponse = false
        val commands = mutableListOf<String>()
        setContent { App(state = ui.value, placeSearchEnabled = false, onResolveScheduledLocalTime = clockResponder(ui),
            onEstimateScheduledPointToPoint = { time, _, _, _, readId ->
                if (correctResponse) ui.value = ui.value.copy(scheduledBookingEstimateReadId = readId, scheduledBookingEstimate = estimate.copy(scheduledFor = time))
            }, onSchedulePointToPoint = { time, _, _, _, _, _ -> commands += time }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        chooseScheduledClock("2026-11-02", "09:30")
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Trip review unavailable. Review the time, route and price again.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Confirm scheduled ride").assertDoesNotExist()
        correctResponse = true
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Confirm scheduled ride").performScrollTo().assertIsEnabled().performClick()
        assertEquals(listOf("2026-11-02T08:30:00Z"), commands)
    }

    @Test fun server_offset_normalization_does_not_replace_the_selected_instant() = runComposeUiTest {
        val b = bookingFixture()
        val estimate = ScheduledBookingEstimate(b.cityId, b.operatorId, "ON_DEMAND", null, b.scheduledFor,
            b.cityTimezone, b.pickup, b.destination, b.economics, b.cancellationTerms, "CASH")
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = b.pickup to b.destination).withScheduledTestCity())
        val commands = mutableListOf<String>()
        setContent { App(state = ui.value, placeSearchEnabled = false, onResolveScheduledLocalTime = clockResponder(ui),
            onEstimateScheduledPointToPoint = { _, _, _, _, readId -> ui.value = ui.value.copy(scheduledBookingEstimateReadId = readId, scheduledBookingEstimate = estimate.copy(scheduledFor = "2026-11-01T09:30:00+01:00")) },
            onSchedulePointToPoint = { time, _, _, _, _, _ -> commands += time }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        chooseScheduledClock("2026-11-01", "09:30")
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Confirm scheduled ride").performScrollTo().assertIsEnabled().performClick()
        assertEquals(listOf("2026-11-01T08:30:00Z"), commands)
    }

    @Test fun changed_trip_warning_wraps_in_every_language_and_style_at_two_hundred_percent_text() {
        val original = Locale.getDefault()
        try {
            val labels = listOf(
                listOf("en", "Schedule", "Review price and terms",
                    "Trip review unavailable. Review the time, route and price again."),
                listOf("fr", "Planifier", "Vérifier le prix et les conditions",
                    "Vérification indisponible. Revoyez l’heure, le trajet et le prix."),
                listOf("ar", "جدولة", "مراجعة السعر والشروط",
                    "المراجعة غير متاحة. راجع الوقت والمسار والسعر."),
            )
            for ((language, schedule, review, warning) in labels) {
                Locale.setDefault(Locale.forLanguageTag(language))
                for (style in TaxiStyle.entries) {
                    val preferences = TaxiStylePreferences(object : TaxiStyleStore {
                        override fun read() = style.storageValue
                        override fun write(value: String) = Unit
                    })
                    val b = bookingFixture()
                    val estimate = ScheduledBookingEstimate(b.cityId, b.operatorId, "ON_DEMAND", null, b.scheduledFor,
                        b.cityTimezone, b.pickup, b.destination, b.economics, b.cancellationTerms, "CASH")
                    var commands = 0
                    val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = b.pickup to b.destination,
                        scheduledBookingEstimate = estimate).withScheduledTestCity())
                    runComposeUiTest {
                        setContent { CompositionLocalProvider(LocalDensity provides Density(1f, 2f)) {
                            Box(Modifier.size(360.dp, 800.dp).testTag("scheduled-review-viewport")) {
                                App(state = ui.value, placeSearchEnabled = false, stylePreferences = preferences,
                                    onResolveScheduledLocalTime = clockResponder(ui),
                                    onSchedulePointToPoint = { _, _, _, _, _, _ -> commands++ })
                            }
                        } }
                        onNodeWithText(schedule).performScrollTo().performClick()
                        chooseScheduledClock("2026-11-02", "09:30", language)
                        onNodeWithText(review).performScrollTo().performClick()
                        val message = onNodeWithText(warning)
                        message.performScrollTo().assertIsDisplayed()
                        val bounds = message.getUnclippedBoundsInRoot()
                        val viewport = onNodeWithTag("scheduled-review-viewport").getUnclippedBoundsInRoot()
                        assertTrue(bounds.left >= viewport.left && bounds.right <= viewport.right)
                        assertTrue(bounds.top >= viewport.top && bounds.bottom <= viewport.bottom)
                        assertEquals(0, commands)
                        System.getenv("TAXIMOBILE_SCHEDULED_REVIEW_EVIDENCE_DIR")?.let { directory ->
                            val path = Path.of(directory); Files.createDirectories(path)
                            val data = Image.makeFromBitmap(onRoot().captureToImage().asSkiaBitmap()).encodeToData(EncodedImageFormat.PNG)
                            assertTrue(data != null)
                            Files.write(path.resolve("${style.storageValue}-$language-large.png"), data.bytes)
                        }
                    }
                }
            }
        } finally { Locale.setDefault(original) }
    }
}
