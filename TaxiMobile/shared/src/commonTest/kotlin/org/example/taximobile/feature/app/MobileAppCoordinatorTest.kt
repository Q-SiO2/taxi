package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlinx.coroutines.runBlocking
import org.example.taximobile.app.AppRole
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.domain.auth.AccountRole
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import org.example.taximobile.feature.auth.AuthenticationState
import org.example.taximobile.domain.drivers.DriverApplication
import org.example.taximobile.domain.drivers.DriverAvailability
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.drivers.DriverGateway
import org.example.taximobile.domain.drivers.DriverEarnings
import org.example.taximobile.domain.drivers.DriverRideGateway
import org.example.taximobile.domain.drivers.DriverRideSummary
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.FareEstimate
import org.example.taximobile.domain.rides.FinalRideFare
import org.example.taximobile.domain.rides.RideGateway
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideReceipt
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideSummary
import org.example.taximobile.domain.routing.RoutePlan
import org.example.taximobile.domain.routing.RoutingGateway
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.notifications.DevicePlatform
import org.example.taximobile.domain.notifications.NotificationGateway
import org.example.taximobile.domain.cooperatives.CooperativeGateway
import org.example.taximobile.domain.cooperatives.CooperativeMembership
import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.*

class MobileAppCoordinatorTest {
    @Test
    fun `driver product requires the backend driver role`() {
        val coordinator = MobileAppCoordinator(AppRole.DRIVER, unusedAuthentication())
        val account = CurrentAccount("user", setOf(AccountRole.PASSENGER), "Driver applicant")

        assertIs<AppUiState.DriverApplicationRequired>(coordinator.stateFor(AuthenticationState.Authenticated(account)))
    }

    @Test
    fun `invalid credentials remain on the sign in screen`() {
        val coordinator = MobileAppCoordinator(AppRole.PASSENGER, unusedAuthentication())

        assertIs<AppUiState.SignedOut>(
            coordinator.stateFor(
                AuthenticationState.Failure(UiMessage(Res.string.message_invalid_credentials))
            )
        )
    }

    @Test
    fun `successful account creation explicitly returns to sign in`() = runBlocking {
        val coordinator = MobileAppCoordinator(AppRole.PASSENGER, unusedAuthentication())

        val state = assertIs<AppUiState.SignedOut>(
            coordinator.register("Passenger", "passenger@example.test", null, "long-password"),
        )

        assertEquals(Res.string.message_account_created, state.message?.resource)
        assertEquals(true, state.registrationCompleted)
        assertEquals("passenger@example.test", state.suggestedIdentifier)
    }

    @Test
    fun `registration network failure remains on account creation form`() = runBlocking {
        val authentication = AuthenticationSessionCoordinator(
            gateway = object : AuthenticationGateway {
                override suspend fun register(
                    displayName: String,
                    email: String?,
                    phoneNumber: String?,
                    password: String,
                ) = throw AuthenticationNetworkException()

                override suspend fun login(identifier: String, password: String, deviceLabel: String?) =
                    error("Not used")
                override suspend fun refresh(refreshToken: String) = error("Not used")
                override suspend fun logout(accessToken: String) = error("Not used")
                override suspend fun currentAccount(accessToken: String) = error("Not used")
            },
            tokenStore = object : SecureTokenStore {
                override suspend fun tokens(): StoredTokens? = null
                override suspend fun save(accessToken: String, refreshToken: String) = error("Not used")
                override suspend fun clear() = error("Not used")
            },
        )
        val coordinator = MobileAppCoordinator(AppRole.PASSENGER, authentication)

        val state = assertIs<AppUiState.SignedOut>(
            coordinator.register("Passenger", "passenger@example.test", null, "long-password"),
        )

        assertEquals(Res.string.message_network_unavailable, state.message?.resource)
        assertEquals(true, state.showRegistrationForm)
        assertFalse(state.registrationCompleted)
    }

    @Test
    fun `registration progress is not an authenticated session`() {
        assertFalse(AppUiState.RegisteringAccount.hasAuthenticatedSession())
    }

    @Test
    fun `logout revokes the push token registered by the current account`() = runBlocking {
        val notifications = RecordingNotificationGateway()
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = unusedAuthentication(),
            notifications = notifications,
        )

        assertEquals(
            true,
            coordinator.registerPushRegistration("firebase-installation-id", DevicePlatform.ANDROID),
        )
        coordinator.logout()

