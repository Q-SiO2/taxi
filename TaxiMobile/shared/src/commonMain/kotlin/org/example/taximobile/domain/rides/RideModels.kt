package org.example.taximobile.domain.rides

enum class RideStatus {
    REQUESTED,
    MATCHING,
    ACCEPTED,
    DRIVER_EN_ROUTE,
    DRIVER_ARRIVED,
    IN_PROGRESS,
    COMPLETED,
    CANCELLED,
    UNMATCHED,
}

enum class RidePaymentMethod {
    CASH,
    MANUAL_TRANSFER,
    /** A newer backend method this client must never reinterpret as cash. */
    UNKNOWN,
}

enum class RideServiceType { ON_DEMAND, FIXED_ROUTE, SCHEDULED, UNKNOWN }

enum class RideCoordinationCode {
    PASSENGER_AT_PICKUP,
    PASSENGER_NEEDS_MORE_TIME,
    PASSENGER_CANNOT_FIND_DRIVER,
    DRIVER_ON_MY_WAY,
    DRIVER_AT_PICKUP,
    DRIVER_CANNOT_FIND_PASSENGER,
    UNKNOWN,
}

enum class RideCoordinationSenderRole { PASSENGER, DRIVER, UNKNOWN }

data class RideCoordinationMessage(
    val id: String,
    val rideId: String,
    val senderRole: RideCoordinationSenderRole,
    val code: RideCoordinationCode,
    val createdAt: String,
)

data class LocalizedText(
    val en: String,
    val fr: String,
    val ar: String,
) {
    fun preferred(language: String): String = when (language.lowercase()) {
        "ar" -> ar
        "fr" -> fr
        else -> en
    }.ifBlank { en.ifBlank { fr.ifBlank { ar } } }
}

data class FixedRouteRideSummary(
    val directionVersionId: String,
    val routeVersionId: String,
    val routeCode: String,
    val routeName: LocalizedText,
    val directionCode: String,
    val startName: LocalizedText,
    val finishName: LocalizedText,
)

data class PublicRideCity(
    val id: String,
    val code: String,
    val name: LocalizedText,
    val timezone: String,
    val lifecycleStatus: String,
    val bookingAvailable: Boolean,
)

data class PublishedFixedRouteStop(
    val sequence: Int,
    val name: LocalizedText,
    val location: Coordinates,
)

data class PublishedFixedRouteDirection(
    val id: String,
    val routeVersionId: String,
    val routeCode: String,
    val routeName: LocalizedText,
    val directionCode: String,
    val startName: LocalizedText,
    val finishName: LocalizedText,
    val start: Coordinates,
    val finish: Coordinates,
    /** Static [longitude, latitude] line owned by the published catalog. */
    val geometry: List<Coordinates>,
    val flatFare: String,
    val currency: String,
    val immediateBookingEnabled: Boolean,
    val scheduledBookingEnabled: Boolean,
    val stops: List<PublishedFixedRouteStop>,
)

data class FixedRouteCatalog(
    val city: PublicRideCity,
    val directions: List<PublishedFixedRouteDirection>,
)

data class RideSummary(
    val id: String,
    val status: RideStatus,
    val completedAt: String? = null,
    val driver: AssignedDriver? = null,
    val lastKnownDriverLocation: LastKnownDriverLocation? = null,
    val pickup: Coordinates? = null,
    val destination: Coordinates? = null,
    val paymentMethod: RidePaymentMethod = RidePaymentMethod.CASH,
    val serviceType: RideServiceType = RideServiceType.ON_DEMAND,
    val fixedRoute: FixedRouteRideSummary? = null,
    val latestCoordinationMessage: RideCoordinationMessage? = null,
)

data class AssignedDriver(val displayName: String, val vehicle: AssignedVehicle)

data class AssignedVehicle(val make: String, val model: String, val color: String, val taxiIdentifier: String?)

/** A single backend-authorized active-ride observation; never presented as a live stream. */
data class LastKnownDriverLocation(
    val coordinates: Coordinates,
    val observedAt: String,
    val accuracyMeters: Double? = null,
)

