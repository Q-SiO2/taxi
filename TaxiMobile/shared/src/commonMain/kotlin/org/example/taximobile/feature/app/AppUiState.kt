package org.example.taximobile.feature.app

import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverRideOffer
import org.example.taximobile.domain.drivers.DriverEarnings
import org.example.taximobile.domain.rides.FareEstimate
import org.example.taximobile.domain.rides.FixedRouteCatalog
import org.example.taximobile.domain.rides.FixedRouteRideSummary
import org.example.taximobile.domain.rides.PublicRideCity
import org.example.taximobile.domain.rides.RideServiceType
import org.example.taximobile.domain.rides.RideReceipt
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideSummary
import org.example.taximobile.domain.rides.AssignedDriver
import org.example.taximobile.domain.rides.LastKnownDriverLocation
import org.example.taximobile.domain.rides.RideCoordinationMessage
import org.example.taximobile.domain.drivers.DriverRideSummary
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.drivers.DriverCityApplication
import org.example.taximobile.domain.drivers.DriverCityApplicationSummary
import org.example.taximobile.domain.drivers.DriverAuthorizedMarket
import org.example.taximobile.domain.drivers.RecruitingCity
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.safety.SafetyReport
import org.example.taximobile.domain.support.SupportTicket
import org.example.taximobile.domain.passengers.PassengerProfile
import org.example.taximobile.domain.places.PlaceSearch
import org.example.taximobile.domain.places.ReversePlace
import org.example.taximobile.domain.routing.RoutePlan
import org.example.taximobile.domain.cooperatives.CooperativeMembership
import org.example.taximobile.domain.auth.AccountRecoveryCodes
import org.example.taximobile.domain.auth.AccountSession
import org.example.taximobile.domain.scheduling.ScheduledBooking
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.domain.scheduling.ScheduledCommitment
import org.example.taximobile.domain.scheduling.ScheduledOffer
import org.example.taximobile.domain.scheduling.ScheduledOfferPreference
import org.example.taximobile.feature.ui.text.UiMessage
import org.jetbrains.compose.resources.StringResource
import taximobile.shared.generated.resources.*

data class AccountSecurityUiState(
    val loaded: Boolean = false,
    val sessions: List<AccountSession> = emptyList(),
    val recoveryCodes: AccountRecoveryCodes? = null,
    val message: UiMessage? = null,
)

data class PlaceDiscoveryUiState(
    /** Monotonic coordinator event used to apply reverse results exactly once. */
    val revision: Long = 0,
    val search: PlaceSearch? = null,
    val reverse: ReversePlace? = null,
)

/** Remove one-time recovery secrets from render state after explicit user acknowledgement. */
fun AppUiState.clearVisibleRecoveryCodes(): AppUiState = when (this) {
    is AppUiState.PassengerReady -> copy(
        accountSecurity = accountSecurity.copy(recoveryCodes = null, message = null),
    )
    is AppUiState.DriverReady -> copy(
        accountSecurity = accountSecurity.copy(recoveryCodes = null, message = null),
    )
    else -> this
}

/**
 * Render-only state supplied by a coordinator. None of these values creates or
 * advances a ride; a refresh from the backend remains authoritative.
 */
