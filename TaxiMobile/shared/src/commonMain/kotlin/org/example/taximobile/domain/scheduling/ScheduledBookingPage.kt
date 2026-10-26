package org.example.taximobile.domain.scheduling

/** One bounded server page; navigation never authorizes a booking transition. */
data class ScheduledBookingPage(
    val items: List<ScheduledBooking>,
    val page: Int,
    val limit: Int,
    val total: Int,
) {
    init {
        require(page >= 1 && limit in 1..100 && total >= 0)
        require(items.size <= limit && items.size <= total)
        require(items.all { it.id.isNotBlank() } && items.map { it.id }.distinct().size == items.size)
    }

    val hasPrevious: Boolean get() = page > 1
    val hasNext: Boolean get() = page.toLong() * limit < total
}
