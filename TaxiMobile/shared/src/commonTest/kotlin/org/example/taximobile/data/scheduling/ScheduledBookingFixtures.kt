package org.example.taximobile.data.scheduling

import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.scheduling.*

internal fun bookingFixture(id: String = "booking-21") = ScheduledBooking(
    id, "synthetic-city", "synthetic-union", "POINT_TO_POINT", null,
    "2026-11-01T08:30:00Z", "Africa/Casablanca", "SCHEDULED",
    Coordinates(34.03, -5.00), Coordinates(34.04, -5.01),
    ScheduledEconomics("8.00", "3.00", "0.00", "11.00", "8.00", "3.00", "MAD", "fare-v1", "fee-v1", "schedule-v1"),
    ScheduledCancellationTerms(60, "FULL_BEFORE_CUTOFF", "Synthetic cancellation terms"),
    false, null, null, "2026-10-26T08:00:00Z",
)

internal fun bookingWire(id: String) = """{
 "id":"$id","city_id":"synthetic-city","operator_id":"synthetic-union","service_type":"POINT_TO_POINT",
 "scheduled_for":"2026-11-01T08:30:00Z","city_timezone":"Africa/Casablanca","status":"SCHEDULED",
 "pickup":{"latitude":34.03,"longitude":-5.00},"destination":{"latitude":34.04,"longitude":-5.01},
 "economics":{"transport_fare":"8.00","scheduling_surcharge":"3.00","operator_service_fee":"0.00",
 "passenger_total":"11.00","expected_driver_net":"8.00","operator_allocation":"3.00","currency":"MAD",
 "pricing_rule_version":"fare-v1","operator_fee_policy_version":"fee-v1","scheduling_policy_version":"schedule-v1"},
 "cancellation_terms":{"passenger_cancel_cutoff_minutes":60,"surcharge_refund_mode":"FULL_BEFORE_CUTOFF","summary":"Synthetic terms"},
 "driver_committed":false,"created_at":"2026-10-26T08:00:00Z"
}"""

internal class PagedBookingFixture : ScheduledBookingGateway {
    val pages = mutableListOf<Int>()
    val cancelled = mutableListOf<String>()
    var onRead: (suspend (Int) -> ScheduledBookingPage)? = null
    val detailReads = mutableListOf<String>()
    var onDetail: (suspend (String) -> ScheduledBooking)? = null
    override suspend fun passengerBooking(bookingId: String): ScheduledBooking {
        detailReads += bookingId
        return onDetail?.invoke(bookingId) ?: bookingFixture(bookingId)
    }
    override suspend fun passengerBookings(page: Int): ScheduledBookingPage {
        pages += page
        return onRead?.invoke(page) ?: ScheduledBookingPage(
            (if (page == 1) (1..20) else (21..21)).map { bookingFixture("booking-$it").let { b ->
                if (b.id in cancelled) b.copy(status = "CANCELLED", cancellationFinancialOutcome = "NO_CHARGE") else b
            } }, page, 20, 21,
        )
    }
    override suspend fun cancelPassengerBooking(bookingId: String, reason: String): ScheduledBooking {
        cancelled += bookingId
        return bookingFixture(bookingId).copy(status = "CANCELLED")
    }
    override suspend fun estimatePointToPoint(scheduledFor: String, cityId: String?, pickup: Coordinates, destination: Coordinates): ScheduledBookingEstimate = error("No estimate during pagination")
    override suspend fun estimateFixedRoute(scheduledFor: String, directionVersionId: String): ScheduledBookingEstimate = error("No estimate during pagination")
    override suspend fun createPointToPoint(scheduledFor: String, cityId: String?, pickup: Coordinates, destination: Coordinates, passengerNote: String?, reviewedEconomics: ScheduledEconomics): ScheduledBooking = error("No creation during pagination")
    override suspend fun createFixedRoute(scheduledFor: String, directionVersionId: String, passengerNote: String?, reviewedEconomics: ScheduledEconomics): ScheduledBooking = error("No creation during pagination")
    override suspend fun driverOffers(): List<ScheduledOffer> = error("No driver reads during passenger pagination")
    override suspend fun driverCommitments(): List<ScheduledCommitment> = error("No driver reads during passenger pagination")
    override suspend fun driverPreferences(): List<ScheduledOfferPreference> = error("No driver reads during passenger pagination")
    override suspend fun setDriverPreference(cityId: String, enabled: Boolean): ScheduledOfferPreference = error("No preference mutation")
    override suspend fun acceptOffer(offerId: String): ScheduledCommitment = error("No acceptance during pagination")
    override suspend fun declineOffer(offerId: String, reason: String?): ScheduledOffer = error("No decline during pagination")
}
