package org.example.taximobile.domain.drivers

/** Server-owned immutable amount/context. A list item is never proof of payment. */
data class PendingCashPayment(
    val paymentId: String,
    val rideId: String,
    val amount: String,
    val currency: String,
    val createdAt: String,
    val completedAt: String? = null,
) {
    init {
        require(paymentId.isNotBlank() && rideId.isNotBlank() && createdAt.isNotBlank())
        require(amount.matches(Regex("[0-9]+(?:\\.[0-9]{1,2})?")) && currency.matches(Regex("[A-Z]{3}")))
    }
}

/** A bounded oldest-first work queue, independent of ride-history pagination. */
data class PendingCashPaymentsPage(
    val items: List<PendingCashPayment>,
    val page: Int,
    val limit: Int,
    val total: Int,
) {
    init {
        require(page >= 1 && limit in 1..100 && total >= 0)
        require(items.size <= limit && items.size <= total)
        require(items.map { it.paymentId }.distinct().size == items.size)
        require(items.map { it.rideId }.distinct().size == items.size)
    }

    val hasPrevious: Boolean get() = page > 1
    val hasNext: Boolean get() = page.toLong() * limit < total
}
