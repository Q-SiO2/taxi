package org.example.taximobile.feature.app

import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverRideOffer
import org.example.taximobile.domain.drivers.DriverEarnings
import org.example.taximobile.domain.rides.FareEstimate
import org.example.taximobile.domain.rides.RideReceipt
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideSummary
import org.example.taximobile.domain.rides.AssignedDriver
import org.example.taximobile.domain.rides.LastKnownDriverLocation
import org.example.taximobile.domain.drivers.DriverRideSummary
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.support.SupportTicket
import org.example.taximobile.domain.passengers.PassengerProfile
import org.example.taximobile.domain.routing.RoutePlan
import org.example.taximobile.domain.cooperatives.CooperativeMembership
import org.example.taximobile.feature.ui.text.UiMessage
import org.jetbrains.compose.resources.StringResource
import taximobile.shared.generated.resources.*

/**
 * Render-only state supplied by a coordinator. None of these values creates or
 * advances a ride; a refresh from the backend remains authoritative.
 */
sealed interface AppUiState {
    data object RestoringSession : AppUiState
    data object RegisteringAccount : AppUiState
    data class SignedOut(
        val message: UiMessage? = null,
        val registrationCompleted: Boolean = false,
        val suggestedIdentifier: String? = null,
        val showRegistrationForm: Boolean = false,
    ) : AppUiState
    data class Offline(val message: UiMessage) : AppUiState
    data class DriverApplicationRequired(val displayName: String) : AppUiState
    data class DriverApplicationPending(val verificationStatus: String) : AppUiState
    data class PassengerReady(
        val profile: PassengerProfile? = null,
        val activeRideId: String? = null,
        val activeRide: RideStatus? = null,
        val assignedDriver: AssignedDriver? = null,
        val lastKnownDriverLocation: LastKnownDriverLocation? = null,
        val pickup: org.example.taximobile.domain.rides.Coordinates? = null,
        val destination: org.example.taximobile.domain.rides.Coordinates? = null,
        val fareEstimate: FareEstimate? = null,
        val routePlan: RoutePlan? = null,
        val routeUnavailable: Boolean = false,
        val rateableRideId: String? = null,
        val rideHistory: List<RideSummary> = emptyList(),
        val latestCompletedReceipt: RideReceipt? = null,
        val selectedHistoryRide: RideSummary? = null,
        val selectedHistoryReceipt: RideReceipt? = null,
        val notifications: List<AppNotification> = emptyList(),
        val supportTickets: List<SupportTicket> = emptyList(),
    ) : AppUiState
    data class DriverReady(
        val availability: DriverAvailabilityStatus,
        val displayName: String? = null,
        val verificationStatus: String? = null,
        val accountStatus: String? = null,
        val activeVehicleId: String? = null,
        val credentials: List<DriverCredential> = emptyList(),
        val vehicles: List<DriverVehicle> = emptyList(),
        val activeRideId: String? = null,
        val activeRide: RideStatus? = null,
        val currentLocation: org.example.taximobile.domain.rides.Coordinates? = null,
        val pickup: org.example.taximobile.domain.rides.Coordinates? = null,
        val destination: org.example.taximobile.domain.rides.Coordinates? = null,
        val routePlan: RoutePlan? = null,
        val routeUnavailable: Boolean = false,
        val pendingCashRideId: String? = null,
        val offers: List<DriverRideOffer> = emptyList(),
        val earnings: DriverEarnings? = null,
        val rideHistory: List<DriverRideSummary> = emptyList(),
        val selectedHistoryRide: RideSummary? = null,
        val selectedHistoryRating: RideRating? = null,
        val notifications: List<AppNotification> = emptyList(),
        val supportTickets: List<SupportTicket> = emptyList(),
        val cooperativeMembership: CooperativeMembership? = null,
    ) : AppUiState
}

/** True only for states reached after the backend has established a session. */
fun AppUiState.hasAuthenticatedSession(): Boolean = when (this) {
    is AppUiState.PassengerReady,
    is AppUiState.DriverReady,
    is AppUiState.DriverApplicationRequired,
    is AppUiState.DriverApplicationPending -> true
    is AppUiState.RestoringSession,
    is AppUiState.RegisteringAccount,
    is AppUiState.SignedOut,
    is AppUiState.Offline -> false
}

fun RideStatus.passengerStatusResource(): StringResource = when (this) {
    RideStatus.REQUESTED,
    RideStatus.MATCHING -> Res.string.ride_status_matching
    RideStatus.ACCEPTED,
    RideStatus.DRIVER_EN_ROUTE -> Res.string.ride_status_driver_on_way
    RideStatus.DRIVER_ARRIVED -> Res.string.ride_status_driver_arrived
    RideStatus.IN_PROGRESS -> Res.string.ride_status_in_progress
    RideStatus.COMPLETED -> Res.string.ride_status_completed
    RideStatus.CANCELLED -> Res.string.ride_status_cancelled
    RideStatus.UNMATCHED -> Res.string.ride_status_unmatched
}

fun driverVerificationStatusResource(status: String): StringResource = when (status) {
    "NOT_STARTED" -> Res.string.verification_not_started
    "SUBMITTED" -> Res.string.verification_submitted
    "UNDER_REVIEW" -> Res.string.verification_under_review
    "VERIFIED", "APPROVED" -> Res.string.verification_verified
    "REJECTED" -> Res.string.verification_rejected
    "ADDITIONAL_INFORMATION_REQUIRED" -> Res.string.verification_more_information
    else -> Res.string.verification_unknown
}

fun driverAccountStatusResource(status: String): StringResource = when (status) {
    "PENDING" -> Res.string.account_status_pending
    "ACTIVE" -> Res.string.account_status_active
    "SUSPENDED" -> Res.string.account_status_suspended
    "DEACTIVATED" -> Res.string.account_status_deactivated
    else -> Res.string.account_status_unknown
}