        assertEquals("firebase-installation-id" to DevicePlatform.ANDROID, notifications.revoked)
    }

    @Test
    fun `accepted offline location enables the separate online action`() = runBlocking {
        val gateway = RecordingDriverGateway()
        val coordinator = MobileAppCoordinator(AppRole.DRIVER, unusedAuthentication(), driver = gateway)
        val location = Coordinates(33.5731, -7.5898)

        val state = assertIs<AppUiState.DriverReady>(coordinator.updateDriverLocation(location))

        assertEquals(location, gateway.submittedLocation)
        assertEquals(location, state.currentLocation)
        assertEquals(DriverAvailabilityStatus.OFFLINE, state.availability)
    }

    @Test
    fun `authoritative availability refresh retains the latest accepted foreground location`() = runBlocking {
        val gateway = RecordingDriverGateway()
        val coordinator = MobileAppCoordinator(AppRole.DRIVER, unusedAuthentication(), driver = gateway)
        val location = Coordinates(33.5731, -7.5898)

        coordinator.updateDriverLocation(location)
        val state = assertIs<AppUiState.DriverReady>(coordinator.changeDriverAvailability(online = true))

        assertEquals(DriverAvailabilityStatus.AVAILABLE, state.availability)
        assertEquals(location, state.currentLocation)
    }

    @Test
    fun `driver refresh exposes backend cooperative membership independently of eligibility`() = runBlocking {
        val membership = CooperativeMembership(
            cooperativeId = "cooperative",
            cooperativeName = "Casablanca Taxi Cooperative",
            status = "ACTIVE",
            joinedAt = "2026-01-01T00:00:00Z",
            membershipNumber = "MEMBER-123",
        )
        val coordinator = MobileAppCoordinator(
            AppRole.DRIVER,
            unusedAuthentication(),
            driver = RecordingDriverGateway(),
            cooperatives = object : CooperativeGateway {
                override suspend fun currentMembership() = membership
            },
        )

        val state = assertIs<AppUiState.DriverReady>(coordinator.changeDriverAvailability(online = false))

        assertEquals(membership, state.cooperativeMembership)
        assertEquals(DriverAvailabilityStatus.OFFLINE, state.availability)
    }

    @Test
    fun `driver refresh exposes only backend credential metadata`() = runBlocking {
        val credential = DriverCredential(
            id = "credential",
            type = "DRIVER_LICENSE",
            status = "VERIFIED",
            issuedAt = "2025-08-13T00:00:00Z",
            expiresAt = "2027-08-13T00:00:00Z",
        )
        val coordinator = MobileAppCoordinator(
            AppRole.DRIVER,
            unusedAuthentication(),
            driver = RecordingDriverGateway(listOf(credential)),
        )

        val state = assertIs<AppUiState.DriverReady>(coordinator.changeDriverAvailability(online = false))

        assertEquals(listOf(credential), state.credentials)
        assertEquals("APPROVED", state.verificationStatus)
        assertEquals("ACTIVE", state.accountStatus)
    }

    @Test
    fun `logout clears the retained driver coordinate`() = runBlocking {
        val coordinator = MobileAppCoordinator(
            AppRole.DRIVER,
            unusedAuthentication(),
            driver = RecordingDriverGateway(),
        )

        coordinator.updateDriverLocation(Coordinates(33.5731, -7.5898))
        coordinator.logout()
        val state = assertIs<AppUiState.DriverReady>(coordinator.changeDriverAvailability(online = true))

        assertNull(state.currentLocation)
    }

    @Test
    fun `driver refresh recomputes pickup guidance from latest accepted location`() = runBlocking {
        val location = Coordinates(33.5731, -7.5898)
        val pickup = Coordinates(33.5899, -7.6039)
        val route = RoutePlan(2_100, 420, listOf(location, pickup), emptyList())
        val routing = RecordingRoutingGateway(route)
        val coordinator = MobileAppCoordinator(
            AppRole.DRIVER,
            unusedAuthentication(),
            driver = RecordingDriverGateway(),
            driverRides = ActiveDriverRideGateway(),
            rides = ActiveRideGateway(pickup),
            routing = routing,
        )

        val state = assertIs<AppUiState.DriverReady>(coordinator.updateDriverLocation(location))

        assertEquals(location to pickup, routing.lastRequest)
        assertEquals(route, state.routePlan)
        assertEquals(false, state.routeUnavailable)
    }

    @Test
    fun `passenger cancellation refreshes terminal history and restores new ride controls`() = runBlocking {
        val rides = CancellingPassengerRideGateway()
        val coordinator = MobileAppCoordinator(
            AppRole.PASSENGER,
            passengerAuthentication(),
            rides = rides,
        )

        val state = assertIs<AppUiState.PassengerReady>(coordinator.cancelRide("ride"))

        assertEquals("PASSENGER_CANCELLED", rides.cancellationReason)
        assertNull(state.activeRideId)
        assertNull(state.activeRide)
        assertEquals(listOf(RideStatus.CANCELLED), state.rideHistory.map { it.status })
    }

    @Test
    fun `requested passenger ride reloads detailed route for active tracking`() = runBlocking {
        val pickup = Coordinates(33.5731, -7.5898)
        val destination = Coordinates(33.5899, -7.6039)
        val route = RoutePlan(2_100, 420, listOf(pickup, destination), emptyList())
        val rides = RequestedPassengerRideGateway(pickup, destination)
        val routing = RecordingRoutingGateway(route)
        val coordinator = MobileAppCoordinator(
            AppRole.PASSENGER,
            passengerAuthentication(),
            rides = rides,
            routing = routing,
        )

        val state = assertIs<AppUiState.PassengerReady>(coordinator.requestRide(pickup, destination))

        assertEquals(pickup to destination, rides.requestedTrip)
        assertEquals("ride", state.activeRideId)
        assertEquals(RideStatus.MATCHING, state.activeRide)
        assertEquals(pickup, state.pickup)
        assertEquals(destination, state.destination)
        assertEquals(route, state.routePlan)
        assertEquals(pickup to destination, routing.lastRequest)
    }

    @Test
    fun `passenger history selection reloads owned detail and completed receipt`() = runBlocking {
        val rides = PassengerHistoryDetailGateway()
        val coordinator = MobileAppCoordinator(
            AppRole.PASSENGER,
            passengerAuthentication(),
            rides = rides,
        )

        val state = assertIs<AppUiState.PassengerReady>(
            coordinator.loadPassengerRideHistoryDetail("ride-history"),
        )

        assertEquals("ride-history", rides.requestedDetailId)
        assertEquals("ride-history", state.selectedHistoryRide?.id)
        assertEquals("Casa Voyageurs", state.selectedHistoryRide?.destination?.address)
        assertEquals("42.00", state.selectedHistoryReceipt?.fare?.amount)
        assertEquals(2, rides.receiptRequests)
    }

    @Test
    fun `driver history detail loads only the selected authorized ride rating`() = runBlocking {
        val rides = PassengerHistoryDetailGateway()
        val coordinator = MobileAppCoordinator(
            AppRole.DRIVER,
            driverAuthentication(),
            driver = RecordingDriverGateway(),
            driverRides = CompletedDriverRideGateway(),
            rides = rides,
        )

        val state = assertIs<AppUiState.DriverReady>(
            coordinator.loadDriverRideHistoryDetail("ride-history"),
        )

        assertEquals("ride-history", rides.requestedDetailId)
        assertEquals("ride-history", state.selectedHistoryRide?.id)
        assertEquals("Casa Voyageurs", state.selectedHistoryRide?.destination?.address)
        assertEquals(5, state.selectedHistoryRating?.score)
        assertEquals("Smooth ride", state.selectedHistoryRating?.comment)
        assertEquals(1, rides.ratingRequests)
        assertEquals(0, rides.receiptRequests)
    }

    @Test
    fun `retry restore recovers a retained session after a transient network failure`() = runBlocking {
        var accountRequests = 0
        var tokenClearCount = 0
        val gateway = object : AuthenticationGateway {
            override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
            override suspend fun login(identifier: String, password: String, deviceLabel: String?) = unusedTokens()
            override suspend fun refresh(refreshToken: String) = unusedTokens()
            override suspend fun logout(accessToken: String) = Unit
            override suspend fun currentAccount(accessToken: String): CurrentAccount {
                accountRequests += 1
                if (accountRequests == 1) throw AuthenticationNetworkException()
                return CurrentAccount("user", setOf(AccountRole.PASSENGER), "Passenger")
            }
        }
        val tokenStore = object : SecureTokenStore {
            override suspend fun tokens() = StoredTokens("access", "refresh")
            override suspend fun save(accessToken: String, refreshToken: String) = Unit
            override suspend fun clear() {
                tokenClearCount += 1
            }
        }
        val coordinator = MobileAppCoordinator(
            AppRole.PASSENGER,
            AuthenticationSessionCoordinator(gateway, tokenStore),
        )

        assertIs<AppUiState.Offline>(coordinator.restore())
        assertIs<AppUiState.PassengerReady>(coordinator.restore())
        assertEquals(0, tokenClearCount)
    }
}