/**
 * Backend-calculated money allocation for a quote or finalized fare.
 *
 * Every amount is intentionally kept as the exact decimal string supplied by
 * the API. Mobile clients render these facts but never recompute a fee, total,
 * or driver settlement.
 */
data class FareEconomics(
    val transportFare: String,
    val schedulingSurcharge: String,
    val operatorServiceFee: String,
    val passengerTotal: String,
    val expectedDriverNet: String,
    val operatorAllocation: String,
    val operatorFeePolicyVersion: String,
    val operatorFeeCalculationMode: String,
    val operatorFeeFundingMode: String,
    val schedulingPolicyVersion: String? = null,
)

data class FareEstimate(
    val amount: String,
    val currency: String,
    val pricingRuleVersion: String,
    val paymentMethods: List<RidePaymentMethod> = listOf(RidePaymentMethod.CASH),
    /** Null only when decoding a response from a pre-economics backend. */
    val economics: FareEconomics? = null,
    val serviceType: RideServiceType = RideServiceType.ON_DEMAND,
    val fixedRoute: FixedRouteRideSummary? = null,
)

data class FareComponent(val code: String, val label: String, val amount: String)

data class FinalRideFare(
    val amount: String,
    val currency: String,
    val pricingRuleVersion: String? = null,
    val components: List<FareComponent> = emptyList(),
    /** Immutable finalized allocation; null for legacy fare records. */
    val economics: FareEconomics? = null,
)

/** A passenger-facing read of backend-finalized fare and payment facts. */
data class RideReceipt(
    val rideId: String,
    val completedAt: String,
    val fare: FinalRideFare,
    val paymentMethod: String,
    val paymentStatus: String,
    val manualTransfer: ManualTransferInstructions? = null,
    val refunds: RideRefundSummary? = null,
)

data class RideRefundSummary(
    val refundedAmount: String,
    val netPaidAmount: String,
    val currency: String,
    val items: List<RideRefund>,
)

data class RideRefund(
    val id: String,
    val amount: String,
    val currency: String,
    val reason: String,
    val refundedAt: String,
)

data class ManualTransferInstructions(
    val recipientName: String,
    val bankAccount: String?,
    val walletId: String?,
    val paymentReference: String,
    val latestClaimStatus: String? = null,
)

/** Feedback returned by the backend for a ride participant; no user IDs are exposed. */
data class RideRating(
    val id: String,
    val score: Int,
    val comment: String?,
)

/** The client renders backend-confirmed state; it does not transition rides locally. */
interface RideGateway {
    suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate
    suspend fun listRides(): List<RideSummary>
    suspend fun currentRide(id: String): RideSummary
    suspend fun finalFare(id: String): FinalRideFare
    suspend fun receipt(id: String): RideReceipt
    suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary
    suspend fun requestRide(
        pickup: Coordinates,
        destination: Coordinates,
        paymentMethod: RidePaymentMethod,
    ): RideSummary = if (paymentMethod == RidePaymentMethod.CASH) {
        requestRide(pickup, destination)
    } else {
        error("This ride gateway does not support manual transfers.")
    }
    suspend fun submitManualTransfer(id: String, payerReference: String?): RideReceipt =
        error("This ride gateway does not support manual transfers.")
    suspend fun cancelRide(id: String, reason: String): RideSummary
    suspend fun ratings(id: String): List<RideRating>
    suspend fun submitRating(id: String, score: Int, comment: String?): RideRating
    suspend fun sendCoordinationMessage(
        id: String,
        code: RideCoordinationCode,
    ): RideCoordinationMessage = error("This ride gateway does not support coordination messages.")
    suspend fun publicCities(): List<PublicRideCity> = emptyList()
    suspend fun fixedRoutes(cityId: String): FixedRouteCatalog? = null
    suspend fun estimateFixedRoute(directionVersionId: String): FareEstimate =
        error("This ride gateway does not support fixed routes.")
    suspend fun requestFixedRoute(
        directionVersionId: String,
        paymentMethod: RidePaymentMethod,
    ): RideSummary = error("This ride gateway does not support fixed routes.")
}

data class Coordinates(
    val latitude: Double,
    val longitude: Double,
    /** Optional backend-returned display text; coordinates remain authoritative. */
    val address: String? = null,
)
