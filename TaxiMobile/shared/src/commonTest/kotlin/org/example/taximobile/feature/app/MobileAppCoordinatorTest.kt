package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlinx.coroutines.runBlocking
import org.example.taximobile.app.AppRole
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AccountSecurityGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.AccountRole
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import org.example.taximobile.domain.auth.AccountRecoveryCodes
import org.example.taximobile.domain.auth.AccountSession
import org.example.taximobile.domain.auth.AccountSessionRevocation
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import org.example.taximobile.feature.auth.AuthenticationState
import org.example.taximobile.domain.drivers.DriverApplication
import org.example.taximobile.domain.drivers.DriverAvailability
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus
import org.example.taximobile.domain.drivers.DriverCredential
import org.example.taximobile.domain.drivers.DriverApplicationAnswerDraft
import org.example.taximobile.domain.drivers.DriverApplicationEvidenceDraft
import org.example.taximobile.domain.drivers.DriverCityApplication
import org.example.taximobile.domain.drivers.DriverCityApplicationSummary
import org.example.taximobile.domain.drivers.DriverCityAuthorization
import org.example.taximobile.domain.drivers.DriverDocumentUpload
import org.example.taximobile.domain.drivers.DriverGateway
import org.example.taximobile.domain.drivers.DriverRecruitmentGateway
import org.example.taximobile.domain.drivers.RecruitingCity
import org.example.taximobile.domain.drivers.RecruitmentCopy
import org.example.taximobile.domain.drivers.DriverEarnings
import org.example.taximobile.domain.drivers.DriverRideGateway
import org.example.taximobile.domain.drivers.DriverRideSummary
import org.example.taximobile.domain.drivers.DriverVehicle
import org.example.taximobile.domain.drivers.VehicleRegistration
import org.example.taximobile.domain.rides.Coordinates
import org.example.taximobile.domain.rides.FareEstimate
import org.example.taximobile.domain.rides.FinalRideFare
import org.example.taximobile.domain.rides.ManualTransferInstructions
import org.example.taximobile.domain.rides.RideGateway
import org.example.taximobile.domain.rides.RideCoordinationCode
import org.example.taximobile.domain.rides.RideCoordinationMessage
import org.example.taximobile.domain.rides.RideCoordinationSenderRole
import org.example.taximobile.domain.rides.RidePaymentMethod
import org.example.taximobile.domain.rides.RideRating
import org.example.taximobile.domain.rides.RideReceipt
import org.example.taximobile.domain.rides.RideStatus
import org.example.taximobile.domain.rides.RideSummary
import org.example.taximobile.domain.routing.RoutePlan
import org.example.taximobile.domain.routing.RoutingGateway
import org.example.taximobile.domain.places.PlaceAttribution
import org.example.taximobile.domain.places.PlaceDiscoveryGateway
import org.example.taximobile.domain.places.PlaceKind
import org.example.taximobile.domain.places.PlaceResult
import org.example.taximobile.domain.places.PlaceSearch
import org.example.taximobile.domain.places.ReversePlace
import org.example.taximobile.domain.notifications.AppNotification
import org.example.taximobile.domain.notifications.DevicePlatform
import org.example.taximobile.domain.notifications.NotificationGateway
import org.example.taximobile.domain.safety.SafetyCategory
import org.example.taximobile.domain.safety.SafetyGateway
import org.example.taximobile.domain.safety.SafetyReport
import org.example.taximobile.domain.cooperatives.CooperativeGateway
import org.example.taximobile.domain.cooperatives.CooperativeMembership
import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.*

class MobileAppCoordinatorTest {
    @Test
    fun `place search and reverse lookup remain provider neutral`() = runBlocking {
        val place = PlaceResult(
            id = "opaque-result",
            primaryText = "Gare Rabat Ville",
            secondaryText = "Hassan, Rabat",
            coordinate = Coordinates(34.0209, -6.8416),
            kind = PlaceKind.POI,
            pickupServiceable = true,
        )
        val gateway = RecordingPlaceDiscoveryGateway(place)
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = passengerAuthentication(),
            places = gateway,
        )

        val searched = assertIs<AppUiState.PassengerReady>(
            coordinator.searchPlaces("city-rabat", "  Gare Rabat  "),
        )
        assertEquals("city-rabat", searched.placeDiscovery.search?.cityId)
        assertEquals("opaque-result", searched.placeDiscovery.search?.items?.single()?.id)
        assertEquals("  Gare Rabat  ", gateway.searchQuery)