private class PassengerHistoryDetailGateway : RideGateway {
    var requestedDetailId: String? = null
    var receiptRequests = 0
    var ratingRequests = 0
    private val destination = Coordinates(33.5890, -7.5910, "Casa Voyageurs")
    private val summary = RideSummary(
        id = "ride-history",
        status = RideStatus.COMPLETED,
        completedAt = "2026-08-13T12:00:00Z",
        pickup = Coordinates(33.5731, -7.5898, "Pickup"),
        destination = destination,
    )

    override suspend fun listRides() = listOf(summary)
    override suspend fun currentRide(id: String): RideSummary {
        requestedDetailId = id
        return summary
    }
    override suspend fun receipt(id: String): RideReceipt {
        receiptRequests += 1
        return RideReceipt(id, summary.completedAt!!, FinalRideFare("42.00", "MAD"), "CASH", "COMPLETED")
    }
    override suspend fun ratings(id: String): List<RideRating> {
        ratingRequests += 1
        return listOf(RideRating("rating", 5, "Smooth ride"))
    }
    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = error("Not used")
    override suspend fun finalFare(id: String): FinalRideFare = error("Not used")
    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary = error("Not used")
    override suspend fun cancelRide(id: String, reason: String): RideSummary = error("Not used")
    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = error("Not used")
}