sealed interface AppUiState {
    data object RestoringSession : AppUiState
    data object RegisteringAccount : AppUiState
    data object RecoveringAccount : AppUiState
    data class UpgradeRequired(
        val minimumVersion: String,
        val policyRevision: String,
    ) : AppUiState
    data class SignedOut(
        val message: UiMessage? = null,
        val registrationCompleted: Boolean = false,
        val suggestedIdentifier: String? = null,
        val showRegistrationForm: Boolean = false,
        val showRecoveryForm: Boolean = false,
        val recoveryCompleted: Boolean = false,
    ) : AppUiState
    data class Offline(val message: UiMessage) : AppUiState
    data class DriverApplicationRequired(val displayName: String) : AppUiState
    data class DriverApplicationPending(val verificationStatus: String) : AppUiState
    data class DriverOnboarding(
        val displayName: String,
        val recruitingCities: List<RecruitingCity>,
        val applications: List<DriverCityApplicationSummary>,
        val selectedApplication: DriverCityApplication? = null,
        val vehicles: List<DriverVehicle> = emptyList(),
        val credentials: List<DriverCredential> = emptyList(),
        val message: UiMessage? = null,
    ) : AppUiState
    data class PassengerReady(
        val profile: PassengerProfile? = null,
        val activeRideId: String? = null,
        val activeRide: RideStatus? = null,
        val assignedDriver: AssignedDriver? = null,
        val lastKnownDriverLocation: LastKnownDriverLocation? = null,
        val latestCoordinationMessage: RideCoordinationMessage? = null,
        val pickup: org.example.taximobile.domain.rides.Coordinates? = null,
        val destination: org.example.taximobile.domain.rides.Coordinates? = null,
        val fareEstimate: FareEstimate? = null,
        val routePlan: RoutePlan? = null,
        val routeUnavailable: Boolean = false,
        val serviceCities: List<PublicRideCity> = emptyList(),
        val fixedRouteCatalog: FixedRouteCatalog? = null,
        val fixedRouteCatalogUnavailable: Boolean = false,
        val selectedFixedRouteDirectionId: String? = null,
        val activeServiceType: RideServiceType = RideServiceType.ON_DEMAND,
        val activeFixedRoute: FixedRouteRideSummary? = null,
        val rateableRideId: String? = null,
        val rideHistory: List<RideSummary> = emptyList(),
        val scheduledBookings: List<ScheduledBooking> = emptyList(),
        val scheduledBookingEstimate: ScheduledBookingEstimate? = null,
        val latestCompletedReceipt: RideReceipt? = null,
        val selectedHistoryRide: RideSummary? = null,
        val selectedHistoryReceipt: RideReceipt? = null,
        val notifications: List<AppNotification> = emptyList(),
        val supportTickets: List<SupportTicket> = emptyList(),
        val safetyReports: List<SafetyReport> = emptyList(),
        val accountSecurity: AccountSecurityUiState = AccountSecurityUiState(),
        val placeDiscovery: PlaceDiscoveryUiState = PlaceDiscoveryUiState(),
    ) : AppUiState
    data class DriverReady(
        val availability: DriverAvailabilityStatus,
        val displayName: String? = null,
        val verificationStatus: String? = null,
        val accountStatus: String? = null,
        val activeVehicleId: String? = null,
        val onlineCityId: String? = null,
        val onlineServiceType: String? = null,
        val authorizedMarkets: List<DriverAuthorizedMarket> = emptyList(),
        val cityAuthorizationRequired: Boolean = false,
        val cityAuthorizationLoadFailed: Boolean = false,
        val credentials: List<DriverCredential> = emptyList(),
        val vehicles: List<DriverVehicle> = emptyList(),
        val activeRideId: String? = null,
        val activeRide: RideStatus? = null,
        val currentLocation: org.example.taximobile.domain.rides.Coordinates? = null,
        val latestCoordinationMessage: RideCoordinationMessage? = null,
        val pickup: org.example.taximobile.domain.rides.Coordinates? = null,
        val destination: org.example.taximobile.domain.rides.Coordinates? = null,
        val routePlan: RoutePlan? = null,
        val routeUnavailable: Boolean = false,
        val activeServiceType: RideServiceType = RideServiceType.ON_DEMAND,
        val activeFixedRoute: FixedRouteRideSummary? = null,
        val pendingCashRideId: String? = null,
        val offers: List<DriverRideOffer> = emptyList(),
        val scheduledOffers: List<ScheduledOffer> = emptyList(),
        val scheduledCommitments: List<ScheduledCommitment> = emptyList(),
        val scheduledOfferPreferences: List<ScheduledOfferPreference> = emptyList(),
        val earnings: DriverEarnings? = null,
        val rideHistory: List<DriverRideSummary> = emptyList(),
        val selectedHistoryRide: RideSummary? = null,
        val selectedHistoryRating: RideRating? = null,
        val notifications: List<AppNotification> = emptyList(),
        val supportTickets: List<SupportTicket> = emptyList(),
        val safetyReports: List<SafetyReport> = emptyList(),
        val cooperativeMembership: CooperativeMembership? = null,
        val accountSecurity: AccountSecurityUiState = AccountSecurityUiState(),
    ) : AppUiState
}

/** True only for states reached after the backend has established a session. */
fun AppUiState.hasAuthenticatedSession(): Boolean = when (this) {
    is AppUiState.PassengerReady,
    is AppUiState.DriverReady,
    is AppUiState.DriverApplicationRequired,
    is AppUiState.DriverApplicationPending,
    is AppUiState.DriverOnboarding -> true
    is AppUiState.RestoringSession,
    is AppUiState.RegisteringAccount,
    is AppUiState.RecoveringAccount,
    is AppUiState.UpgradeRequired,
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
    "VERIFIED" -> Res.string.verification_verified
    "APPROVED" -> Res.string.verification_verified
    "REJECTED" -> Res.string.verification_rejected
    "ADDITIONAL_INFORMATION_REQUIRED" -> Res.string.verification_more_information
    "WITHDRAWN" -> Res.string.application_status_withdrawn
    "SUSPENDED" -> Res.string.application_status_suspended
    "EXPIRED" -> Res.string.application_status_expired
    else -> Res.string.verification_unknown
}

fun driverApplicationStatusResource(status: String): StringResource = when (status) {
    "APPROVED" -> Res.string.application_status_approved
    else -> driverVerificationStatusResource(status)
}

fun driverAccountStatusResource(status: String): StringResource = when (status) {
    "PENDING" -> Res.string.account_status_pending
    "ACTIVE" -> Res.string.account_status_active
    "SUSPENDED" -> Res.string.account_status_suspended
    "DEACTIVATED" -> Res.string.account_status_deactivated
    else -> Res.string.account_status_unknown
}
