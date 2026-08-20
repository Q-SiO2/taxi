package org.example.taximobile.feature.app

import org.example.taximobile.app.AppRole
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.AccountRole
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverAvailability
import org.example.taximobile.domain.drivers.DriverGateway
import org.example.taximobile.domain.drivers.DriverOfferGateway
import org.example.taximobile.domain.drivers.DriverRideAction
import org.example.taximobile.domain.drivers.DriverRideGateway
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideGateway
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.drivers.VehicleRegistration
import kotlin.time.Clock
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.domain.support.SupportGateway
import org.example.taximobile.domain.realtime.LiveEventGateway
import org.example.taximobile.domain.notifications.NotificationGateway
import org.example.taximobile.domain.notifications.DevicePlatform
import org.example.taximobile.domain.passengers.PassengerProfileGateway
import org.example.taximobile.domain.routing.RoutingGateway
import org.example.taximobile.domain.cooperatives.CooperativeGateway
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import org.example.taximobile.feature.auth.AuthenticationState
import org.example.taximobile.feature.ui.text.UiMessage
import org.jetbrains.compose.resources.StringResource
import taximobile.shared.generated.resources.*

/**
 * Converts restored, backend-validated authentication state into render state.
 * It intentionally does not infer driver eligibility or availability; those
 * values will be refreshed from the driver API before driver controls exist.
 */
