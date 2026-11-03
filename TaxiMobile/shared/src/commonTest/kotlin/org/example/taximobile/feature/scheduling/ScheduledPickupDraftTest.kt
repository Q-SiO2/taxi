package org.example.taximobile.feature.scheduling

import kotlin.test.*
import org.example.taximobile.domain.rides.LocalizedText
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.domain.scheduling.ScheduledLocalTimeOption
import org.example.taximobile.domain.scheduling.ScheduledLocalTimeOptions

class ScheduledPickupDraftTest {
    private val city = PublicRideCity("fes", "FES", LocalizedText("Fès", "Fès", "فاس"), "Africa/Casablanca", "ACTIVE", true)
    private fun ordinary() = ScheduledLocalTimeOptions("fes", city.timezone, "2026-11-01", "09:30", true,
        "2026b", listOf(ScheduledLocalTimeOption("2026-11-01T08:30:00Z", 3600)))
    private fun draft() = ScheduledPickupDraft().apply { editDate("2026-11-01"); editTime("09:30") }

    @Test fun arabic_and_eastern_digits_are_normalized_before_strict_clock_validation() {
        val value = ScheduledPickupDraft().apply { editDate("٢٠٢٦-١١-٠١"); editTime("۰۹:۳۰") }
        assertEquals("2026-11-01", value.date)
        assertEquals("09:30", value.time)
        assertNotNull(value.beginRead(city, "read"))
        value.editTime("٢٤:٠٠")
        assertNull(value.beginRead(city, "bad"))
    }

    @Test fun a_failed_new_read_cannot_reuse_retained_matching_old_options() {
        val value = draft(); value.beginRead(city, "old")
        assertTrue(value.acceptRead("old", ordinary(), city))
        assertNotNull(value.selectedInstant)
        value.beginRead(city, "new")
        assertFalse(value.acceptRead("old", ordinary(), city))
        assertNull(value.resolution)
        assertNull(value.selectedInstant)
        assertTrue(value.acceptRead("new", ordinary(), city))
        assertEquals("2026-11-01T08:30:00Z", value.selectedInstant)
    }

    @Test fun editing_and_returning_to_the_old_clock_still_requires_a_new_read() {
        val value = draft(); value.beginRead(city, "old")
        value.editTime("10:30"); value.editTime("09:30")
        assertFalse(value.acceptRead("old", ordinary(), city))
        assertNull(value.requested)
        assertNull(value.selectedInstant)
    }

    @Test fun changed_city_metadata_and_unavailable_booking_cannot_enable_selection() {
        val value = draft(); value.beginRead(city, "read")
        assertFalse(value.acceptRead("read", ordinary(), city.copy(timezone = "UTC")))
        assertFalse(value.acceptRead("read", ordinary(), city.copy(bookingAvailable = false)))
        assertTrue(value.acceptRead("read", ordinary().copy(bookingAvailable = false), city))
        value.choose("2026-11-01T08:30:00Z")
        assertNull(value.selectedInstant)
    }

    @Test fun overlap_needs_an_explicit_choice_and_each_changed_choice_invalidates_review_revision() {
        val value = draft().apply { editDate("2026-02-15"); editTime("02:30"); beginRead(city, "read") }
        val options = ordinary().copy(localDate = "2026-02-15", localTime = "02:30", options = listOf(
            ScheduledLocalTimeOption("2026-02-15T01:30:00Z", 3600), ScheduledLocalTimeOption("2026-02-15T02:30:00Z", 0)))
        assertTrue(value.acceptRead("read", options, city))
        assertNull(value.selectedInstant)
        value.choose("PRIVATE-invalid"); assertNull(value.selectedInstant)
        value.choose(options.options[1].scheduledFor)
        val revision = value.selectionRevision
        assertEquals(options.options[1].scheduledFor, value.selectedInstant)
        value.choose(options.options[0].scheduledFor)
        assertTrue(value.selectionRevision > revision)
    }

    @Test fun gap_options_never_choose_an_instant() {
        val value = draft().apply { editDate("2026-03-22"); editTime("02:30"); beginRead(city, "read") }
        assertTrue(value.acceptRead("read", ordinary().copy(localDate = "2026-03-22", localTime = "02:30", options = emptyList()), city))
        assertNull(value.selectedInstant)
    }

    @Test fun restored_inputs_never_restore_a_clock_read_or_review_authority() {
        val value = draft(); value.beginRead(city, "old")
        assertTrue(value.acceptRead("old", ordinary(), city))
        val restored = assertNotNull(ScheduledPickupDraft.Saver.restore(listOf(value.date, value.time)))
        assertEquals(value.date, restored.date)
        assertEquals(value.time, restored.time)
        assertNull(restored.requested)
        assertNull(restored.resolution)
        assertNull(restored.acceptedReadId)
        assertNull(restored.selectedInstant)
    }
}
