package org.example.taximobile.feature.app

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
import androidx.compose.ui.test.*
import androidx.compose.ui.test.v2.runComposeUiTest
import org.example.taximobile.App
import org.example.taximobile.data.scheduling.bookingFixture
import org.example.taximobile.domain.rides.LocalizedText
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.FixedRouteCatalog
import org.example.taximobile.domain.rides.PublishedFixedRouteDirection
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.feature.ui.theme.TaxiStyle
import org.example.taximobile.feature.ui.theme.TaxiStylePreferences
import org.example.taximobile.feature.ui.theme.TaxiStyleStore
import org.jetbrains.skia.Image
import org.jetbrains.skia.EncodedImageFormat
import java.nio.file.Files
import java.nio.file.Path
import java.util.Locale
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

@OptIn(ExperimentalTestApi::class)
class ScheduledPickupInputUiTest {
    @Test fun fixed_route_uses_its_catalog_city_for_clock_and_price() = runComposeUiTest {
        val fes = scheduledTestCity("fes", "Fès")
        val route = PublishedFixedRouteDirection("direction-fes", "version-fes", "FES_01",
            LocalizedText("Station route", "Ligne de la gare", "خط المحطة"), "OUTBOUND",
            LocalizedText("Station", "Gare", "المحطة"), LocalizedText("University", "Université", "الجامعة"),
            Coordinates(34.02, -5.00), Coordinates(34.00, -5.01),
            listOf(Coordinates(34.02, -5.00), Coordinates(34.00, -5.01)), "8.00", "MAD", true, true, emptyList())
        val booking = bookingFixture().copy(cityId = "fes", serviceType = "FIXED_ROUTE", fixedRouteDirectionVersionId = route.id)
        val ui = mutableStateOf(AppUiState.PassengerReady(
            serviceCities = listOf(scheduledTestCity("cas", "Casablanca"), fes),
            fixedRouteCatalog = FixedRouteCatalog(fes, listOf(route)), selectedFixedRouteDirectionId = route.id))
        val clockCities = mutableListOf<String>()
        val quoteDirections = mutableListOf<String>()
        val created = mutableListOf<String>()
        setContent { App(state = ui.value, placeSearchEnabled = false,
            onResolveScheduledLocalTime = { city, zone, date, time, id ->
                clockCities += city
                ui.value = ui.value.copy(scheduledLocalTimeOptions = scheduledClockFixture(city, zone, date, time), scheduledLocalTimeReadId = id)
            }, onEstimateScheduledFixedRoute = { time, direction, id ->
                quoteDirections += direction
                ui.value = ui.value.copy(scheduledBookingEstimateReadId = id, scheduledBookingEstimate = ScheduledBookingEstimate(
                    booking.cityId, booking.operatorId, booking.serviceType, route.id, time, booking.cityTimezone,
                    booking.pickup, booking.destination, booking.economics, booking.cancellationTerms, "CASH"))
            }, onScheduleFixedRoute = { time, direction, _, _ -> created += "$direction|$time" }) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Fixed route").performScrollTo().performClick()
        onNodeWithText("Fès").performScrollTo().assertIsDisplayed()
        chooseScheduledClock("2026-11-01", "09:30")
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Confirm scheduled ride").performScrollTo().performClick()
        assertEquals(listOf("fes"), clockCities)
        assertEquals(listOf(route.id), quoteDirections)
        assertEquals(listOf("${route.id}|2026-11-01T08:30:00Z"), created)
    }

    @Test fun selected_fes_city_after_another_catalog_city_controls_resolution_quote_and_creation() = runComposeUiTest {
        val booking = bookingFixture().copy(cityId = "fes")
        val firstCity = scheduledTestCity("cas", "Casablanca").copy(name = LocalizedText("Casablanca", "Casablanca", "الدار البيضاء"))
        val fes = scheduledTestCity("fes", "Fès")
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = booking.pickup to booking.destination,
            serviceCities = listOf(firstCity, fes)))
        val clockCities = mutableListOf<String>()
        val quoteCities = mutableListOf<String?>()
        val created = mutableListOf<Pair<String?, String>>()
        setContent { App(state = ui.value, placeSearchEnabled = false,
            onResolveScheduledLocalTime = { city, zone, date, time, id ->
                clockCities += city
                ui.value = ui.value.copy(scheduledLocalTimeOptions = scheduledClockFixture(city, zone, date, time), scheduledLocalTimeReadId = id)
            },
            onEstimateScheduledPointToPoint = { time, city, _, _, id ->
                quoteCities += city
                ui.value = ui.value.copy(scheduledBookingEstimateReadId = id, scheduledBookingEstimate = ScheduledBookingEstimate(
                    booking.cityId, booking.operatorId, booking.serviceType, null, time, booking.cityTimezone,
                    booking.pickup, booking.destination, booking.economics, booking.cancellationTerms, "CASH"))
            },
            onSchedulePointToPoint = { time, city, _, _, _, _ -> created += city to time }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithText("Choose city").performScrollTo().assertIsDisplayed().performClick()
        onNodeWithText("Fès").performClick()
        chooseScheduledClock("2026-11-01", "09:30")
        assertEquals(listOf("fes"), clockCities)
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        assertEquals(listOf<String?>("fes"), quoteCities)
        onNodeWithText("Confirm scheduled ride").performScrollTo().performClick()
        assertEquals(listOf<Pair<String?, String>>("fes" to "2026-11-01T08:30:00Z"), created)
    }

    @Test fun nonexistent_local_time_shows_gap_and_never_exposes_review() = runComposeUiTest {
        val paris = scheduledTestCity("paris", "Paris").copy(timezone = "Europe/Paris")
        val ui = mutableStateOf(AppUiState.PassengerReady(serviceCities = listOf(paris)))
        var quoteCalls = 0
        setContent { App(state = ui.value, placeSearchEnabled = false,
            onResolveScheduledLocalTime = clockResponder(ui),
            onEstimateScheduledPointToPoint = { _, _, _, _, _ -> quoteCalls++ }) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        chooseScheduledClock("2026-03-29", "02:30")
        onNodeWithText("This time is skipped here. Choose another time.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Review price and terms").assertDoesNotExist()
        onNodeWithText("Confirm scheduled ride").assertDoesNotExist()
        assertEquals(0, quoteCalls)
    }

    @Test fun repeated_local_hour_requires_explicit_offset_choice_and_a_new_review_after_switching() = runComposeUiTest {
        val paris = scheduledTestCity("paris", "Paris").copy(timezone = "Europe/Paris")
        val booking = bookingFixture().copy(cityId = "paris", cityTimezone = "Europe/Paris")
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = booking.pickup to booking.destination,
            serviceCities = listOf(paris)))
        val quoted = mutableListOf<String>()
        val created = mutableListOf<String>()
        setContent { App(state = ui.value, placeSearchEnabled = false,
            onResolveScheduledLocalTime = clockResponder(ui),
            onEstimateScheduledPointToPoint = { time, _, _, _, id ->
                quoted += time
                ui.value = ui.value.copy(scheduledBookingEstimateReadId = id, scheduledBookingEstimate = ScheduledBookingEstimate(
                    booking.cityId, booking.operatorId, booking.serviceType, null, time, booking.cityTimezone,
                    booking.pickup, booking.destination, booking.economics, booking.cancellationTerms, "CASH"))
            }, onSchedulePointToPoint = { time, _, _, _, _, _ -> created += time }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        chooseScheduledClock("2026-10-25", "02:30")
        onNodeWithText("Choose which pickup time.").performScrollTo().assertIsDisplayed()
        onNodeWithText("Review price and terms").assertDoesNotExist()
        onNodeWithText("02:30 (UTC+02:00)", substring = true).performScrollTo().performClick()
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Confirm scheduled ride").performScrollTo().assertIsEnabled()
        onNodeWithText("02:30 (UTC+01:00)", substring = true).performScrollTo().performClick()
        onNodeWithText("Confirm scheduled ride").assertDoesNotExist()
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Confirm scheduled ride").performScrollTo().performClick()
        assertEquals(listOf("2026-10-25T00:30:00Z", "2026-10-25T01:30:00Z"), quoted)
        assertEquals(listOf("2026-10-25T01:30:00Z"), created)
        assertTrue(quoted[0] != quoted[1])
    }

    @Test fun calendar_and_24_hour_picker_have_reachable_controls() = runComposeUiTest {
        val ui = mutableStateOf(AppUiState.PassengerReady(serviceCities = listOf(scheduledTestCity())))
        setContent { App(state = ui.value, placeSearchEnabled = false) }
        onNodeWithText("Choose on the map").performScrollTo().performClick()
        onNodeWithText("Schedule").performScrollTo().performClick()
        onNodeWithContentDescription("Choose date").performScrollTo().performClick()
        onNodeWithText("Use this").assertIsNotEnabled()
        onNodeWithText("Cancel").performClick()
        onNodeWithContentDescription("Choose time").performScrollTo().performClick()
        onNodeWithText("Use this").performClick()
        onNodeWithText("00:00").assertExists()
    }

    @Test fun failed_explicit_recheck_cannot_reuse_a_previous_clock_or_price_review() = runComposeUiTest {
        val booking = bookingFixture()
        val ui = mutableStateOf(AppUiState.PassengerReady(reviewedPointQuoteInput = booking.pickup to booking.destination).withScheduledTestCity())
        var clockReads = 0
        var commands = 0
        setContent { App(state = ui.value, placeSearchEnabled = false,
            onResolveScheduledLocalTime = { city, zone, date, time, id ->
                clockReads++
                if (clockReads == 1) ui.value = ui.value.copy(scheduledLocalTimeOptions = scheduledClockFixture(city, zone, date, time), scheduledLocalTimeReadId = id)
            },
            onEstimateScheduledPointToPoint = { time, _, _, _, id ->
                ui.value = ui.value.copy(scheduledBookingEstimateReadId = id, scheduledBookingEstimate = ScheduledBookingEstimate(
                    booking.cityId, booking.operatorId, booking.serviceType, null, time, booking.cityTimezone,
                    booking.pickup, booking.destination, booking.economics, booking.cancellationTerms, "CASH"))
            }, onSchedulePointToPoint = { _, _, _, _, _, _ -> commands++ }) }
        onNodeWithText("Schedule").performScrollTo().performClick()
        chooseScheduledClock("2026-11-01", "09:30")
        onNodeWithText("Review price and terms").performScrollTo().performClick()
        onNodeWithText("Confirm scheduled ride").performScrollTo().assertIsEnabled()
        onNodeWithText("Check pickup time").performScrollTo().performClick()
        assertEquals(2, clockReads)
        onNodeWithText("Review price and terms").assertDoesNotExist()
        onNodeWithText("Confirm scheduled ride").assertDoesNotExist()
        assertEquals(0, commands)
    }

    @Test fun native_clock_fields_remain_reachable_in_each_language_and_style_at_large_text() {
        val original = Locale.getDefault()
        try {
            for ((language, choose, schedule, date, time) in listOf(
                listOf("en", "Choose on the map", "Schedule", "Date", "Time"),
                listOf("fr", "Choisir sur la carte", "Planifier", "Date", "Heure"),
                listOf("ar", "اختر على الخريطة", "جدولة", "التاريخ", "الوقت"),
            )) {
                Locale.setDefault(Locale.forLanguageTag(language))
                for (style in TaxiStyle.entries) {
                    val preferences = TaxiStylePreferences(object : TaxiStyleStore {
                        override fun read() = style.storageValue
                        override fun write(value: String) = Unit
                    })
                    runComposeUiTest {
                        setContent { CompositionLocalProvider(LocalDensity provides Density(1f, 2f)) {
                            Box(Modifier.size(360.dp, 800.dp).testTag("clock-viewport")) {
                                App(state = AppUiState.PassengerReady(serviceCities = listOf(scheduledTestCity())),
                                    placeSearchEnabled = false, stylePreferences = preferences)
                            }
                        } }
                        onNodeWithText(choose).performScrollTo().performClick()
                        onNodeWithText(schedule).performScrollTo().performClick()
                        for (label in listOf(date, time)) {
                            val field = onNodeWithText(label)
                            field.performScrollTo().assertIsDisplayed()
                            val bounds = field.getUnclippedBoundsInRoot()
                            val viewport = onNodeWithTag("clock-viewport").getUnclippedBoundsInRoot()
                            assertTrue(bounds.left >= viewport.left && bounds.right <= viewport.right)
                            assertTrue(bounds.top >= viewport.top && bounds.bottom <= viewport.bottom)
                        }
                        onNodeWithContentDescription(if (language == "fr") "Choisir la date" else if (language == "ar") "اختر التاريخ" else "Choose date")
                            .performScrollTo().assertIsDisplayed()
                        System.getenv("TAXIMOBILE_SCHEDULED_INPUT_EVIDENCE_DIR")?.let { directory ->
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
