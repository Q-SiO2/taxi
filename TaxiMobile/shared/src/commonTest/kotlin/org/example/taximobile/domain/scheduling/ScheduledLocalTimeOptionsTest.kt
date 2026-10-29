package org.example.taximobile.domain.scheduling

import kotlin.test.*

class ScheduledLocalTimeOptionsTest {
    private fun ordinary() = ScheduledLocalTimeOptions("city", "Africa/Casablanca", "2026-11-01", "09:30", true,
        "2026b", listOf(ScheduledLocalTimeOption("2026-11-01T08:30:00Z", 3600)))
    private fun ScheduledLocalTimeOptions.valid() = matchesRequest("city", "Africa/Casablanca", localDate, localTime)

    @Test fun normal_and_paused_context_retain_the_server_option_without_booking_authority() {
        val q = ordinary()
        assertTrue(q.valid())
        assertTrue(q.copy(bookingAvailable = false).valid())
        assertTrue(q.copy(options = listOf(q.options.single().copy(scheduledFor = "2026-11-01T09:30:00+01:00"))).valid())
    }

    @Test fun skipped_and_repeated_moroccan_hours_keep_zero_or_two_distinct_options() {
        val q = ordinary()
        assertTrue(q.copy(localDate = "2026-03-22", localTime = "02:30", options = emptyList()).valid())
        val overlap = q.copy(localDate = "2026-02-15", localTime = "02:30", options = listOf(
            ScheduledLocalTimeOption("2026-02-15T01:30:00Z", 3600), ScheduledLocalTimeOption("2026-02-15T02:30:00Z", 0)))
        assertTrue(overlap.valid())
        assertFalse(overlap.copy(options = overlap.options.reversed()).valid())
        assertFalse(overlap.copy(options = listOf(overlap.options.first(), overlap.options.first())).valid())
    }

    @Test fun changed_context_missing_fields_or_unknown_zone_cannot_become_a_selection() {
        val q = ordinary()
        assertFalse(q.matchesRequest("other-city", q.cityTimezone, q.localDate, q.localTime))
        assertFalse(q.matchesRequest(q.cityId, "UTC", q.localDate, q.localTime))
        assertFalse(q.matchesRequest(q.cityId, q.cityTimezone, "2026-11-02", q.localTime))
        assertFalse(q.matchesRequest(q.cityId, q.cityTimezone, q.localDate, "10:30"))
        assertFalse(q.copy(cityId = "").matchesRequest("", q.cityTimezone, q.localDate, q.localTime))
        assertFalse(q.copy(rulesVersion = "").valid())
        assertFalse(q.copy(cityTimezone = "PRIVATE-invalid").matchesRequest(q.cityId, "PRIVATE-invalid", q.localDate, q.localTime))
    }

    @Test fun malformed_shifted_wrong_offset_or_excessive_options_are_rejected() {
        val q = ordinary(); val option = q.options.single()
        for (bad in listOf(q.copy(options = listOf(option.copy(scheduledFor = "PRIVATE-invalid"))),
            q.copy(options = listOf(option.copy(scheduledFor = "2026-11-01T08:30:00"))),
            q.copy(options = listOf(option.copy(scheduledFor = "2026-11-01T09:30:00Z"))),
            q.copy(options = listOf(option.copy(utcOffsetSeconds = 0))),
            q.copy(options = List(3) { option }))) assertFalse(bad.valid())
    }

    @Test fun non_hour_transition_keeps_both_exact_offsets() {
        val q = ScheduledLocalTimeOptions("city", "Australia/Lord_Howe", "2026-04-05", "01:45", true, "2026b", listOf(
            ScheduledLocalTimeOption("2026-04-04T14:45:00Z", 39600), ScheduledLocalTimeOption("2026-04-04T15:15:00Z", 37800)))
        assertTrue(q.matchesRequest(q.cityId, q.cityTimezone, q.localDate, q.localTime))
    }

    @Test fun clock_input_is_strict_minute_precision_with_no_offset_or_silent_twenty_four_hour_normalization() {
        assertTrue(isScheduledLocalClockInput("2026-11-01", "09:30"))
        for ((date, time) in listOf("2026-02-30" to "09:30", "2026-2-03" to "09:30", "2026-11-01" to "9:30",
            "2026-11-01" to "24:00", "2026-11-01" to "09:30:00", "2026-11-01" to "09:30Z")) {
            assertFalse(isScheduledLocalClockInput(date, time))
        }
    }
}