private class CompletedDriverRideGateway : DriverRideGateway {
    override suspend fun rides() = listOf(
        DriverRideSummary("ride-history", RideStatus.COMPLETED, "2026-08-13T12:00:00Z")
    )
    override suspend fun earnings() = DriverEarnings("MAD", "0.00", "0.00", "0.00", "0.00")
    override suspend fun markEnRoute(rideId: String) = error("Not used")
    override suspend fun markArrived(rideId: String) = error("Not used")
    override suspend fun start(rideId: String) = error("Not used")
    override suspend fun cancel(rideId: String, reason: String) = error("Not used")
    override suspend fun complete(rideId: String, location: Coordinates) = error("Not used")
    override suspend fun settleCash(rideId: String) = error("Not used")
}

private class RecordingDriverGateway(
    private val credentialItems: List<DriverCredential> = emptyList(),
) : DriverGateway {
    var submittedLocation: Coordinates? = null

    override suspend fun apply(displayName: String) = error("Not used")
    override suspend fun profile() = DriverApplication("Driver", "APPROVED", "ACTIVE")
    override suspend fun verificationStatus() = "APPROVED"
    override suspend fun submitVerification() = error("Not used")
    override suspend fun currentAvailability() = DriverAvailability(DriverAvailabilityStatus.OFFLINE, "vehicle")
    override suspend fun goOnline() = DriverAvailability(DriverAvailabilityStatus.AVAILABLE, "vehicle")
    override suspend fun goOffline() = DriverAvailability(DriverAvailabilityStatus.OFFLINE, "vehicle")
    override suspend fun credentials() = credentialItems
    override suspend fun vehicles(): List<DriverVehicle> = emptyList()
    override suspend fun registerVehicle(vehicle: VehicleRegistration) = error("Not used")
    override suspend fun selectActiveVehicle(vehicleId: String) = error("Not used")
    override suspend fun deactivateVehicle(vehicleId: String) = error("Not used")
    override suspend fun updateLocation(location: Coordinates, observedAt: String) {
        submittedLocation = location
    }
}

private class ActiveDriverRideGateway : DriverRideGateway {
    override suspend fun rides() = listOf(DriverRideSummary("ride", RideStatus.ACCEPTED))
    override suspend fun earnings() = DriverEarnings("MAD", "0.00", "0.00", "0.00", "0.00")
    override suspend fun markEnRoute(rideId: String) = error("Not used")
    override suspend fun markArrived(rideId: String) = error("Not used")
    override suspend fun start(rideId: String) = error("Not used")
    override suspend fun cancel(rideId: String, reason: String) = error("Not used")
    override suspend fun complete(rideId: String, location: Coordinates) = error("Not used")
    override suspend fun settleCash(rideId: String) = error("Not used")
}

private class ActiveRideGateway(private val pickup: Coordinates) : RideGateway {
    override suspend fun currentRide(id: String) = RideSummary(
        id = id,
        status = RideStatus.ACCEPTED,
        pickup = pickup,
        destination = Coordinates(33.6000, -7.6200),
    )

    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = error("Not used")
    override suspend fun listRides(): List<RideSummary> = error("Not used")
    override suspend fun finalFare(id: String): FinalRideFare = error("Not used")
    override suspend fun receipt(id: String): RideReceipt = error("Not used")
    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary = error("Not used")
    override suspend fun cancelRide(id: String, reason: String): RideSummary = error("Not used")
    override suspend fun ratings(id: String): List<RideRating> = error("Not used")
    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = error("Not used")
}

private class RecordingRoutingGateway(private val route: RoutePlan) : RoutingGateway {
    var lastRequest: Pair<Coordinates, Coordinates>? = null

