package org.example.taximobile.operations.model

import kotlin.test.*
import org.example.taximobile.domain.scheduling.scheduledCityTime
import org.example.taximobile.domain.scheduling.scheduledCityWindow
import kotlin.time.TimeSource

class ScheduledCityTimeBrowserTest {
    @Test fun both_browser_targets_load_named_city_rules_including_moroccan_changes() {
        val started = TimeSource.Monotonic.markNow()
        val first = scheduledCityTime("2026-11-01T08:30:00Z","Africa/Casablanca")
        println("Scheduled city-time cold lookup ms: ${started.elapsedNow().inWholeMilliseconds}")
        assertEquals("UTC+01:00",first?.utcOffset)
        assertEquals("UTC",scheduledCityTime("2026-02-22T08:30:00Z","Africa/Casablanca")?.utcOffset)
        assertEquals("14:15",scheduledCityTime("2026-11-01T08:30:00Z","Asia/Kathmandu")?.time)
        assertEquals("09:30:12.123456789",scheduledCityTime("2026-11-01T08:30:12.123456789Z","Africa/Casablanca")?.time)
        println("Scheduled city-time browser case ms: ${started.elapsedNow().inWholeMilliseconds}")
    }
    @Test fun repeated_local_hour_is_unambiguous_and_invalid_data_has_no_fallback() {
        val window = scheduledCityWindow("2026-02-15T01:30:00Z","2026-02-15T02:30:00Z","Africa/Casablanca")!!
        assertEquals(window.from.time,window.until.time)
        assertNotEquals(window.from.utcOffset,window.until.utcOffset)
        assertNull(scheduledCityTime("PRIVATE-invalid","Africa/Casablanca"))
        assertNull(scheduledCityTime("2026-11-01T08:30:00Z","PRIVATE-invalid"))
    }
}