class MobileAppCoordinator(
    private val appRole: AppRole,
    private val authentication: AuthenticationSessionCoordinator,
    private val driver: DriverGateway? = null,
    private val driverOffers: DriverOfferGateway? = null,
    private val driverRides: DriverRideGateway? = null,
    private val rides: RideGateway? = null,
    private val passengerProfile: PassengerProfileGateway? = null,
    private val support: SupportGateway? = null,
    private val notifications: NotificationGateway? = null,
    private val liveEvents: LiveEventGateway? = null,
    private val routing: RoutingGateway? = null,
    private val cooperatives: CooperativeGateway? = null,
) {
    // Retain only the latest coordinate that the backend accepted during this
    // foreground app process. This is navigation presentation state, not a
    // location history or an alternative source of dispatch truth.
    private var latestAcceptedDriverLocation: Coordinates? = null
    private val pushRegistrationMutex = Mutex()
    private var registeredPushRegistration: Pair<String, DevicePlatform>? = null

    suspend fun restore(): AppUiState = authenticatedProductState(authentication.restore())

    /** Local credential removal succeeds even when the backend cannot be reached. */
    suspend fun logout(): AppUiState {
        latestAcceptedDriverLocation = null
        revokeRegisteredPushRegistration()
        return stateFor(authentication.logout())
    }

    suspend fun login(identifier: String, password: String, deviceLabel: String?): AppUiState {
        // A coordinator may outlive one signed-in account. Never carry a
        // previous driver's coordinate into a new authentication attempt.
        latestAcceptedDriverLocation = null
        return authenticatedProductState(authentication.login(identifier, password, deviceLabel))
    }

    suspend fun register(
        displayName: String,
        email: String?,
        phoneNumber: String?,
        password: String,
    ): AppUiState {
        val result = authentication.register(displayName, email, phoneNumber, password)
        return if (result == AuthenticationState.Unauthenticated) {
            AppUiState.SignedOut(
                message = message(Res.string.message_account_created),
                registrationCompleted = true,
                suggestedIdentifier = email?.trim()?.takeIf { it.isNotEmpty() }
                    ?: phoneNumber?.trim()?.takeIf { it.isNotEmpty() },
            )
        } else if (result is AuthenticationState.Failure) {
            // Keep registration failures on the account form. A transport
            // failure must not discard the user's non-secret form input.
            AppUiState.SignedOut(
                message = result.message,
                showRegistrationForm = true,
            )
        } else {
            stateFor(result)
        }
    }

    fun stateFor(state: AuthenticationState): AppUiState = when (state) {
        AuthenticationState.Restoring -> AppUiState.RestoringSession
        AuthenticationState.Unauthenticated -> AppUiState.SignedOut()
        AuthenticationState.Authenticating -> AppUiState.RestoringSession
        is AuthenticationState.Failure -> if (
            state.message.resource == Res.string.message_network_unavailable
        ) {
            AppUiState.Offline(state.message)
        } else {
            AppUiState.SignedOut(state.message)
        }
        is AuthenticationState.Refreshing -> authenticatedState(state.account)
        is AuthenticationState.Authenticated -> authenticatedState(state.account)
    }

    private fun authenticatedState(account: CurrentAccount): AppUiState = when (appRole) {
        AppRole.PASSENGER -> {
            if (AccountRole.PASSENGER in account.roles) AppUiState.PassengerReady()
            else signedOut(Res.string.message_passenger_not_enabled)
        }

        AppRole.DRIVER -> {
            if (AccountRole.DRIVER in account.roles) AppUiState.DriverReady(DriverAvailabilityStatus.OFFLINE)
            else AppUiState.DriverApplicationRequired(account.displayName)
        }
    }

    suspend fun applyToDrive(displayName: String): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            gateway.apply(displayName).let { AppUiState.DriverApplicationPending(it.verificationStatus) }
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_driver_application_failed)
        }
    }

    suspend fun submitDriverVerification(): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            AppUiState.DriverApplicationPending(gateway.submitVerification())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_verification_failed)
        }
    }

    suspend fun changeDriverAvailability(online: Boolean): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            driverReadyWithOffers(if (online) gateway.goOnline() else gateway.goOffline())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_availability_failed)
        }
    }

    suspend fun updateDriverLocation(location: Coordinates): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            gateway.updateLocation(location, Clock.System.now().toString())
            latestAcceptedDriverLocation = location
            refreshDriverState()
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_location_update_failed)
        }
    }

    suspend fun registerDriverVehicle(vehicle: VehicleRegistration): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            gateway.registerVehicle(vehicle)
            refreshDriverState()
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_vehicle_registration_failed)
        }
    }

    suspend fun selectDriverVehicle(vehicleId: String): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            driverReadyWithOffers(gateway.selectActiveVehicle(vehicleId))
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_vehicle_selection_failed)
        }
    }

    suspend fun deactivateDriverVehicle(vehicleId: String): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            gateway.deactivateVehicle(vehicleId)
            refreshDriverState()
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_vehicle_deactivation_failed)
        }
    }

    suspend fun respondToOffer(offerId: String, accept: Boolean): AppUiState {
        val gateway = driverOffers ?: return offline(Res.string.message_ride_offer_services_unavailable)
        return try {
            if (accept) gateway.accept(offerId) else gateway.decline(offerId, "DRIVER_DECLINED")
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_offer_update_failed)
        }
    }

    suspend fun advanceDriverRide(rideId: String, action: DriverRideAction): AppUiState {
        val gateway = driverRides ?: return offline(Res.string.message_driver_ride_services_unavailable)
        return try {
            when (action) {
                DriverRideAction.EN_ROUTE -> gateway.markEnRoute(rideId)
                DriverRideAction.ARRIVED -> gateway.markArrived(rideId)
                DriverRideAction.START -> gateway.start(rideId)
            }
            refreshDriverState()
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_update_failed)
        }
    }

    suspend fun cancelDriverRide(rideId: String, reason: String): AppUiState {
        val gateway = driverRides ?: return offline(Res.string.message_driver_ride_services_unavailable)
        return try {
            gateway.cancel(rideId, reason.trim())
            refreshDriverState()
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_cancel_failed)
        }
    }

    suspend fun completeDriverRide(rideId: String, location: Coordinates): AppUiState {
        val gateway = driverRides ?: return offline(Res.string.message_driver_ride_services_unavailable)
        return try {
            gateway.complete(rideId, location)
            (refreshDriverState() as? AppUiState.DriverReady)?.copy(pendingCashRideId = rideId)
                ?: offline(Res.string.message_driver_refresh_after_completion_failed)
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_completion_failed)
        }
    }

    suspend fun settleDriverCash(rideId: String): AppUiState {
        val gateway = driverRides ?: return offline(Res.string.message_driver_ride_services_unavailable)
        return try {
            gateway.settleCash(rideId)
            refreshDriverState()
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_cash_settlement_failed)
        }
    }

    suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            val estimate = gateway.estimateRide(pickup, destination)
            val routePlan = try {
                routing?.route(pickup, destination)
            } catch (_: AuthenticationNetworkException) {
                null
            } catch (_: ApiRequestException) {
                null
            }
            val refreshed = authenticatedProductState(authentication.restore())
            if (refreshed is AppUiState.PassengerReady) {
                refreshed.copy(
                    fareEstimate = estimate,
                    routePlan = routePlan,
                    routeUnavailable = routing != null && routePlan == null,
                )
            } else {
                refreshed
            }
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_estimate_failed)
        }
    }

    suspend fun requestRide(pickup: Coordinates, destination: Coordinates): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            gateway.requestRide(pickup, destination)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_request_failed)
        }
    }

    suspend fun cancelRide(rideId: String): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            gateway.cancelRide(rideId, "PASSENGER_CANCELLED")
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_cancel_failed)
        }
    }

    suspend fun loadPassengerRideHistoryDetail(rideId: String): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            // Reload the collection and account state first, then authorize the
            // selected resource independently through its detail endpoint.
            val refreshed = authenticatedProductState(authentication.restore())
            if (refreshed !is AppUiState.PassengerReady) return refreshed
            val detail = gateway.currentRide(rideId)
            val receipt = if (detail.status == RideStatus.COMPLETED) gateway.receipt(rideId) else null
            refreshed.copy(selectedHistoryRide = detail, selectedHistoryReceipt = receipt)
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_history_detail_failed)
        }
    }

    suspend fun loadDriverRideHistoryDetail(rideId: String): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            // Refresh owner-scoped driver collections first. The detail and
            // feedback endpoints still independently authorize this ride.
            val refreshed = authenticatedProductState(authentication.restore())
            if (refreshed !is AppUiState.DriverReady) return refreshed
            val detail = gateway.currentRide(rideId)
            val rating = if (detail.status == RideStatus.COMPLETED) {
                gateway.ratings(rideId).firstOrNull()
            } else {
                null
            }
            refreshed.copy(selectedHistoryRide = detail, selectedHistoryRating = rating)
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_history_detail_failed)
        }
    }

    suspend fun submitRideRating(rideId: String, score: Int, comment: String?): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            gateway.submitRating(rideId, score, comment?.trim()?.ifBlank { null })
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_rating_failed)
        }
    }

    suspend fun updatePassengerProfile(displayName: String): AppUiState {
        val gateway = passengerProfile ?: return offline(Res.string.message_passenger_profile_services_unavailable)
        return try {
            gateway.updateDisplayName(displayName)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_profile_update_failed)
        }
    }

    suspend fun createSupportTicket(
        category: SupportCategory,
        subject: String,
        description: String,
        rideId: String? = null,
    ): AppUiState {
        val gateway = support ?: return offline(Res.string.message_support_services_unavailable)
        return try {
            gateway.createTicket(category, subject.trim(), description.trim(), rideId)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_support_creation_failed)
        }
    }

    suspend fun markNotificationRead(notificationId: String): AppUiState {
        val gateway = notifications ?: return offline(Res.string.message_notification_services_unavailable)
        return try {
            gateway.markRead(notificationId)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_notification_update_failed)
        }
    }

    /** A Firebase installation ID is delivery metadata, never authenticated UI state. */
    suspend fun registerPushRegistration(registrationId: String, platform: DevicePlatform): Boolean {
        if (registrationId.isBlank()) return false
        val gateway = notifications ?: return false
        return pushRegistrationMutex.withLock {
            try {
                gateway.registerDevice(registrationId, platform)
                registeredPushRegistration = registrationId to platform
                true
            } catch (_: AuthenticationRejectedException) {
                // The platform relay retains the token in memory and retries after authentication.
                false
            } catch (_: AuthenticationNetworkException) {
                // FCM and notification history are best-effort, never business truth.
                false
            } catch (_: ApiRequestException) {
                // A later app start/token callback retries with current backend policy.
                false
            }
        }
    }

    private suspend fun revokeRegisteredPushRegistration() {
        pushRegistrationMutex.withLock {
            val registration = registeredPushRegistration ?: return@withLock
            try {
                notifications?.unregisterDevice(registration.first, registration.second)
            } catch (_: AuthenticationRejectedException) {
                // Session revocation still proceeds and local credentials are removed.
            } catch (_: AuthenticationNetworkException) {
                // Offline logout is local-first; the backend token expires or is transferred later.
            } catch (_: ApiRequestException) {
                // Push metadata cannot prevent logout.
            } finally {
                registeredPushRegistration = null
            }
        }
    }

    /** Starts a best-effort listener; state is refreshed only after a server hint. */
    suspend fun listenForLiveUpdates(onRefresh: suspend () -> Unit) {
        try {
            liveEvents?.listen { onRefresh() }
        } catch (_: AuthenticationRejectedException) {
            // A normal foreground restore will replace/revoke credentials as needed.
        } catch (_: AuthenticationNetworkException) {
            // WebSocket delivery is not authoritative and must not overwrite UI state.
        }
    }

    private suspend fun authenticatedProductState(state: AuthenticationState): AppUiState {
        val rendered = stateFor(state)
        if (appRole == AppRole.DRIVER && rendered is AppUiState.DriverApplicationRequired && driver != null) {
            return try {
                AppUiState.DriverApplicationPending(driver.verificationStatus())
            } catch (_: AuthenticationRejectedException) {
                signedOut(Res.string.message_session_expired)
            } catch (_: AuthenticationNetworkException) {
                offline(Res.string.message_network_unavailable)
            } catch (error: ApiRequestException) {
                // A 404 is the normal no-application case; other failures must
                // remain visible rather than pretending a new application is safe.
                if (error.statusCode == 404) rendered
                else offline(Res.string.message_verification_load_failed)
            }
        }
        if (appRole == AppRole.PASSENGER && rendered is AppUiState.PassengerReady && rides != null) {
            return try {
                val passengerRides = rides.listRides()
                val profile = passengerProfile?.profile()
                val notificationHistory = notifications?.list() ?: emptyList()
                val supportHistory = support?.tickets() ?: emptyList()
                passengerRides
                    .firstOrNull {
                        it.status !in setOf(RideStatus.COMPLETED, RideStatus.CANCELLED, RideStatus.UNMATCHED)
                    }
                    ?.let { activeSummary ->
                        val activeRide = rides.currentRide(activeSummary.id)
                        val routePlan = try {
                            val pickup = activeRide.pickup
                            val destination = activeRide.destination
                            if (pickup != null && destination != null) routing?.route(pickup, destination) else null
                        } catch (_: AuthenticationNetworkException) {
                            null
                        } catch (_: ApiRequestException) {
                            null
                        }
                        AppUiState.PassengerReady(
                            profile = profile,
                            activeRideId = activeRide.id,
                            activeRide = activeRide.status,
                            assignedDriver = activeRide.driver,
                            lastKnownDriverLocation = activeRide.lastKnownDriverLocation,
                            pickup = activeRide.pickup,
                            destination = activeRide.destination,
                            routePlan = routePlan,
                            routeUnavailable = routing != null &&
                                activeRide.pickup != null && activeRide.destination != null && routePlan == null,
                            rideHistory = passengerRides,
                            notifications = notificationHistory,
                            supportTickets = supportHistory,
                        )
                    }
                    ?: passengerRides.firstOrNull { it.status == RideStatus.COMPLETED }
                        ?.let { completedRide ->
                            val ratingExists = rides.ratings(completedRide.id).isNotEmpty()
                            val receipt = rides.receipt(completedRide.id)
                            AppUiState.PassengerReady(
                                profile = profile,
                                rateableRideId = completedRide.id.takeUnless { ratingExists },
                                rideHistory = passengerRides,
                                latestCompletedReceipt = receipt,
                                notifications = notificationHistory,
                                supportTickets = supportHistory,
                            )
                        }
                    ?: AppUiState.PassengerReady(
                        profile = profile,
                        rideHistory = passengerRides,
                        notifications = notificationHistory,
                        supportTickets = supportHistory,
                    )
            } catch (_: AuthenticationRejectedException) {
                signedOut(Res.string.message_session_expired)
            } catch (_: AuthenticationNetworkException) {
                offline(Res.string.message_network_unavailable)
            } catch (_: ApiRequestException) {
                offline(Res.string.message_current_rides_load_failed)
            }
        }
        if (appRole != AppRole.DRIVER || rendered !is AppUiState.DriverReady || driver == null) return rendered
        return try {
            refreshDriverState()
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_availability_load_failed)
        }
    }

    private suspend fun driverReadyWithOffers(availability: DriverAvailability): AppUiState {
        val profile = driver?.profile()
        val offers = driverOffers?.currentOffers() ?: emptyList()
        val rideHistory = driverRides?.rides() ?: emptyList()
        val credentials = driver?.credentials() ?: emptyList()
        val vehicles = driver?.vehicles() ?: emptyList()
        val activeRide = rideHistory.firstOrNull {
            it.status !in setOf(RideStatus.COMPLETED, RideStatus.CANCELLED, RideStatus.UNMATCHED)
        }
        val activeRideDetail = activeRide?.let { rides?.currentRide(it.id) }
        val guidanceDestination = when (activeRide?.status) {
            RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE -> activeRideDetail?.pickup
            RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS -> activeRideDetail?.destination
            else -> null
        }
        val guidanceOrigin = latestAcceptedDriverLocation
        val routePlan = try {
            if (guidanceOrigin != null && guidanceDestination != null) {
                routing?.route(guidanceOrigin, guidanceDestination)
            } else {
                null
            }
        } catch (_: AuthenticationNetworkException) {
            null
        } catch (_: ApiRequestException) {
            null
        }
        val earnings = driverRides?.earnings()
        val notificationHistory = notifications?.list() ?: emptyList()
        val supportHistory = support?.tickets() ?: emptyList()
        val cooperativeMembership = cooperatives?.currentMembership()
        return AppUiState.DriverReady(
            availability = availability.status,
            displayName = profile?.displayName,
            verificationStatus = profile?.verificationStatus,
            accountStatus = profile?.accountStatus,
            activeVehicleId = availability.activeVehicleId,
            credentials = credentials,
            vehicles = vehicles,
            activeRideId = activeRide?.id,
            activeRide = activeRide?.status,
            currentLocation = guidanceOrigin,
            pickup = activeRideDetail?.pickup,
            destination = activeRideDetail?.destination,
            routePlan = routePlan,
            routeUnavailable = routing != null && guidanceOrigin != null && guidanceDestination != null && routePlan == null,
            offers = offers,
            earnings = earnings,
            rideHistory = rideHistory,
            notifications = notificationHistory,
            supportTickets = supportHistory,
            cooperativeMembership = cooperativeMembership,
        )
    }

    private suspend fun refreshDriverState(): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return driverReadyWithOffers(gateway.currentAvailability())
    }
}

private fun message(resource: StringResource): UiMessage = UiMessage(resource)

private fun offline(resource: StringResource): AppUiState.Offline =
    AppUiState.Offline(message(resource))

private fun signedOut(resource: StringResource): AppUiState.SignedOut =
    AppUiState.SignedOut(message(resource))