    override suspend fun route(origin: Coordinates, destination: Coordinates): RoutePlan {
        lastRequest = origin to destination
        return route
    }
}

private class CancellingPassengerRideGateway : RideGateway {
    var cancellationReason: String? = null

    override suspend fun cancelRide(id: String, reason: String): RideSummary {
        cancellationReason = reason
        return RideSummary(id, RideStatus.CANCELLED)
    }

    override suspend fun listRides() = listOf(RideSummary("ride", RideStatus.CANCELLED))
    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = error("Not used")
    override suspend fun currentRide(id: String): RideSummary = error("Not used")
    override suspend fun finalFare(id: String): FinalRideFare = error("Not used")
    override suspend fun receipt(id: String): RideReceipt = error("Not used")
    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary = error("Not used")
    override suspend fun ratings(id: String): List<RideRating> = error("Not used")
    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = error("Not used")
}

private class RequestedPassengerRideGateway(
    private val pickup: Coordinates,
    private val destination: Coordinates,
) : RideGateway {
    var requestedTrip: Pair<Coordinates, Coordinates>? = null

    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary {
        requestedTrip = pickup to destination
        return RideSummary("ride", RideStatus.MATCHING, pickup = pickup, destination = destination)
    }

    override suspend fun listRides() = listOf(RideSummary("ride", RideStatus.MATCHING))
    override suspend fun currentRide(id: String) =
        RideSummary(id, RideStatus.MATCHING, pickup = pickup, destination = destination)
    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = error("Not used")
    override suspend fun finalFare(id: String): FinalRideFare = error("Not used")
    override suspend fun receipt(id: String): RideReceipt = error("Not used")
    override suspend fun cancelRide(id: String, reason: String): RideSummary = error("Not used")
    override suspend fun ratings(id: String): List<RideRating> = error("Not used")
    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = error("Not used")
}

private fun unusedAuthentication() = AuthenticationSessionCoordinator(
    gateway = object : AuthenticationGateway {
        override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
        override suspend fun login(identifier: String, password: String, deviceLabel: String?) = unusedTokens()
        override suspend fun refresh(refreshToken: String) = unusedTokens()
        override suspend fun logout(accessToken: String) = Unit
        override suspend fun currentAccount(accessToken: String) = error("Not used by this state-mapping test")
    },
    tokenStore = object : SecureTokenStore {
        override suspend fun tokens(): StoredTokens? = null
        override suspend fun save(accessToken: String, refreshToken: String) = Unit
        override suspend fun clear() = Unit
    },
)

private fun passengerAuthentication() = AuthenticationSessionCoordinator(
    gateway = object : AuthenticationGateway {
        override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
        override suspend fun login(identifier: String, password: String, deviceLabel: String?) = unusedTokens()
        override suspend fun refresh(refreshToken: String) = unusedTokens()
        override suspend fun logout(accessToken: String) = Unit
        override suspend fun currentAccount(accessToken: String) =
            CurrentAccount("passenger", setOf(AccountRole.PASSENGER), "Passenger")
    },
    tokenStore = object : SecureTokenStore {
        override suspend fun tokens() = StoredTokens("access", "refresh")
        override suspend fun save(accessToken: String, refreshToken: String) = Unit
        override suspend fun clear() = Unit
    },
)

private fun driverAuthentication() = AuthenticationSessionCoordinator(
    gateway = object : AuthenticationGateway {
        override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
        override suspend fun login(identifier: String, password: String, deviceLabel: String?) = unusedTokens()
        override suspend fun refresh(refreshToken: String) = unusedTokens()
        override suspend fun logout(accessToken: String) = Unit
        override suspend fun currentAccount(accessToken: String) =
            CurrentAccount("driver", setOf(AccountRole.DRIVER), "Driver")
    },
    tokenStore = object : SecureTokenStore {
        override suspend fun tokens() = StoredTokens("access", "refresh")
        override suspend fun save(accessToken: String, refreshToken: String) = Unit
        override suspend fun clear() = Unit
    },
)

private fun unusedTokens() = SessionTokens(accessToken = "unused", refreshToken = "unused")

private class RecordingNotificationGateway : NotificationGateway {
    var revoked: Pair<String, DevicePlatform>? = null

    override suspend fun list(): List<AppNotification> = emptyList()
    override suspend fun markRead(id: String): AppNotification = error("Not used")
    override suspend fun registerDevice(registrationId: String, platform: DevicePlatform) = Unit
    override suspend fun unregisterDevice(registrationId: String, platform: DevicePlatform) {
        revoked = registrationId to platform
    }
}
