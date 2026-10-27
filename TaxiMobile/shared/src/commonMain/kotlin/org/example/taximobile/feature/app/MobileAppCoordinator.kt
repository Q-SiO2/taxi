package org.example.taximobile.feature.app

import org.example.taximobile.domain.scheduling.canReviewAcceptance
import org.example.taximobile.domain.scheduling.scheduledCityTime
import org.example.taximobile.domain.scheduling.matchesPointRequest
import org.example.taximobile.domain.scheduling.matchesFixedRouteRequest
import org.example.taximobile.domain.scheduling.matchesRequest
import org.example.taximobile.domain.scheduling.isScheduledLocalClockInput

import org.example.taximobile.app.AppRole
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.AccountSecurityGateway
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.AccountRole
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverAvailability
import org.example.taximobile.domain.drivers.DriverGateway
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import org.example.taximobile.domain.drivers.DriverCityApplication
import org.example.taximobile.domain.drivers.DriverDocumentUpload
import org.example.taximobile.domain.drivers.DriverAuthorizedMarket
import org.example.taximobile.domain.drivers.DriverRecruitmentGateway
import org.example.taximobile.domain.drivers.DriverOfferGateway
import org.example.taximobile.domain.drivers.DriverRideAction
import org.example.taximobile.domain.drivers.DriverRideGateway
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.RideGateway
import org.example.taximobile.domain.rides.RidePaymentMethod
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.scheduling.ScheduledBookingGateway
import org.example.taximobile.domain.scheduling.ScheduledBookingEstimate
import org.example.taximobile.domain.drivers.VehicleRegistration
import kotlin.time.Clock
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.sync.withLock
import org.example.taximobile.domain.support.SupportCategory
import org.example.taximobile.domain.support.SupportGateway
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.safety.SafetyGateway
import org.example.taximobile.domain.realtime.LiveEventGateway
import org.example.taximobile.domain.notifications.NotificationGateway
import org.example.taximobile.domain.notifications.DevicePlatform
import org.example.taximobile.domain.passengers.PassengerProfileGateway
import org.example.taximobile.domain.places.PlaceDiscoveryGateway
import org.example.taximobile.domain.routing.RoutingGateway
import org.example.taximobile.domain.cooperatives.CooperativeGateway
import org.example.taximobile.domain.system.ClientCompatibilityGateway
import org.example.taximobile.domain.system.ClientCompatibilityStatus
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import org.example.taximobile.feature.auth.AuthenticationState
import org.example.taximobile.feature.realtime.LiveUpdateSubscription
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
    private val accountSecurity: AccountSecurityGateway? = null,
    private val driver: DriverGateway? = null,
    private val driverRecruitment: DriverRecruitmentGateway? = null,
    private val driverOffers: DriverOfferGateway? = null,
    private val driverRides: DriverRideGateway? = null,
    private val rides: RideGateway? = null,
    private val scheduling: ScheduledBookingGateway? = null,
    private val passengerProfile: PassengerProfileGateway? = null,
    private val support: SupportGateway? = null,
    private val safety: SafetyGateway? = null,
    private val notifications: NotificationGateway? = null,
    private val liveEvents: LiveEventGateway? = null,
    private val routing: RoutingGateway? = null,
    private val places: PlaceDiscoveryGateway? = null,
    private val cooperatives: CooperativeGateway? = null,
    private val clientCompatibility: ClientCompatibilityGateway? = null,
) {
    // Retain only the latest coordinate that the backend accepted during this
    // foreground app process. This is navigation presentation state, not a
    // location history or an alternative source of dispatch truth.
    private var latestAcceptedDriverLocation: Coordinates? = null
    // Navigation preference only. Every page is read afresh from the server;
    // this never retains a payment, amount or settlement authority.
    private var selectedPendingCashPage: Int = 1
    private data class BookingPageSelection(val page: Int, val owner: Long)
    private var selectedBookingPage: BookingPageSelection? = null
    private var bookingPageReadRevision: Long = 0
    private var scheduledClockReadRevision: Long = 0
    private var selectedFixedRouteCityId: String? = null
    // Session-owned navigation only. Every refresh reauthorizes and rereads
    // the selected ride and receipt/feedback; no financial projection is cached.
    private data class HistorySelection(
        val rideId: String,
        val owner: Long,
        val primaryRideId: String?,
    )
    private var historySelection: HistorySelection? = null
    private sealed interface RideQuoteInput {
        data class Point(val pickup: Coordinates, val destination: Coordinates) : RideQuoteInput
        data class Fixed(val directionId: String) : RideQuoteInput
    }
    private data class RideQuoteSelection(
        val input: RideQuoteInput,
        val owner: Long,
        val primaryRideId: String?,
    )
    // Inputs only: catch-up fetches current server terms, never caches a price
    // or replays the consequential create-ride command.
    private var rideQuoteSelection: RideQuoteSelection? = null
    private var placeDiscoveryRevision: Long = 0
    private val pushRegistrationMutex = Mutex()
    private var registeredPushRegistration: Pair<String, DevicePlatform>? = null
    val liveSessionLifetime get() = authentication.liveSessionLifetime
    private val liveSubscription = liveEvents?.let { LiveUpdateSubscription(it, liveSessionLifetime) }

    suspend fun restore(): AppUiState {
        val compatibility = clientCompatibility ?: return authenticatedProductState(
            authentication.restore()
        )
        return try {
            val result = compatibility.check()
            if (result.status == ClientCompatibilityStatus.UPGRADE_REQUIRED) {
                AppUiState.UpgradeRequired(
                    minimumVersion = result.minimumVersion,
                    policyRevision = result.policyRevision,
                )
            } else {
                authenticatedProductState(authentication.restore())
            }
        } catch (_: AuthenticationNetworkException) {
            AppUiState.Offline(message(Res.string.message_network_unavailable))
        } catch (_: ApiRequestException) {
            AppUiState.Offline(message(Res.string.message_client_compatibility_failed))
        }
    }

    /** Local credential removal succeeds even when the backend cannot be reached. */
    suspend fun logout(): AppUiState {
        authentication.beginSessionEnd()
        historySelection = null
        rideQuoteSelection = null
        latestAcceptedDriverLocation = null
        selectedPendingCashPage = 1
        selectedBookingPage = null
        bookingPageReadRevision++
        revokeRegisteredPushRegistration()
        return stateFor(authentication.logout())
    }

    suspend fun login(identifier: String, password: String, deviceLabel: String?): AppUiState {
        // A coordinator may outlive one signed-in account. Never carry a
        // previous driver's coordinate into a new authentication attempt.
        latestAcceptedDriverLocation = null
        selectedPendingCashPage = 1
        selectedBookingPage = null
        bookingPageReadRevision++
        historySelection = null
        rideQuoteSelection = null
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

    /**
     * Public recovery is intentionally enumeration-safe: a reachable backend
     * always returns the same confirmation, whether or not the reset occurred.
     */
    suspend fun recoverAccount(
        identifier: String,
        recoveryCode: String,
        newPassword: String,
    ): AppUiState {
        val gateway = accountSecurity
            ?: return signedOut(Res.string.message_account_recovery_unavailable)
        return try {
            gateway.resetPassword(identifier, recoveryCode, newPassword)
            AppUiState.SignedOut(
                message = message(Res.string.message_account_recovery_accepted),
                recoveryCompleted = true,
            )
        } catch (_: AuthenticationNetworkException) {
            AppUiState.SignedOut(
                message = message(Res.string.message_network_unavailable),
                showRecoveryForm = true,
            )
        } catch (_: ApiRequestException) {
            AppUiState.SignedOut(
                message = message(Res.string.message_account_recovery_failed),
                showRecoveryForm = true,
            )
        }
    }

    suspend fun loadAccountSecurity(): AppUiState {
        val gateway = accountSecurity
            ?: return accountSecurityFailure(Res.string.message_account_security_unavailable)
        return try {
            accountSecurityState(
                AccountSecurityUiState(loaded = true, sessions = gateway.sessions()),
            )
        } catch (_: AuthenticationRejectedException) {
            authentication.clearLocalSession()
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            accountSecurityFailure(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            accountSecurityFailure(Res.string.message_account_security_load_failed)
        }
    }

    suspend fun createRecoveryCodes(currentPassword: String): AppUiState {
        val gateway = accountSecurity
            ?: return accountSecurityFailure(Res.string.message_account_security_unavailable)
        return try {
            val recoveryCodes = gateway.recoveryCodes(currentPassword)
            accountSecurityState(
                AccountSecurityUiState(
                    loaded = true,
                    sessions = gateway.sessions(),
                    recoveryCodes = recoveryCodes,
                    message = message(Res.string.message_recovery_codes_created),
                ),
            )
        } catch (_: AuthenticationRejectedException) {
            authentication.clearLocalSession()
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            accountSecurityFailure(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            accountSecurityFailure(Res.string.message_recovery_codes_failed)
        }
    }

    suspend fun revokeAccountSession(sessionId: String): AppUiState {
        val gateway = accountSecurity
            ?: return accountSecurityFailure(Res.string.message_account_security_unavailable)
        return try {
            val result = gateway.revokeSession(sessionId)
            if (result.currentSession) {
                authentication.clearLocalSession()
                signedOut(Res.string.message_current_session_revoked)
            } else {
                accountSecurityState(
                    AccountSecurityUiState(
                        loaded = true,
                        sessions = gateway.sessions(),
                        message = message(Res.string.message_session_revoked),
                    ),
                )
            }
        } catch (_: AuthenticationRejectedException) {
            authentication.clearLocalSession()
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            accountSecurityFailure(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            accountSecurityFailure(Res.string.message_session_revoke_failed)
        }
    }

    suspend fun changeAccountPassword(currentPassword: String, newPassword: String): AppUiState {
        val gateway = accountSecurity
            ?: return accountSecurityFailure(Res.string.message_account_security_unavailable)
        return try {
            gateway.changePassword(currentPassword, newPassword)
            authentication.clearLocalSession()
            AppUiState.SignedOut(
                message = message(Res.string.message_password_changed),
                recoveryCompleted = true,
            )
        } catch (_: AuthenticationRejectedException) {
            authentication.clearLocalSession()
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            accountSecurityFailure(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            accountSecurityFailure(Res.string.message_password_change_failed)
        }
    }

    private suspend fun accountSecurityState(security: AccountSecurityUiState): AppUiState =
        authenticatedProductState(authentication.restore()).withAccountSecurity(security)

    private suspend fun accountSecurityFailure(resource: StringResource): AppUiState =
        authenticatedProductState(authentication.restore()).withAccountSecurity(
            // Mark this attempt complete so Compose does not immediately launch
            // the same failed request again. Reopening the account panel or an
            // explicit later action performs a fresh backend read.
            AccountSecurityUiState(loaded = true, message = message(resource)),
        )

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

    suspend fun createDriverCityApplication(cityId: String, displayName: String): AppUiState =
        recruitmentMutation(displayName) { gateway ->
            gateway.createApplication(cityId, displayName)
        }

    suspend fun uploadDriverCityApplicationDocument(
        applicationId: String,
        requirementItemId: String,
        expectedVersion: Int,
        displayName: String,
        document: DriverDocumentUpload,
    ): AppUiState = recruitmentMutation(displayName) { gateway ->
        gateway.uploadDocument(
            applicationId = applicationId,
            requirementItemId = requirementItemId,
            expectedVersion = expectedVersion,
            document = document,
        )
    }

    suspend fun deleteDriverCityApplicationDocument(
        applicationId: String,
        documentId: String,
        expectedVersion: Int,
        displayName: String,
    ): AppUiState = recruitmentMutation(displayName) { gateway ->
        gateway.deleteDocument(applicationId, documentId, expectedVersion)
    }

    suspend fun selectDriverCityApplication(
        applicationId: String,
        displayName: String,
    ): AppUiState {
        val gateway = driverRecruitment
            ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            driverOnboardingState(
                displayName = displayName,
                selectedApplication = gateway.application(applicationId),
            )
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            restoreDriverOnboardingAfterFailure(
                displayName,
                Res.string.message_driver_recruitment_failed,
            )
        }
    }

    suspend fun saveDriverCityApplication(
        applicationId: String,
        expectedVersion: Int,
        displayName: String,
        answers: List<DriverApplicationAnswerDraft>,
        evidence: List<DriverApplicationEvidenceDraft>,
        removeAnswerItemIds: List<String> = emptyList(),
        removeEvidenceItemIds: List<String> = emptyList(),
    ): AppUiState = recruitmentMutation(displayName) { gateway ->
        gateway.updateApplication(
            applicationId = applicationId,
            expectedVersion = expectedVersion,
            answers = answers,
            evidence = evidence,
            removeAnswerItemIds = removeAnswerItemIds,
            removeEvidenceItemIds = removeEvidenceItemIds,
        )
    }

    suspend fun submitDriverCityApplication(
        applicationId: String,
        displayName: String,
    ): AppUiState = recruitmentMutation(displayName) { gateway ->
        gateway.submitApplication(applicationId)
    }

    suspend fun withdrawDriverCityApplication(
        applicationId: String,
        displayName: String,
    ): AppUiState = recruitmentMutation(displayName) { gateway ->
        gateway.withdrawApplication(applicationId)
    }

    suspend fun registerApplicantVehicle(
        displayName: String,
        vehicle: VehicleRegistration,
    ): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            gateway.registerVehicle(vehicle)
            driverOnboardingState(displayName)
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            restoreDriverOnboardingAfterFailure(
                displayName,
                Res.string.message_vehicle_registration_failed,
            )
        }
    }

    private suspend fun recruitmentMutation(
        displayName: String,
        mutation: suspend (DriverRecruitmentGateway) -> DriverCityApplication,
    ): AppUiState {
        val gateway = driverRecruitment
            ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            val application = mutation(gateway)
            driverOnboardingState(displayName, selectedApplication = application)
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            restoreDriverOnboardingAfterFailure(
                displayName,
                Res.string.message_driver_recruitment_failed,
            )
        }
    }

    private suspend fun restoreDriverOnboardingAfterFailure(
        displayName: String,
        failureMessage: StringResource,
    ): AppUiState = try {
        driverOnboardingState(displayName, message = message(failureMessage))
    } catch (_: AuthenticationRejectedException) {
        signedOut(Res.string.message_session_expired)
    } catch (_: AuthenticationNetworkException) {
        offline(Res.string.message_network_unavailable)
    } catch (_: ApiRequestException) {
        AppUiState.DriverOnboarding(
            displayName = displayName,
            recruitingCities = emptyList(),
            applications = emptyList(),
            message = message(failureMessage),
        )
    }

    private suspend fun driverOnboardingState(
        displayName: String,
        selectedApplication: DriverCityApplication? = null,
        message: UiMessage? = null,
    ): AppUiState.DriverOnboarding {
        val recruitment = requireNotNull(driverRecruitment)
        val cities = recruitment.recruitingCities()
        val applications = recruitment.applications()
        val selected = selectedApplication ?: applications.firstOrNull()?.let {
            recruitment.application(it.id)
        }
        val vehicles = if (applications.isEmpty()) emptyList() else driver?.vehicles().orEmpty()
        val credentials = if (applications.isEmpty()) emptyList() else driver?.credentials().orEmpty()
        return AppUiState.DriverOnboarding(
            displayName = displayName,
            recruitingCities = cities,
            applications = applications,
            selectedApplication = selected,
            vehicles = vehicles,
            credentials = credentials,
            message = message,
        )
    }

    suspend fun changeDriverAvailability(
        online: Boolean,
        cityId: String? = null,
        serviceType: String = "ON_DEMAND",
    ): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            driverReadyWithOffers(
                if (online) gateway.goOnline(cityId = cityId, serviceType = serviceType)
                else gateway.goOffline(),
            )
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (error: ApiRequestException) {
            offline(if (error.reason == org.example.taximobile.data.network.ApiFailureReason.OPERATOR_MEMBERSHIP_REQUIRED)
                Res.string.message_membership_required else Res.string.message_availability_failed)
        }
    }

    suspend fun updateDriverLocation(
        observation: org.example.taximobile.domain.drivers.DriverLocationObservation,
        currentDriverState: (() -> AppUiState.DriverReady?)? = null,
    ): AppUiState {
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        if (!observation.isUsableAt(Clock.System.now().toEpochMilliseconds())) {
            return offline(Res.string.message_location_update_failed)
        }
        val owner = liveSessionLifetime.value
        return try {
            gateway.updateLocation(observation.coordinates, observation.observedAtIso, observation.accuracyMeters)
            // A location acknowledgement changes only this fact. Do not reload
            // every dashboard resource while holding the native command gate.
            // Read the latest projection after IO, so concurrent hints are kept.
            if (owner != liveSessionLifetime.value) return signedOut(Res.string.message_session_expired)
            latestAcceptedDriverLocation = observation.coordinates
            currentDriverState?.invoke()?.let { rendered ->
                val destination = when (rendered.activeRide) {
                    RideStatus.ACCEPTED, RideStatus.DRIVER_EN_ROUTE -> rendered.pickup
                    RideStatus.DRIVER_ARRIVED, RideStatus.IN_PROGRESS -> rendered.destination
                    else -> null
                }
                val route = try {
                    destination?.let { routing?.route(observation.coordinates, it) }
                } catch (_: AuthenticationNetworkException) {
                    null
                } catch (_: ApiRequestException) {
                    null
                }
                if (owner != liveSessionLifetime.value) return signedOut(Res.string.message_session_expired)
                currentDriverState.invoke()?.let { latest ->
                    val sameTripPhase = latest.activeRideId == rendered.activeRideId && latest.activeRide == rendered.activeRide
                    return latest.copy(
                        currentLocation = observation.coordinates,
                        routePlan = if (sameTripPhase) route else latest.routePlan,
                        routeUnavailable = if (sameTripPhase) routing != null && destination != null && route == null else latest.routeUnavailable,
                    )
                }
            }
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
        } catch (error: ApiRequestException) {
            offline(if (error.reason == org.example.taximobile.data.network.ApiFailureReason.OPERATOR_MEMBERSHIP_REQUIRED)
                Res.string.message_membership_required else Res.string.message_offer_update_failed)
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
            selectedPendingCashPage = 1
            (refreshDriverState() as? AppUiState.DriverReady)
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
            selectedPendingCashPage = 1
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
        rideQuoteSelection = null
        return try {
            authentication.readWithSessionRecovery { account ->
                val owner = authentication.localSessionOwnerEpoch
                val estimate = gateway.estimateRide(pickup, destination)
                val routePlan = try {
                    routing?.route(pickup, destination)
                } catch (_: AuthenticationNetworkException) {
                    null
                } catch (_: ApiRequestException) {
                    null
                }
                val refreshed = quoteProductState(account)
                if (!navigationOwnerIsCurrent(owner)) return@readWithSessionRecovery signedOut(Res.string.message_session_expired)
                if (refreshed is AppUiState.PassengerReady && refreshed.activeRide == null) {
                    rideQuoteSelection = RideQuoteSelection(
                        RideQuoteInput.Point(pickup, destination), owner, refreshed.rideHistory.firstOrNull()?.id,
                    )
                    refreshed.copy(
                        fareEstimate = estimate,
                        reviewedPointQuoteInput = pickup to destination,
                        routePlan = routePlan,
                        routeUnavailable = routing != null && routePlan == null,
                    )
                } else {
                    refreshed
                }
            }
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_estimate_failed)
        }
    }

    suspend fun searchPlaces(cityId: String, query: String): AppUiState {
        val gateway = places ?: return offline(Res.string.message_place_search_unavailable)
        return try {
            val result = gateway.search(cityId, query)
            val refreshed = authenticatedProductState(authentication.restore())
            if (refreshed is AppUiState.PassengerReady) {
                placeDiscoveryRevision += 1
                refreshed.copy(
                    placeDiscovery = PlaceDiscoveryUiState(
                        revision = placeDiscoveryRevision,
                        search = result,
                    ),
                )
            } else refreshed
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_place_search_unavailable)
        }
    }

    suspend fun reversePlace(cityId: String, coordinate: Coordinates): AppUiState {
        val gateway = places ?: return offline(Res.string.message_address_lookup_unavailable)
        return try {
            val result = gateway.reverse(cityId, coordinate)
            val refreshed = authenticatedProductState(authentication.restore())
            if (refreshed is AppUiState.PassengerReady) {
                placeDiscoveryRevision += 1
                refreshed.copy(
                    placeDiscovery = PlaceDiscoveryUiState(
                        revision = placeDiscoveryRevision,
                        reverse = result,
                    ),
                )
            } else refreshed
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_address_lookup_unavailable)
        }
    }

    suspend fun requestRide(pickup: Coordinates, destination: Coordinates): AppUiState =
        requestRide(pickup, destination, RidePaymentMethod.CASH)

    suspend fun requestRide(
        pickup: Coordinates,
        destination: Coordinates,
        paymentMethod: RidePaymentMethod,
    ): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            gateway.requestRide(pickup, destination, paymentMethod)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_request_failed)
        }
    }

    suspend fun loadFixedRoutes(cityId: String): AppUiState {
        selectedFixedRouteCityId = cityId
        return authenticatedProductState(authentication.restore())
    }

    suspend fun estimateFixedRoute(directionVersionId: String): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        rideQuoteSelection = null
        return try {
            authentication.readWithSessionRecovery { account ->
                val owner = authentication.localSessionOwnerEpoch
                val estimate = gateway.estimateFixedRoute(directionVersionId)
                val refreshed = quoteProductState(account)
                if (!navigationOwnerIsCurrent(owner)) return@readWithSessionRecovery signedOut(Res.string.message_session_expired)
                if (refreshed is AppUiState.PassengerReady && refreshed.activeRide == null) {
                    rideQuoteSelection = RideQuoteSelection(
                        RideQuoteInput.Fixed(directionVersionId), owner, refreshed.rideHistory.firstOrNull()?.id,
                    )
                    refreshed.copy(
                        fareEstimate = estimate,
                        selectedFixedRouteDirectionId = directionVersionId,
                    )
                } else refreshed
            }
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_estimate_failed)
        }
    }

    suspend fun requestFixedRoute(
        directionVersionId: String,
        paymentMethod: RidePaymentMethod,
    ): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            gateway.requestFixedRoute(directionVersionId, paymentMethod)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_request_failed)
        }
    }

    suspend fun schedulePointToPoint(
        scheduledFor: String,
        cityId: String?,
        pickup: Coordinates,
        destination: Coordinates,
        note: String?,
        estimate: ScheduledBookingEstimate,
    ): AppUiState {
        if (scheduledCityTime(estimate.scheduledFor, estimate.cityTimezone) == null) return offline(Res.string.scheduled_time_unavailable)
        if (!estimate.cancellationTerms.isSupportedForReview) return offline(Res.string.scheduled_refund_unavailable)
        if (!estimate.matchesPointRequest(scheduledFor, cityId, pickup, destination)) return offline(Res.string.scheduled_review_unavailable)
        return schedulingMutation {
            it.createPointToPoint(scheduledFor, cityId, pickup, destination, note, estimate.economics)
        }
    }

    suspend fun scheduleFixedRoute(
        scheduledFor: String,
        directionVersionId: String,
        note: String?,
        estimate: ScheduledBookingEstimate,
    ): AppUiState {
        if (scheduledCityTime(estimate.scheduledFor, estimate.cityTimezone) == null) return offline(Res.string.scheduled_time_unavailable)
        if (!estimate.cancellationTerms.isSupportedForReview) return offline(Res.string.scheduled_refund_unavailable)
        if (!estimate.matchesFixedRouteRequest(scheduledFor, directionVersionId)) return offline(Res.string.scheduled_review_unavailable)
        return schedulingMutation {
            it.createFixedRoute(scheduledFor, directionVersionId, note, estimate.economics)
        }
    }

    suspend fun resolveScheduledLocalTime(cityId: String, cityTimezone: String, localDate: String, localTime: String): AppUiState {
        val revision = ++scheduledClockReadRevision
        val gateway = scheduling ?: return offline(Res.string.message_ride_services_unavailable)
        if (appRole != AppRole.PASSENGER || cityId.isBlank() || !isScheduledLocalClockInput(localDate, localTime)) {
            return offline(Res.string.scheduled_clock_unavailable)
        }
        return try {
            authentication.readWithSessionRecovery { account ->
                val result = gateway.localTimeOptions(cityId, cityTimezone, localDate, localTime)
                if (revision != scheduledClockReadRevision || result == null ||
                    !result.matchesRequest(cityId, cityTimezone, localDate, localTime)) {
                    return@readWithSessionRecovery offline(Res.string.scheduled_clock_unavailable)
                }
                val refreshed = quoteProductState(account)
                if (revision != scheduledClockReadRevision) return@readWithSessionRecovery offline(Res.string.scheduled_clock_unavailable)
                if (refreshed is AppUiState.PassengerReady) refreshed.copy(scheduledLocalTimeOptions = result) else refreshed
            }
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.scheduled_clock_unavailable)
        }
    }

    suspend fun estimateScheduledPointToPoint(
        scheduledFor: String,
        cityId: String?,
        pickup: Coordinates,
        destination: Coordinates,
    ): AppUiState = scheduledEstimate({ it.matchesPointRequest(scheduledFor, cityId, pickup, destination) }) {
        it.estimatePointToPoint(scheduledFor, cityId, pickup, destination)
    }

    suspend fun estimateScheduledFixedRoute(
        scheduledFor: String,
        directionVersionId: String,
    ): AppUiState = scheduledEstimate({ it.matchesFixedRouteRequest(scheduledFor, directionVersionId) }) {
        it.estimateFixedRoute(scheduledFor, directionVersionId)
    }

    private suspend fun scheduledEstimate(
        matchesRequest: (ScheduledBookingEstimate) -> Boolean,
        estimate: suspend (ScheduledBookingGateway) -> ScheduledBookingEstimate,
    ): AppUiState {
        val gateway = scheduling ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            authentication.readWithSessionRecovery { account ->
                val result = estimate(gateway)
                if (!matchesRequest(result)) return@readWithSessionRecovery offline(Res.string.scheduled_review_unavailable)
                val refreshed = quoteProductState(account)
                if (refreshed is AppUiState.PassengerReady) {
                    refreshed.copy(scheduledBookingEstimate = result)
                } else refreshed
            }
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_estimate_failed)
        }
    }

    private suspend fun quoteProductState(account: CurrentAccount): AppUiState {
        // Quote reads already hold the non-reentrant credential mutex. Their
        // base projection must not enter navigation's owned quote read again.
        val state = baseAuthenticatedProductState(AuthenticationState.Authenticated(account))
        if (state is AppUiState.SignedOut && state.message?.resource == Res.string.message_session_expired) {
            throw AuthenticationRejectedException()
        }
        return state
    }

    suspend fun loadPassengerScheduledBookings(page: Int): AppUiState {
        require(page >= 1)
        if (appRole != AppRole.PASSENGER || scheduling == null || rides == null) return offline(Res.string.message_ride_services_unavailable)
        val selection = BookingPageSelection(page, authentication.localSessionOwnerEpoch)
        selectedBookingPage = selection
        bookingPageReadRevision++
        return try {
            authentication.readWithSessionRecovery { account ->
                if (selection.owner != authentication.localSessionOwnerEpoch) throw AuthenticationRejectedException()
                if (selectedBookingPage !== selection) throw CancellationException("Superseded booking page read")
                quoteProductState(account)
            }
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_scheduled_bookings_unavailable)
        }
    }

    suspend fun cancelScheduledBooking(bookingId: String): AppUiState {
        val owner = authentication.localSessionOwnerEpoch
        return schedulingMutation { gateway ->
            // The selected row may have moved to another page. Authorize and read
            // its current terms independently; only this read may recover a session.
            val booking = authentication.readWithSessionRecovery {
                if (owner != authentication.localSessionOwnerEpoch) throw AuthenticationRejectedException()
                gateway.passengerBooking(bookingId)
            }
            if (!navigationOwnerIsCurrent(owner)) throw AuthenticationRejectedException()
            if (!booking.cancellationTerms.isSupportedForReview) return@schedulingMutation null
            gateway.cancelPassengerBooking(bookingId, "PASSENGER_CANCELLED")
        }
    }

    suspend fun setScheduledOfferPreference(cityId: String, enabled: Boolean): AppUiState =
        schedulingMutation { it.setDriverPreference(cityId, enabled) }

    suspend fun respondToScheduledOffer(offerId: String, accept: Boolean): AppUiState {
        if (!accept) return schedulingMutation { it.declineOffer(offerId, "DRIVER_DECLINED") }
        val owner = authentication.localSessionOwnerEpoch
        return schedulingMutation(Res.string.scheduled_offer_unavailable) { gateway ->
            val offer = authentication.readWithSessionRecovery {
                if (owner != authentication.localSessionOwnerEpoch) throw AuthenticationRejectedException()
                gateway.driverOffers().filter { it.id == offerId }.singleOrNull()
            }
            if (!navigationOwnerIsCurrent(owner)) throw AuthenticationRejectedException()
            if (offer?.canReviewAcceptance != true) return@schedulingMutation null
            gateway.acceptOffer(offerId)
        }
    }

    private suspend fun schedulingMutation(
        reviewUnavailableMessage: StringResource = Res.string.scheduled_refund_unavailable,
        mutation: suspend (ScheduledBookingGateway) -> Any?,
    ): AppUiState {
        val gateway = scheduling ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            mutation(gateway) ?: return offline(reviewUnavailableMessage)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (error: ApiRequestException) {
            offline(if (error.reason == org.example.taximobile.data.network.ApiFailureReason.OPERATOR_MEMBERSHIP_REQUIRED)
                Res.string.message_membership_required else Res.string.message_ride_request_failed)
        }
    }

    suspend fun submitManualTransfer(rideId: String, payerReference: String?): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            gateway.submitManualTransfer(rideId, payerReference)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_manual_transfer_submission_failed)
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

    suspend fun sendRideCoordinationMessage(
        rideId: String,
        code: org.example.taximobile.domain.rides.RideCoordinationCode,
    ): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        return try {
            gateway.sendCoordinationMessage(rideId, code)
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_ride_coordination_failed)
        }
    }

    suspend fun loadPassengerRideHistoryDetail(rideId: String): AppUiState {
        val gateway = rides ?: return offline(Res.string.message_ride_services_unavailable)
        historySelection = null
        return try {
            // Reload the collection and account state first, then authorize the
            // selected resource independently through its detail endpoint.
            val refreshed = baseAuthenticatedProductState(authentication.restore())
            if (refreshed !is AppUiState.PassengerReady) return refreshed
            val owner = authentication.localSessionOwnerEpoch
            val detail = gateway.currentRide(rideId)
            if (!navigationOwnerIsCurrent(owner)) return signedOut(Res.string.message_session_expired)
            val receipt = if (detail.status == RideStatus.COMPLETED) gateway.receipt(rideId) else null
            if (!navigationOwnerIsCurrent(owner)) return signedOut(Res.string.message_session_expired)
            historySelection = HistorySelection(rideId, owner, refreshed.rideHistory.firstOrNull()?.id)
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
        historySelection = null
        return try {
            // Refresh owner-scoped driver collections first. The detail and
            // feedback endpoints still independently authorize this ride.
            val refreshed = baseAuthenticatedProductState(authentication.restore())
            if (refreshed !is AppUiState.DriverReady) return refreshed
            val owner = authentication.localSessionOwnerEpoch
            val detail = gateway.currentRide(rideId)
            if (!navigationOwnerIsCurrent(owner)) return signedOut(Res.string.message_session_expired)
            val rating = if (detail.status == RideStatus.COMPLETED) {
                gateway.ratings(rideId).firstOrNull()
            } else {
                null
            }
            if (!navigationOwnerIsCurrent(owner)) return signedOut(Res.string.message_session_expired)
            historySelection = HistorySelection(rideId, owner, refreshed.rideHistory.firstOrNull()?.id)
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

    suspend fun createSafetyReport(
        rideId: String,
        category: SafetyCategory,
        description: String,
    ): AppUiState {
        val gateway = safety ?: return offline(Res.string.message_safety_services_unavailable)
        return try {
            gateway.createReport(rideId, category, description.trim())
            authenticatedProductState(authentication.restore())
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_safety_creation_failed)
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

    /** Foreground owner supplies read-only REST catch-up; no commands are replayed. */
    suspend fun listenForLiveUpdates(onRefresh: suspend () -> Unit) {
        liveSubscription?.run(onRefresh)
    }

    private fun navigationOwnerIsCurrent(owner: Long): Boolean {
        val lifetime = liveSessionLifetime.value
        return owner == authentication.localSessionOwnerEpoch && lifetime.active && !lifetime.ending
    }

    private fun requireCurrentBookingRead(selection: BookingPageSelection, revision: Long) {
        if (!navigationOwnerIsCurrent(selection.owner)) throw AuthenticationRejectedException()
        if (selectedBookingPage !== selection || bookingPageReadRevision != revision) {
            throw CancellationException("Superseded booking page read")
        }
    }

    private suspend fun refreshRideQuote(state: AppUiState): AppUiState {
        val selection = rideQuoteSelection ?: return state
        if (!navigationOwnerIsCurrent(selection.owner)) {
            if (rideQuoteSelection == selection) rideQuoteSelection = null
            return state
        }
        if (state !is AppUiState.PassengerReady) return state
        if (state.activeRide != null || state.rideHistory.firstOrNull()?.id != selection.primaryRideId) {
            if (rideQuoteSelection == selection) rideQuoteSelection = null
            return state
        }
        val gateway = rides ?: return state
        return try {
            authentication.readWithSessionRecovery {
                if (!navigationOwnerIsCurrent(selection.owner)) throw AuthenticationRejectedException()
                val estimate = when (val input = selection.input) {
                    is RideQuoteInput.Point -> gateway.estimateRide(input.pickup, input.destination)
                    is RideQuoteInput.Fixed -> gateway.estimateFixedRoute(input.directionId)
                }
                val route = try {
                    (selection.input as? RideQuoteInput.Point)?.let { routing?.route(it.pickup, it.destination) }
                } catch (_: AuthenticationNetworkException) {
                    null
                } catch (_: ApiRequestException) {
                    null
                }
                if (!navigationOwnerIsCurrent(selection.owner)) throw AuthenticationRejectedException()
                if (rideQuoteSelection != selection) return@readWithSessionRecovery state
                state.copy(
                    fareEstimate = estimate,
                    reviewedPointQuoteInput = (selection.input as? RideQuoteInput.Point)?.let {
                        it.pickup to it.destination
                    },
                    selectedFixedRouteDirectionId = (selection.input as? RideQuoteInput.Fixed)?.directionId,
                    routePlan = route,
                    routeUnavailable = selection.input is RideQuoteInput.Point && routing != null && route == null,
                )
            }
        } catch (_: AuthenticationRejectedException) {
            if (rideQuoteSelection == selection) rideQuoteSelection = null
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (error: ApiRequestException) {
            if (error.statusCode in setOf(400, 403, 404, 409, 422) && rideQuoteSelection == selection) rideQuoteSelection = null
            offline(Res.string.message_ride_estimate_failed)
        }
    }

    private suspend fun authenticatedProductState(state: AuthenticationState): AppUiState {
        val refreshed = refreshRideQuote(baseAuthenticatedProductState(state))
        val selection = historySelection ?: return refreshed
        if (!navigationOwnerIsCurrent(selection.owner)) {
            if (historySelection == selection) historySelection = null
            return refreshed
        }
        val primaryRideId = when (refreshed) {
            is AppUiState.PassengerReady -> refreshed.rideHistory.firstOrNull()?.id
            is AppUiState.DriverReady -> refreshed.rideHistory.firstOrNull()?.id
            else -> return refreshed
        }
        // A new primary journey returns the account surface to its current
        // receipt rather than leaving a previous trip's cash result selected.
        if (primaryRideId != selection.primaryRideId) {
            if (historySelection == selection) historySelection = null
            return refreshed
        }
        val gateway = rides ?: return refreshed
        return try {
            authentication.readWithSessionRecovery {
                if (!navigationOwnerIsCurrent(selection.owner)) throw AuthenticationRejectedException()
                val detail = gateway.currentRide(selection.rideId)
                if (!navigationOwnerIsCurrent(selection.owner)) throw AuthenticationRejectedException()
                val result = when (refreshed) {
                    is AppUiState.PassengerReady -> refreshed.copy(
                        selectedHistoryRide = detail,
                        selectedHistoryReceipt = if (detail.status == RideStatus.COMPLETED) gateway.receipt(selection.rideId) else null,
                    )
                    is AppUiState.DriverReady -> refreshed.copy(
                        selectedHistoryRide = detail,
                        selectedHistoryRating = if (detail.status == RideStatus.COMPLETED) gateway.ratings(selection.rideId).firstOrNull() else null,
                    )
                    else -> refreshed
                }
                if (!navigationOwnerIsCurrent(selection.owner)) throw AuthenticationRejectedException()
                if (historySelection == selection) result else refreshed
            }
        } catch (_: AuthenticationRejectedException) {
            if (historySelection == selection) historySelection = null
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (error: ApiRequestException) {
            if (error.statusCode in setOf(403, 404) && historySelection == selection) historySelection = null
            offline(Res.string.message_ride_history_detail_failed)
        }
    }

    private suspend fun baseAuthenticatedProductState(state: AuthenticationState): AppUiState {
        val rendered = stateFor(state)
        if (
            appRole == AppRole.DRIVER &&
            rendered is AppUiState.DriverApplicationRequired &&
            driverRecruitment != null
        ) {
            return try {
                driverOnboardingState(rendered.displayName)
            } catch (_: AuthenticationRejectedException) {
                signedOut(Res.string.message_session_expired)
            } catch (_: AuthenticationNetworkException) {
                offline(Res.string.message_network_unavailable)
            } catch (_: ApiRequestException) {
                offline(Res.string.message_driver_recruitment_load_failed)
            }
        }
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
            val passengerRideGateway = rides
            return try {
                val owner = authentication.localSessionOwnerEpoch
                val selection = selectedBookingPage?.takeIf { it.owner == owner }
                    ?: BookingPageSelection(1, owner).also { selectedBookingPage = it }
                val revision = ++bookingPageReadRevision
                requireCurrentBookingRead(selection, revision)
                val passengerRides = passengerRideGateway.listRides()
                requireCurrentBookingRead(selection, revision)
                var scheduledBookingsLoadFailed = false
                val scheduledBookingPage = try {
                    var result = scheduling?.passengerBookings(selection.page)
                    requireCurrentBookingRead(selection, revision)
                    if (result != null && result.items.isEmpty() && result.page > 1) {
                        val lastPage = ((result.total.toLong() + result.limit - 1) / result.limit).coerceAtLeast(1).toInt()
                        if (lastPage < result.page) result = scheduling?.passengerBookings(lastPage)
                        requireCurrentBookingRead(selection, revision)
                    }
                    result
                } catch (_: AuthenticationNetworkException) {
                    scheduledBookingsLoadFailed = true
                    null
                } catch (_: ApiRequestException) {
                    scheduledBookingsLoadFailed = true
                    null
                }
                requireCurrentBookingRead(selection, revision)
                var catalogUnavailable = false
                val serviceCities = try {
                    passengerRideGateway.publicCities()
                } catch (_: AuthenticationNetworkException) {
                    catalogUnavailable = true
                    emptyList()
                } catch (_: ApiRequestException) {
                    catalogUnavailable = true
                    emptyList()
                }
                val selectedCity = serviceCities.firstOrNull { it.id == selectedFixedRouteCityId }
                    ?: serviceCities.firstOrNull()
                selectedFixedRouteCityId = selectedCity?.id
                val fixedRouteCatalog = selectedCity?.let { city ->
                    try {
                        passengerRideGateway.fixedRoutes(city.id)
                    } catch (_: AuthenticationNetworkException) {
                        catalogUnavailable = true
                        null
                    } catch (_: ApiRequestException) {
                        catalogUnavailable = true
                        null
                    }
                }
                val profile = passengerProfile?.profile()
                val notificationHistory = notifications?.list() ?: emptyList()
                val supportHistory = support?.tickets() ?: emptyList()
                val safetyHistory = safety?.reports() ?: emptyList()
                val product = passengerRides
                    .firstOrNull {
                        it.status !in setOf(RideStatus.COMPLETED, RideStatus.CANCELLED, RideStatus.UNMATCHED)
                    }
                    ?.let { activeSummary ->
                        val activeRide = passengerRideGateway.currentRide(activeSummary.id)
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
                            latestCoordinationMessage = activeRide.latestCoordinationMessage,
                            pickup = activeRide.pickup,
                            destination = activeRide.destination,
                            routePlan = routePlan,
                            routeUnavailable = routing != null &&
                                activeRide.pickup != null && activeRide.destination != null && routePlan == null,
                            serviceCities = serviceCities,
                            fixedRouteCatalog = fixedRouteCatalog,
                            fixedRouteCatalogUnavailable = catalogUnavailable,
                            activeServiceType = activeRide.serviceType,
                            activeFixedRoute = activeRide.fixedRoute,
                            rideHistory = passengerRides,
                            scheduledBookingPage = scheduledBookingPage,
                            scheduledBookingsLoadFailed = scheduledBookingsLoadFailed,
                            scheduledBookingRequestedPage = selection.page,
                            notifications = notificationHistory,
                            supportTickets = supportHistory,
                            safetyReports = safetyHistory,
                        )
                    }
                    ?: passengerRides.firstOrNull { it.status == RideStatus.COMPLETED }
                        ?.let { completedRide ->
                            val ratingExists = passengerRideGateway.ratings(completedRide.id).isNotEmpty()
                            val receipt = passengerRideGateway.receipt(completedRide.id)
                            AppUiState.PassengerReady(
                                profile = profile,
                                rateableRideId = completedRide.id.takeUnless { ratingExists },
                                rideHistory = passengerRides,
                                scheduledBookingPage = scheduledBookingPage,
                                scheduledBookingsLoadFailed = scheduledBookingsLoadFailed,
                                scheduledBookingRequestedPage = selection.page,
                                latestCompletedReceipt = receipt,
                                serviceCities = serviceCities,
                                fixedRouteCatalog = fixedRouteCatalog,
                                fixedRouteCatalogUnavailable = catalogUnavailable,
                                notifications = notificationHistory,
                                supportTickets = supportHistory,
                                safetyReports = safetyHistory,
                            )
                        }
                    ?: AppUiState.PassengerReady(
                        profile = profile,
                        serviceCities = serviceCities,
                        fixedRouteCatalog = fixedRouteCatalog,
                        fixedRouteCatalogUnavailable = catalogUnavailable,
                        rideHistory = passengerRides,
                        scheduledBookingPage = scheduledBookingPage,
                        scheduledBookingsLoadFailed = scheduledBookingsLoadFailed,
                        scheduledBookingRequestedPage = selection.page,
                        notifications = notificationHistory,
                        supportTickets = supportHistory,
                        safetyReports = safetyHistory,
                    )
                requireCurrentBookingRead(selection, revision)
                if (scheduledBookingPage != null && scheduledBookingPage.page != selection.page) {
                    selectedBookingPage = selection.copy(page = scheduledBookingPage.page)
                }
                product
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

    suspend fun loadDriverPendingCashPayments(page: Int): AppUiState {
        require(page >= 1)
        val gateway = driver ?: return offline(Res.string.message_driver_services_unavailable)
        return try {
            driverReadyWithOffers(gateway.currentAvailability(), pendingCashPage = page)
        } catch (_: AuthenticationRejectedException) {
            signedOut(Res.string.message_session_expired)
        } catch (_: AuthenticationNetworkException) {
            offline(Res.string.message_network_unavailable)
        } catch (_: ApiRequestException) {
            offline(Res.string.message_pending_cash_unavailable)
        }
    }

    private suspend fun driverReadyWithOffers(availability: DriverAvailability, pendingCashPage: Int = selectedPendingCashPage): AppUiState {
        val profile = driver?.profile()
        val offers = driverOffers?.currentOffers() ?: emptyList()
        val scheduledOffers = scheduling?.driverOffers().orEmpty()
        val scheduledCommitments = scheduling?.driverCommitments().orEmpty()
        val scheduledOfferPreferences = scheduling?.driverPreferences().orEmpty()
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
        var pendingCashLoadFailed = driverRides == null
        val pendingCashPayments = try {
            var queue = driverRides?.pendingCashPayments(pendingCashPage)
            if (queue != null && queue.page > 1 && queue.items.isEmpty()) {
                // Another device may settle the last item on this page. Read
                // the new final page instead of leaving the user stranded.
                val lastPage = ((queue.total.toLong() + queue.limit - 1) / queue.limit)
                    .coerceAtLeast(1).toInt()
                if (lastPage < queue.page) queue = driverRides?.pendingCashPayments(lastPage)
            }
            queue?.let { selectedPendingCashPage = it.page }
            queue
        } catch (_: AuthenticationNetworkException) {
            pendingCashLoadFailed = true
            null
        } catch (_: ApiRequestException) {
            pendingCashLoadFailed = true
            null
        }
        val notificationHistory = notifications?.list() ?: emptyList()
        val supportHistory = support?.tickets() ?: emptyList()
        val safetyHistory = safety?.reports() ?: emptyList()
        val cooperativeMembership = cooperatives?.currentMembership()
        val (authorizedMarkets, authorizationLoadFailed) = loadAuthorizedMarkets()
        return AppUiState.DriverReady(
            availability = availability.status,
            displayName = profile?.displayName,
            verificationStatus = profile?.verificationStatus,
            accountStatus = profile?.accountStatus,
            activeVehicleId = availability.activeVehicleId,
            onlineCityId = availability.cityId,
            onlineServiceType = availability.serviceType,
            authorizedMarkets = authorizedMarkets,
            cityAuthorizationRequired = driverRecruitment != null,
            cityAuthorizationLoadFailed = authorizationLoadFailed,
            credentials = credentials,
            vehicles = vehicles,
            activeRideId = activeRide?.id,
            activeRide = activeRide?.status,
            currentLocation = guidanceOrigin,
            latestCoordinationMessage = activeRideDetail?.latestCoordinationMessage,
            pickup = activeRideDetail?.pickup,
            destination = activeRideDetail?.destination,
            routePlan = routePlan,
            routeUnavailable = routing != null && guidanceOrigin != null && guidanceDestination != null && routePlan == null,
            activeServiceType = activeRideDetail?.serviceType
                ?: org.example.taximobile.domain.rides.RideServiceType.ON_DEMAND,
            activeFixedRoute = activeRideDetail?.fixedRoute,
            offers = offers,
            scheduledOffers = scheduledOffers,
            scheduledCommitments = scheduledCommitments,
            scheduledOfferPreferences = scheduledOfferPreferences,
            earnings = earnings,
            pendingCashPayments = pendingCashPayments,
            pendingCashLoadFailed = pendingCashLoadFailed,
            rideHistory = rideHistory,
            notifications = notificationHistory,
            supportTickets = supportHistory,
            safetyReports = safetyHistory,
            cooperativeMembership = cooperativeMembership,
        )
    }

    private suspend fun loadAuthorizedMarkets(): Pair<List<DriverAuthorizedMarket>, Boolean> {
        val recruitment = driverRecruitment ?: return emptyList<DriverAuthorizedMarket>() to false
        return try {
            val markets = buildList {
                for (summary in recruitment.applications().filter { it.status == "APPROVED" }) {
                    val application = recruitment.application(summary.id)
                    val authorization = application.authorization?.takeIf { it.status == "ACTIVE" }
                        ?: continue
                    add(
                        DriverAuthorizedMarket(
                            applicationId = application.id,
                            cityId = application.cityId,
                            cityCode = application.cityCode,
                            cityName = application.cityName,
                            authorization = authorization,
                        ),
                    )
                }
            }
            markets to false
        } catch (error: AuthenticationRejectedException) {
            throw error
        } catch (_: AuthenticationNetworkException) {
            emptyList<DriverAuthorizedMarket>() to true
        } catch (_: ApiRequestException) {
            emptyList<DriverAuthorizedMarket>() to true
        }
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
    AppUiState.SignedOut(message(resource), requiresSessionRecheck = true)

private fun AppUiState.withAccountSecurity(security: AccountSecurityUiState): AppUiState =
    when (this) {
        is AppUiState.PassengerReady -> copy(accountSecurity = security)
        is AppUiState.DriverReady -> copy(accountSecurity = security)
        else -> this
    }
