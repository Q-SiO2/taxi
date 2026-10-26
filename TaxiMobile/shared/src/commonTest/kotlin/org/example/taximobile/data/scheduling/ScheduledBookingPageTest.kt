package org.example.taximobile.data.scheduling

import kotlinx.serialization.json.Json
import org.example.taximobile.domain.scheduling.ScheduledBookingPage
import kotlin.test.*

class ScheduledBookingPageTest {
    @Test fun last_page_preserves_context_and_has_bounded_navigation() {
        val page = ScheduledBookingPage(listOf(bookingFixture()), 2, 20, 21)
        assertTrue(page.hasPrevious)
        assertFalse(page.hasNext)
        assertEquals("booking-21", page.items.single().id)
        assertFalse(ScheduledBookingPage(emptyList(), Int.MAX_VALUE, 100, Int.MAX_VALUE).hasNext)
    }
    @Test fun invalid_counts_identifiers_and_duplicate_records_are_rejected() {
        for (build in listOf<() -> ScheduledBookingPage>(
            { ScheduledBookingPage(emptyList(), 0, 20, 0) },
            { ScheduledBookingPage(emptyList(), 1, 101, 0) },
            { ScheduledBookingPage(emptyList(), 1, 20, -1) },
            { ScheduledBookingPage(List(21) { bookingFixture("$it") }, 1, 20, 21) },
            { ScheduledBookingPage(listOf(bookingFixture()), 1, 20, 0) },
            { ScheduledBookingPage(listOf(bookingFixture("")), 1, 20, 1) },
            { ScheduledBookingPage(listOf(bookingFixture(), bookingFixture()), 1, 20, 2) },
        )) assertFailsWith<IllegalArgumentException> { build() }
    }
    @Test fun wire_page_and_limit_must_match_the_requested_boundary() {
        val response = Json.decodeFromString<ScheduledBookingListResponse>("""{"items":[],"page":2,"limit":20,"total":21}""")
        assertEquals(2, response.toDomain(2).page)
        assertFailsWith<IllegalArgumentException> { response.toDomain(1) }
        assertFailsWith<IllegalArgumentException> { response.copy(limit = 100).toDomain(2) }
    }
}