        val coordinate = Coordinates(34.021, -6.842)
        val reversed = assertIs<AppUiState.PassengerReady>(
            coordinator.reversePlace("city-rabat", coordinate),
        )
        assertEquals(coordinate, gateway.reverseCoordinate)
        assertEquals("opaque-result", reversed.placeDiscovery.reverse?.item?.id)
        assertEquals(searched.placeDiscovery.revision + 1, reversed.placeDiscovery.revision)
    }

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
    fun `recovery progress is not an authenticated session`() {
        assertFalse(AppUiState.RecoveringAccount.hasAuthenticatedSession())
    }

    @Test
    fun `account recovery always returns the generic accepted message`() = runBlocking {
        val security = RecordingAccountSecurityGateway()
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = unusedAuthentication(),
            accountSecurity = security,
        )

        val state = assertIs<AppUiState.SignedOut>(
            coordinator.recoverAccount(
                "passenger@example.test",
                "23456-789AB-CDEFG-HJKLM",
                "new-password-long-enough",
            ),
        )

        assertEquals(Res.string.message_account_recovery_accepted, state.message?.resource)
        assertEquals(true, state.recoveryCompleted)
        assertEquals("passenger@example.test", security.identifier)
    }

    @Test
    fun `account recovery transport failure keeps the recovery form visible`() = runBlocking {
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = unusedAuthentication(),
            accountSecurity = RecordingAccountSecurityGateway(networkFailure = true),
        )

        val state = assertIs<AppUiState.SignedOut>(
            coordinator.recoverAccount(
                "passenger@example.test",
                "23456-789AB-CDEFG-HJKLM",
                "new-password-long-enough",
            ),
        )

        assertEquals(Res.string.message_network_unavailable, state.message?.resource)
        assertEquals(true, state.showRecoveryForm)
    }

    @Test
    fun `account security loads backend sessions into passenger account state`() = runBlocking {
        val security = RecordingAccountSecurityGateway(
            activeSessions = listOf(
                AccountSession("session", "Android passenger app", true, "created", "expires"),
            ),
        )
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = passengerAuthentication(),
            accountSecurity = security,
        )

        val state = assertIs<AppUiState.PassengerReady>(coordinator.loadAccountSecurity())

        assertEquals(true, state.accountSecurity.loaded)
        assertEquals("session", state.accountSecurity.sessions.single().id)
    }

    @Test
    fun `creating recovery codes exposes the one-time backend bundle`() = runBlocking {
        val security = RecordingAccountSecurityGateway()
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = passengerAuthentication(),
            accountSecurity = security,
        )

        val state = assertIs<AppUiState.PassengerReady>(
            coordinator.createRecoveryCodes("current-password"),
        )

        assertEquals("current-password", security.currentPassword)
        assertEquals(listOf("23456-789AB-CDEFG-HJKLM"), state.accountSecurity.recoveryCodes?.codes)
        assertEquals(Res.string.message_recovery_codes_created, state.accountSecurity.message?.resource)
    }

    @Test
    fun `revoking current session returns to sign in`() = runBlocking {
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = passengerAuthentication(),
            accountSecurity = RecordingAccountSecurityGateway(revokesCurrentSession = true),
        )

        val state = assertIs<AppUiState.SignedOut>(coordinator.revokeAccountSession("session"))

        assertEquals(Res.string.message_current_session_revoked, state.message?.resource)
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
    fun `online command sends the explicitly selected city and service`() = runBlocking {
        val gateway = RecordingDriverGateway()
        val coordinator = MobileAppCoordinator(AppRole.DRIVER, unusedAuthentication(), driver = gateway)

        val state = assertIs<AppUiState.DriverReady>(
            coordinator.changeDriverAvailability(
                online = true,
                cityId = "city-casablanca",
                serviceType = "FIXED_ROUTE",
            ),
        )

        assertEquals("city-casablanca" to "FIXED_ROUTE", gateway.requestedOnlineMarket)
        assertEquals("city-casablanca", state.onlineCityId)
        assertEquals("FIXED_ROUTE", state.onlineServiceType)
    }

    @Test
    fun `driver applicant restore loads the public recruiting city catalog`() = runBlocking {
        val recruitment = RecordingRecruitmentGateway()
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.DRIVER,
            authentication = applicantAuthentication(),
            driverRecruitment = recruitment,
        )

        val state = assertIs<AppUiState.DriverOnboarding>(coordinator.restore())

        assertEquals(listOf("CASABLANCA"), state.recruitingCities.map { it.code })
        assertEquals("Applicant", state.displayName)
        assertNull(state.selectedApplication)
    }

    @Test
    fun `approved city applications become named operating authorizations`() = runBlocking {
        val application = approvedCityApplication()
        val recruitment = RecordingRecruitmentGateway(application)
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.DRIVER,
            authentication = driverAuthentication(),
            driver = RecordingDriverGateway(),
            driverRecruitment = recruitment,
        )

        val state = assertIs<AppUiState.DriverReady>(coordinator.restore())

        assertEquals(true, state.cityAuthorizationRequired)
        assertFalse(state.cityAuthorizationLoadFailed)
        assertEquals(listOf("CASABLANCA"), state.authorizedMarkets.map { it.cityCode })
        assertEquals(listOf("ON_DEMAND", "FIXED_ROUTE"), state.authorizedMarkets.single().authorization.serviceTypes)
    }

    @Test
    fun `city application update preserves backend optimistic version authority`() = runBlocking {
        val recruitment = RecordingRecruitmentGateway(draftCityApplication())
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.DRIVER,
            authentication = applicantAuthentication(),
            driverRecruitment = recruitment,
        )
        val answer = DriverApplicationAnswerDraft(
            requirementItemId = "requirement-name",
            answerType = "TEXT",
            textValue = "Applicant Name",
        )

        val state = assertIs<AppUiState.DriverOnboarding>(
            coordinator.saveDriverCityApplication(
                applicationId = "application",
                expectedVersion = 7,
                displayName = "Applicant",
                answers = listOf(answer),
                evidence = emptyList(),
            ),
        )

        assertEquals(7, recruitment.lastExpectedVersion)
        assertEquals(listOf(answer), recruitment.lastAnswers)
        assertEquals("application", state.selectedApplication?.id)
    }

    @Test
    fun `driver document upload forwards bounded file metadata and authoritative version`() = runBlocking {
        val recruitment = RecordingRecruitmentGateway(draftCityApplication())
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.DRIVER,
            authentication = applicantAuthentication(),
            driverRecruitment = recruitment,
        )
        val document = DriverDocumentUpload(
            fileName = "license.pdf",
            mediaType = "application/pdf",
            bytes = "%PDF-1.7".encodeToByteArray(),
        )

        val state = assertIs<AppUiState.DriverOnboarding>(
            coordinator.uploadDriverCityApplicationDocument(
                applicationId = "application",
                requirementItemId = "requirement-license",
                expectedVersion = 7,
                displayName = "Applicant",
                document = document,
            ),
        )

        assertEquals("application", recruitment.lastDocumentApplicationId)
        assertEquals("requirement-license", recruitment.lastDocumentRequirementItemId)
        assertEquals(7, recruitment.lastExpectedVersion)
        assertEquals("license.pdf", recruitment.lastDocumentUpload?.fileName)
        assertEquals("application/pdf", recruitment.lastDocumentUpload?.mediaType)
        assertContentEquals(document.bytes, recruitment.lastDocumentUpload?.bytes)
        assertEquals(8, state.selectedApplication?.optimisticVersion)
        assertEquals(true, state.selectedApplication?.complete)
    }

    @Test
    fun `driver document deletion forwards identity and refreshes authoritative completeness`() = runBlocking {
        val recruitment = RecordingRecruitmentGateway(
            draftCityApplication().copy(optimisticVersion = 8, complete = true),
        )
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.DRIVER,
            authentication = applicantAuthentication(),
            driverRecruitment = recruitment,
        )

        val state = assertIs<AppUiState.DriverOnboarding>(
            coordinator.deleteDriverCityApplicationDocument(
                applicationId = "application",
                documentId = "document-1",
                expectedVersion = 8,
                displayName = "Applicant",
            ),
        )

        assertEquals("application", recruitment.lastDocumentApplicationId)
        assertEquals("document-1", recruitment.lastDeletedDocumentId)
        assertEquals(8, recruitment.lastExpectedVersion)
        assertEquals(9, state.selectedApplication?.optimisticVersion)
        assertEquals(false, state.selectedApplication?.complete)
    }

    @Test
    fun `application mutation stays renderable when the authoritative reload fails`() = runBlocking {
        val recruitment = RecordingRecruitmentGateway(
            initialApplication = draftCityApplication(),
            failCatalog = true,
        )
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.DRIVER,
            authentication = applicantAuthentication(),
            driverRecruitment = recruitment,
        )

        val state = assertIs<AppUiState.DriverOnboarding>(
            coordinator.saveDriverCityApplication(
                applicationId = "application",
                expectedVersion = 7,
                displayName = "Applicant",
                answers = emptyList(),
                evidence = emptyList(),
            ),
        )

        assertEquals("Applicant", state.displayName)
        assertNotNull(state.message)
        assertEquals(emptyList(), state.recruitingCities)
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
    fun `passenger coordination sends closed code then reloads backend message`() = runBlocking {
        val rides = CoordinatingPassengerRideGateway()
        val coordinator = MobileAppCoordinator(
            AppRole.PASSENGER,
            passengerAuthentication(),
            rides = rides,
        )

        val state = assertIs<AppUiState.PassengerReady>(
            coordinator.sendRideCoordinationMessage(
                "ride-coordinate",
                RideCoordinationCode.PASSENGER_AT_PICKUP,
            ),
        )

        assertEquals(RideCoordinationCode.PASSENGER_AT_PICKUP, rides.sentCode)
        assertEquals(
            RideCoordinationCode.PASSENGER_AT_PICKUP,
            state.latestCoordinationMessage?.code,
        )
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
    fun `manual transfer selection is sent to the ride gateway`() = runBlocking {
        val pickup = Coordinates(33.5731, -7.5898)
        val destination = Coordinates(33.5899, -7.6039)
        val rides = RequestedPassengerRideGateway(pickup, destination)
        val coordinator = MobileAppCoordinator(
            AppRole.PASSENGER,
            passengerAuthentication(),
            rides = rides,
        )

        coordinator.requestRide(pickup, destination, RidePaymentMethod.MANUAL_TRANSFER)

        assertEquals(RidePaymentMethod.MANUAL_TRANSFER, rides.requestedPaymentMethod)
    }

    @Test
    fun `transfer submission refreshes a still-pending authoritative receipt`() = runBlocking {
        val rides = ManualTransferPassengerGateway()
        val coordinator = MobileAppCoordinator(
            AppRole.PASSENGER,
            passengerAuthentication(),
            rides = rides,
        )

        val state = assertIs<AppUiState.PassengerReady>(
            coordinator.submitManualTransfer("ride-transfer", "BANK-123"),
        )

        assertEquals("BANK-123", rides.submittedReference)
        assertEquals("PROCESSING", state.latestCompletedReceipt?.paymentStatus)
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

    @Test
    fun `safety submission is trimmed and refreshes participant safe history`() = runBlocking {
        val safety = RecordingSafetyGateway()
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = passengerAuthentication(),
            rides = PassengerHistoryDetailGateway(),
            safety = safety,
        )

        val state = assertIs<AppUiState.PassengerReady>(
            coordinator.createSafetyReport(
                rideId = "ride-history",
                category = SafetyCategory.UNSAFE_DRIVING,
                description = "  The driver repeatedly crossed the center line.  ",
            )
        )

        assertEquals(
            Triple(
                "ride-history",
                SafetyCategory.UNSAFE_DRIVING,
                "The driver repeatedly crossed the center line.",
            ),
            safety.created,
        )
        assertEquals("report-1", state.safetyReports.single().id)
        assertEquals("We received your report.", state.safetyReports.single().latestPublicMessage)
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
    var requestedOnlineMarket: Pair<String?, String>? = null

    override suspend fun apply(displayName: String) = error("Not used")
    override suspend fun profile() = DriverApplication("Driver", "APPROVED", "ACTIVE")
    override suspend fun verificationStatus() = "APPROVED"
    override suspend fun submitVerification() = error("Not used")
    override suspend fun currentAvailability() = DriverAvailability(DriverAvailabilityStatus.OFFLINE, "vehicle")
    override suspend fun goOnline(cityId: String?, serviceType: String): DriverAvailability {
        requestedOnlineMarket = cityId to serviceType
        return DriverAvailability(DriverAvailabilityStatus.AVAILABLE, "vehicle", cityId, serviceType)
    }
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

private class RecordingPlaceDiscoveryGateway(
    private val place: PlaceResult,
) : PlaceDiscoveryGateway {
    var searchQuery: String? = null
    var reverseCoordinate: Coordinates? = null
    private val attribution = PlaceAttribution(
        "© OpenStreetMap contributors",
        "https://www.openstreetmap.org/copyright",
    )

    override suspend fun search(cityId: String, query: String): PlaceSearch {
        searchQuery = query
        return PlaceSearch(cityId, query.trim(), listOf(place), attribution)
    }

    override suspend fun reverse(cityId: String, coordinate: Coordinates): ReversePlace {
        reverseCoordinate = coordinate
        return ReversePlace(cityId, place, attribution)
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

private class CoordinatingPassengerRideGateway : RideGateway {
    var sentCode: RideCoordinationCode? = null
    private var latest: RideCoordinationMessage? = null

    override suspend fun sendCoordinationMessage(
        id: String,
        code: RideCoordinationCode,
    ): RideCoordinationMessage {
        sentCode = code
        return RideCoordinationMessage(
            id = "message-coordinate",
            rideId = id,
            senderRole = RideCoordinationSenderRole.PASSENGER,
            code = code,
            createdAt = "2026-09-03T10:15:00Z",
        ).also { latest = it }
    }

    override suspend fun listRides() = listOf(
        RideSummary("ride-coordinate", RideStatus.ACCEPTED),
    )

    override suspend fun currentRide(id: String) = RideSummary(
        id = id,
        status = RideStatus.ACCEPTED,
        pickup = Coordinates(33.5731, -7.5898),
        destination = Coordinates(33.5890, -7.5910),
        latestCoordinationMessage = latest,
    )

    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = error("Not used")
    override suspend fun finalFare(id: String): FinalRideFare = error("Not used")
    override suspend fun receipt(id: String): RideReceipt = error("Not used")
    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary = error("Not used")
    override suspend fun cancelRide(id: String, reason: String): RideSummary = error("Not used")
    override suspend fun ratings(id: String): List<RideRating> = emptyList()
    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = error("Not used")
}

private class RequestedPassengerRideGateway(
    private val pickup: Coordinates,
    private val destination: Coordinates,
) : RideGateway {
    var requestedTrip: Pair<Coordinates, Coordinates>? = null
    var requestedPaymentMethod: RidePaymentMethod? = null

    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary {
        return requestRide(pickup, destination, RidePaymentMethod.CASH)
    }

    override suspend fun requestRide(
        pickup: Coordinates,
        destination: Coordinates,
        paymentMethod: RidePaymentMethod,
    ): RideSummary {
        requestedTrip = pickup to destination
        requestedPaymentMethod = paymentMethod
        return RideSummary(
            "ride",
            RideStatus.MATCHING,
            pickup = pickup,
            destination = destination,
            paymentMethod = paymentMethod,
        )
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

private class ManualTransferPassengerGateway : RideGateway {
    var submittedReference: String? = null
    private val summary = RideSummary(
        id = "ride-transfer",
        status = RideStatus.COMPLETED,
        completedAt = "2026-08-23T12:00:00Z",
        paymentMethod = RidePaymentMethod.MANUAL_TRANSFER,
    )

    override suspend fun listRides() = listOf(summary)
    override suspend fun ratings(id: String): List<RideRating> = emptyList()
    override suspend fun receipt(id: String) = RideReceipt(
        rideId = id,
        completedAt = summary.completedAt!!,
        fare = FinalRideFare("42.00", "MAD"),
        paymentMethod = "MANUAL_TRANSFER",
        paymentStatus = "PROCESSING",
        manualTransfer = ManualTransferInstructions(
            recipientName = "TaxiMobile Pilot",
            bankAccount = "ACCOUNT-123",
            walletId = null,
            paymentReference = "TM-REFERENCE-123",
        ),
    )
    override suspend fun submitManualTransfer(id: String, payerReference: String?): RideReceipt {
        submittedReference = payerReference
        return receipt(id)
    }
    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates): FareEstimate = error("Not used")
    override suspend fun currentRide(id: String): RideSummary = summary
    override suspend fun finalFare(id: String): FinalRideFare = error("Not used")
    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary = error("Not used")
    override suspend fun cancelRide(id: String, reason: String): RideSummary = error("Not used")
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

private fun applicantAuthentication() = AuthenticationSessionCoordinator(
    gateway = object : AuthenticationGateway {
        override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
        override suspend fun login(identifier: String, password: String, deviceLabel: String?) = unusedTokens()
        override suspend fun refresh(refreshToken: String) = unusedTokens()
        override suspend fun logout(accessToken: String) = Unit
        override suspend fun currentAccount(accessToken: String) =
            CurrentAccount("applicant", setOf(AccountRole.PASSENGER), "Applicant")
    },
    tokenStore = object : SecureTokenStore {
        override suspend fun tokens() = StoredTokens("access", "refresh")
        override suspend fun save(accessToken: String, refreshToken: String) = Unit
        override suspend fun clear() = Unit
    },
)

private fun unusedTokens() = SessionTokens(accessToken = "unused", refreshToken = "unused")

private class RecordingRecruitmentGateway(
    initialApplication: DriverCityApplication? = null,
    private val failCatalog: Boolean = false,
) : DriverRecruitmentGateway {
    private var currentApplication = initialApplication
    var lastExpectedVersion: Int? = null
    var lastAnswers: List<DriverApplicationAnswerDraft> = emptyList()
    var lastDocumentApplicationId: String? = null
    var lastDocumentRequirementItemId: String? = null
    var lastDocumentUpload: DriverDocumentUpload? = null
    var lastDeletedDocumentId: String? = null

    override suspend fun recruitingCities() =
        if (failCatalog) throw ApiRequestException(503, "Catalog unavailable")
        else listOf(recruitingCity())

    override suspend fun applications(): List<DriverCityApplicationSummary> =
        currentApplication?.let { listOf(it.toSummary()) }.orEmpty()

    override suspend fun application(applicationId: String): DriverCityApplication =
        currentApplication?.takeIf { it.id == applicationId } ?: error("Unknown application")

    override suspend fun createApplication(cityId: String, displayName: String?): DriverCityApplication =
        draftCityApplication().also { currentApplication = it }

    override suspend fun updateApplication(
        applicationId: String,
        expectedVersion: Int,
        answers: List<DriverApplicationAnswerDraft>,
        evidence: List<DriverApplicationEvidenceDraft>,
        removeAnswerItemIds: List<String>,
        removeEvidenceItemIds: List<String>,
    ): DriverCityApplication {
        lastExpectedVersion = expectedVersion
        lastAnswers = answers
        return application(applicationId).copy(optimisticVersion = expectedVersion + 1)
            .also { currentApplication = it }
    }

    override suspend fun submitApplication(applicationId: String): DriverCityApplication =
        application(applicationId).copy(status = "SUBMITTED", editable = false)
            .also { currentApplication = it }

    override suspend fun withdrawApplication(applicationId: String): DriverCityApplication =
        application(applicationId).copy(status = "WITHDRAWN", editable = false)
            .also { currentApplication = it }

    override suspend fun uploadDocument(
        applicationId: String,
        requirementItemId: String,
        expectedVersion: Int,
        document: DriverDocumentUpload,
    ): DriverCityApplication {
        lastDocumentApplicationId = applicationId
        lastDocumentRequirementItemId = requirementItemId
        lastExpectedVersion = expectedVersion
        lastDocumentUpload = document
        return application(applicationId)
            .copy(optimisticVersion = expectedVersion + 1, complete = true)
            .also { currentApplication = it }
    }

    override suspend fun deleteDocument(
        applicationId: String,
        documentId: String,
        expectedVersion: Int,
    ): DriverCityApplication {
        lastDocumentApplicationId = applicationId
        lastDeletedDocumentId = documentId
        lastExpectedVersion = expectedVersion
        return application(applicationId)
            .copy(optimisticVersion = expectedVersion + 1, complete = false)
            .also { currentApplication = it }
    }
}

private fun recruitingCity() = RecruitingCity(
    id = "city-casablanca",
    code = "CASABLANCA",
    name = RecruitmentCopy("Casablanca", "Casablanca", "الدار البيضاء"),
    timezone = "Africa/Casablanca",
    lifecycleStatus = "RECRUITING",
    requirementVersionId = "requirements-v1",
    requirementVersion = "1",
)

private fun draftCityApplication() = DriverCityApplication(
    id = "application",
    driverId = "driver",
    cityId = "city-casablanca",
    cityCode = "CASABLANCA",
    cityName = RecruitmentCopy("Casablanca", "Casablanca", "الدار البيضاء"),
    requirementVersionId = "requirements-v1",
    requirementVersion = "1",
    status = "NOT_STARTED",
    optimisticVersion = 7,
    submissionRevision = 0,
    editable = true,
    complete = false,
    missingRequiredItemIds = setOf("requirement-name"),
    documentUploadAvailable = false,
    submittedAt = null,
    reviewedAt = null,
    withdrawnAt = null,
    updatedAt = "2026-08-24T12:00:00Z",
    requirements = emptyList(),
    answers = emptyList(),
    evidence = emptyList(),
    documents = emptyList(),
    latestDecision = null,
    authorization = null,
)

private fun approvedCityApplication() = draftCityApplication().copy(
    status = "APPROVED",
    editable = false,
    complete = true,
    missingRequiredItemIds = emptySet(),
    authorization = DriverCityAuthorization(
        id = "authorization",
        cityId = "city-casablanca",
        status = "ACTIVE",
        vehicleId = "vehicle",
        serviceTypes = listOf("ON_DEMAND", "FIXED_ROUTE"),
        scheduledOffersEnabled = false,
        validFrom = "2026-08-24T12:00:00Z",
        validUntil = null,
    ),
)

private fun DriverCityApplication.toSummary() = DriverCityApplicationSummary(
    id = id,
    cityId = cityId,
    cityCode = cityCode,
    cityName = cityName,
    requirementVersionId = requirementVersionId,
    requirementVersion = requirementVersion,
    status = status,
    optimisticVersion = optimisticVersion,
    submittedAt = submittedAt,
    reviewedAt = reviewedAt,
    updatedAt = updatedAt,
    latestApplicantMessage = latestDecision?.message,
)

private class RecordingNotificationGateway : NotificationGateway {
    var revoked: Pair<String, DevicePlatform>? = null

    override suspend fun list(): List<AppNotification> = emptyList()
    override suspend fun markRead(id: String): AppNotification = error("Not used")
    override suspend fun registerDevice(registrationId: String, platform: DevicePlatform) = Unit
    override suspend fun unregisterDevice(registrationId: String, platform: DevicePlatform) {
        revoked = registrationId to platform
    }
}

private class RecordingSafetyGateway : SafetyGateway {
    var created: Triple<String, SafetyCategory, String>? = null

    override suspend fun createReport(rideId: String, category: SafetyCategory, description: String) {
        created = Triple(rideId, category, description)
    }

    override suspend fun reports() = listOf(
        SafetyReport(
            id = "report-1",
            rideId = "ride-history",
            category = SafetyCategory.UNSAFE_DRIVING,
            status = "SUBMITTED",
            createdAt = "2026-08-24T12:00:00Z",
            latestPublicMessage = "We received your report.",
        )
    )
}

private class RecordingAccountSecurityGateway(
    private val networkFailure: Boolean = false,
    private val activeSessions: List<AccountSession> = emptyList(),
    private val revokesCurrentSession: Boolean = false,
) : AccountSecurityGateway {
    var identifier: String? = null
    var currentPassword: String? = null

    override suspend fun resetPassword(
        identifier: String,
        recoveryCode: String,
        newPassword: String,
    ) {
        if (networkFailure) throw AuthenticationNetworkException()
        this.identifier = identifier
    }

    override suspend fun recoveryCodes(currentPassword: String): AccountRecoveryCodes {
        this.currentPassword = currentPassword
        return AccountRecoveryCodes(listOf("23456-789AB-CDEFG-HJKLM"), "expiry")
    }

    override suspend fun sessions(): List<AccountSession> = activeSessions

    override suspend fun revokeSession(sessionId: String) =
        AccountSessionRevocation(currentSession = revokesCurrentSession)

    override suspend fun changePassword(currentPassword: String, newPassword: String) = Unit
}
