package org.example.taximobile.domain.scheduling

import org.example.taximobile.domain.rides.Coordinates
import kotlin.time.TimeMark
import kotlin.time.TimeSource

/** Exact server amounts. Clients display these values and never recompute allocations. */
data class ScheduledEconomics(
    val transportFare: String,
    val schedulingSurcharge: String,
    val operatorServiceFee: String,
    val passengerTotal: String,
    val expectedDriverNet: String,
    val operatorAllocation: String,
    val currency: String,
    val pricingRuleVersion: String,
    val operatorFeePolicyVersion: String,
    val schedulingPolicyVersion: String,
)

data class ScheduledCancellationTerms(
    val passengerCancelCutoffMinutes: Int,
    val surchargeRefundMode: String,
    val summary: String,
) {
    /** Client compatibility for review only; the backend decides all refunds. */
    val isSupportedForReview: Boolean
        get() = passengerCancelCutoffMinutes in 0..10080 && surchargeRefundMode in setOf(
            "ALWAYS_FULL", "FULL_BEFORE_CUTOFF", "NON_REFUNDABLE",
        )
}

data class ScheduledBookingEstimate(
    val cityId: String,
    val operatorId: String,
    val serviceType: String,
    val fixedRouteDirectionVersionId: String?,
    val scheduledFor: String,
    val cityTimezone: String,
    val pickup: Coordinates,
    val destination: Coordinates,
    val economics: ScheduledEconomics,
    val cancellationTerms: ScheduledCancellationTerms,
    val paymentMethod: String,
)

data class ScheduledBooking(
    val id: String,
    val cityId: String,
    val operatorId: String,
    val serviceType: String,
    val fixedRouteDirectionVersionId: String?,
    val scheduledFor: String,
    val cityTimezone: String,
    val status: String,
    val pickup: Coordinates,
    val destination: Coordinates,
    val economics: ScheduledEconomics,
    val cancellationTerms: ScheduledCancellationTerms,
    val driverCommitted: Boolean,
    val liveRideId: String?,
    val cancellationFinancialOutcome: String?,
    val createdAt: String,
)

data class ScheduledOffer(
    val id: String,
    val bookingId: String,
    val status: String,
    val cityId: String,
    val serviceType: String,
    val scheduledFor: String,
    val cityTimezone: String,
    val expiresAt: String,
    val pickup: Coordinates,
    val destination: Coordinates,
    val economics: ScheduledEconomics,
    val cancellationTerms: ScheduledCancellationTerms,
    val serverTime: String,
    /** Conservative elapsed-time anchor captured before the owned list request. */
    val readStartedAt: TimeMark = TimeSource.Monotonic.markNow(),
)

data class ScheduledCommitment(
    val id: String,
    val bookingId: String,
    val cityId: String,
    val serviceType: String,
    val scheduledFor: String,
    val cityTimezone: String,
    val status: String,
    val protectedFrom: String,
    val protectedUntil: String,
    val pickup: Coordinates,
    val destination: Coordinates,
    val economics: ScheduledEconomics,
)

data class ScheduledOfferPreference(
    val cityId: String,
    val enabled: Boolean,
    val updatedAt: String,
)

interface ScheduledBookingGateway {
    /** Null explicitly means this gateway lacks clock-resolution capability. */
    suspend fun localTimeOptions(cityId: String, cityTimezone: String, localDate: String, localTime: String): ScheduledLocalTimeOptions? = null
    suspend fun passengerBookings(page: Int = 1): ScheduledBookingPage
    suspend fun passengerBooking(bookingId: String): ScheduledBooking
    suspend fun estimatePointToPoint(
        scheduledFor: String,
        cityId: String?,
        pickup: Coordinates,
        destination: Coordinates,
    ): ScheduledBookingEstimate
    suspend fun estimateFixedRoute(
        scheduledFor: String,
        directionVersionId: String,
    ): ScheduledBookingEstimate
    suspend fun createPointToPoint(
        scheduledFor: String,
        cityId: String?,
        pickup: Coordinates,
        destination: Coordinates,
        passengerNote: String? = null,
        reviewedEconomics: ScheduledEconomics,
    ): ScheduledBooking

    suspend fun createFixedRoute(
        scheduledFor: String,
        directionVersionId: String,
        passengerNote: String? = null,
        reviewedEconomics: ScheduledEconomics,
    ): ScheduledBooking

    suspend fun cancelPassengerBooking(bookingId: String, reason: String): ScheduledBooking
    suspend fun driverOffers(): List<ScheduledOffer>
    suspend fun driverCommitments(): List<ScheduledCommitment>
    suspend fun driverPreferences(): List<ScheduledOfferPreference>
    suspend fun setDriverPreference(cityId: String, enabled: Boolean): ScheduledOfferPreference
    suspend fun acceptOffer(offerId: String): ScheduledCommitment
    suspend fun declineOffer(offerId: String, reason: String? = null): ScheduledOffer
}
