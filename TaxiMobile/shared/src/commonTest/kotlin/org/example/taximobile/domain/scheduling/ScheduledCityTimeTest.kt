package org.example.taximobile.domain.scheduling

import kotlin.test.*

class ScheduledCityTimeTest {
    @Test fun city_rules_change_the_offset_during_moroccan_ramadan() {
        assertEquals(ScheduledCityTime("2026-11-01","09:30","UTC+01:00"), scheduledCityTime("2026-11-01T08:30:00Z","Africa/Casablanca"))
        assertEquals(ScheduledCityTime("2026-02-22","08:30","UTC"), scheduledCityTime("2026-02-22T08:30:00Z","Africa/Casablanca"))
    }

    @Test fun repeated_and_skipped_local_hours_retain_the_actual_offset() {
        val repeated = scheduledCityWindow("2026-02-15T01:30:00Z","2026-02-15T02:30:00Z","Africa/Casablanca")!!
        assertEquals(ScheduledCityTime("2026-02-15","02:30","UTC+01:00"),repeated.from)
        assertEquals(ScheduledCityTime("2026-02-15","02:30","UTC"),repeated.until)
        val skipped = scheduledCityWindow("2026-03-22T01:30:00Z","2026-03-22T02:30:00Z","Africa/Casablanca")!!
        assertEquals("01:30",skipped.from.time)
        assertEquals("03:30",skipped.until.time)
        assertEquals("UTC",skipped.from.utcOffset)
        assertEquals("UTC+01:00",skipped.until.utcOffset)
    }

    @Test fun date_rollover_and_non_hour_zones_do_not_use_a_fixed_moroccan_offset() {
        assertEquals(ScheduledCityTime("2026-11-02","00:30","UTC+01:00"),scheduledCityTime("2026-11-01T23:30:00Z","Africa/Casablanca"))
        assertEquals(ScheduledCityTime("2026-11-01","14:15","UTC+05:45"),scheduledCityTime("2026-11-01T08:30:00Z","Asia/Kathmandu"))
    }

    @Test fun equivalent_instants_and_fractional_seconds_keep_exact_display_meaning() {
        assertEquals(scheduledCityTime("2026-11-01T08:30:00Z","Africa/Casablanca"),scheduledCityTime("2026-11-01T09:30:00+01:00","Africa/Casablanca"))
        assertEquals("09:30:12.123456789",scheduledCityTime("2026-11-01T08:30:12.123456789Z","Africa/Casablanca")?.time)
        assertEquals("UTC",scheduledCityTime("2026-11-01T08:30:00Z","UTC")?.utcOffset)
    }

    @Test fun unsupported_zone_or_invalid_instant_never_falls_back_to_utc_or_device_time() {
        for (zone in listOf("","PRIVATE-invalid","UTC+01:00"," Africa/Casablanca ")) assertNull(scheduledCityTime("2026-11-01T08:30:00Z",zone))
        for (instant in listOf("","PRIVATE-invalid","2026-11-01T08:30:00","2026-02-30T08:30:00Z")) assertNull(scheduledCityTime(instant,"Africa/Casablanca"))
    }

    @Test fun invalid_protected_window_does_not_invent_endpoint_order() {
        assertNull(scheduledCityWindow("2026-11-01T09:00:00Z","2026-11-01T08:00:00Z","Africa/Casablanca"))
        assertNull(scheduledCityWindow("2026-11-01T08:00:00Z","2026-11-01T08:00:00Z","Africa/Casablanca"))
        assertNull(scheduledCityWindow("PRIVATE-invalid","2026-11-01T08:00:00Z","Africa/Casablanca"))
    }
}
