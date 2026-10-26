package org.example.taximobile.feature.app

import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import org.example.taximobile.app.AppRole
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.domain.auth.AccountRole
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import org.example.taximobile.domain.rides.*
import org.example.taximobile.domain.scheduling.*
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNull

/** Real coordinator boundary, with explicitly simulated transport/credentials. */
class QuoteSessionRecoveryTest {
    @Test fun point_quote_survives_catch_up_with_fresh_server_amount_without_a_ride_command() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.app.estimateRide(PICKUP, DESTINATION)
        f.rides.amount = "37.00"
        val restored = assertIs<AppUiState.PassengerReady>(f.app.restore())
        assertEquals("37.00", restored.fareEstimate?.amount)
        assertEquals(PICKUP to DESTINATION, restored.reviewedPointQuoteInput)
        assertEquals(2, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun fixed_quote_survives_catch_up_for_its_selected_direction() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.app.estimateFixedRoute("reviewed-direction")
        f.rides.amount = "38.00"
        val restored = assertIs<AppUiState.PassengerReady>(f.app.restore())
        assertEquals("reviewed-direction", restored.selectedFixedRouteDirectionId)
        assertNull(restored.reviewedPointQuoteInput)
        assertEquals(RideServiceType.FIXED_ROUTE, restored.fareEstimate?.serviceType)
        assertEquals("38.00", restored.fareEstimate?.amount)
        assertEquals(2, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun quote_catch_up_rotates_rejected_access_once_without_replaying_a_ride_command() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.app.estimateRide(PICKUP, DESTINATION)
        f.rides.rejectQuoteOnce = true
        val restored = assertIs<AppUiState.PassengerReady>(f.app.restore())
        assertEquals("35.00", restored.fareEstimate?.amount)
        assertEquals(PICKUP to DESTINATION, restored.reviewedPointQuoteInput)
        assertEquals(1, f.auth.refreshes)
        assertEquals(3, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun token_rotation_keeps_selected_history_under_the_same_credential_owner() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.rides.history = listOf(RideSummary("past-trip", RideStatus.COMPLETED, "2026-10-19T10:00:00Z"))
        f.app.loadPassengerRideHistoryDetail("past-trip")
        f.auth.expired = true
        val restored = assertIs<AppUiState.PassengerReady>(f.app.restore())
        assertEquals("past-trip", restored.selectedHistoryRide?.id)
        assertEquals("COMPLETED", restored.selectedHistoryReceipt?.paymentStatus)
        assertEquals(1, f.auth.refreshes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun a_new_primary_ride_discards_old_quote_inputs_without_requoting() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.app.estimateRide(PICKUP, DESTINATION)
        f.rides.history = listOf(RideSummary("new-primary", RideStatus.MATCHING))
        val restored = assertIs<AppUiState.PassengerReady>(f.app.restore())
        assertEquals("new-primary", restored.activeRideId)
        assertNull(restored.reviewedPointQuoteInput)
        assertNull(restored.fareEstimate)
        assertEquals(1, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun rejected_quote_catch_up_is_explicit_and_forgets_the_denied_inputs() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.app.estimateRide(PICKUP, DESTINATION)
        f.rides.quoteFailure = ApiRequestException(403, "Market access withdrawn")
        assertIs<AppUiState.Offline>(f.app.restore())
        assertEquals(2, f.rides.quotes)
        val next = assertIs<AppUiState.PassengerReady>(f.app.restore())
        assertNull(next.fareEstimate)
        assertEquals(2, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun signing_back_in_does_not_restore_the_previous_session_quote() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.app.estimateRide(PICKUP, DESTINATION)
        f.app.logout()
        val signedIn = assertIs<AppUiState.PassengerReady>(f.app.login("passenger", "test-password", null))
        assertNull(signedIn.fareEstimate)
        assertNull(signedIn.reviewedPointQuoteInput)
        assertEquals(1, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun a_quote_response_finishing_after_logout_cannot_install_reviewed_terms() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        lateinit var logout: Job
        // Stage session end immediately, then let the owned advisory read
        // release its non-reentrant credential mutex before logout finishes.
        f.rides.onQuote = { logout = launch(start = CoroutineStart.UNDISPATCHED) { f.app.logout() } }
        assertIs<AppUiState.SignedOut>(f.app.estimateRide(PICKUP, DESTINATION))
        logout.join()
        f.rides.onQuote = null
        assertNull(assertIs<AppUiState.PassengerReady>(f.app.login("passenger", "test-password", null)).fareEstimate)
        assertEquals(1, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun point_quote_refreshes_before_read_and_preserves_backend_amounts() = runBlocking {
        val f = QuoteFixture()
        val state = assertIs<AppUiState.PassengerReady>(f.app.estimateRide(PICKUP, DESTINATION))
        assertEquals("35.00", state.fareEstimate?.amount)
        assertEquals(PICKUP to DESTINATION, state.reviewedPointQuoteInput)
        assertEquals(listOf(RidePaymentMethod.CASH), state.fareEstimate?.paymentMethods)
        assertEquals(1, f.auth.refreshes)
        assertEquals(1, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun fixed_quote_refreshes_without_creating_a_ride() = runBlocking {
        val f = QuoteFixture()
        val state = assertIs<AppUiState.PassengerReady>(f.app.estimateFixedRoute("direction"))
        assertEquals("direction", state.selectedFixedRouteDirectionId)
        assertEquals("35.00", state.fareEstimate?.amount)
        assertEquals(1, f.auth.refreshes)
        assertEquals(1, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun scheduled_point_quote_refreshes_without_submitting_booking() = runBlocking {
        val f = QuoteFixture()
        val state = assertIs<AppUiState.PassengerReady>(
            f.app.estimateScheduledPointToPoint(SCHEDULED_FOR, "city", PICKUP, DESTINATION),
        )
        assertEquals(SCHEDULED_FOR, state.scheduledBookingEstimate?.scheduledFor)
        assertEquals("40.00", state.scheduledBookingEstimate?.economics?.passengerTotal)
        assertEquals(1, f.auth.refreshes)
        assertEquals(1, f.scheduling.quotes)
        assertEquals(0, f.scheduling.commands)
    }

    @Test fun scheduled_fixed_quote_refreshes_without_submitting_booking() = runBlocking {
        val f = QuoteFixture()
        val state = assertIs<AppUiState.PassengerReady>(
            f.app.estimateScheduledFixedRoute(SCHEDULED_FOR, "direction"),
        )
        assertEquals("direction", state.scheduledBookingEstimate?.fixedRouteDirectionVersionId)
        assertEquals(1, f.auth.refreshes)
        assertEquals(1, f.scheduling.quotes)
        assertEquals(0, f.scheduling.commands)
    }

    @Test fun quote_rejected_after_preflight_is_retried_once_with_rotated_access() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.rides.rejectQuoteOnce = true
        assertIs<AppUiState.PassengerReady>(f.app.estimateRide(PICKUP, DESTINATION))
        assertEquals(1, f.auth.refreshes)
        assertEquals(2, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun product_reload_401_is_not_swallowed_as_final_sign_out() = runBlocking {
        val f = QuoteFixture(initiallyExpired = false)
        f.rides.rejectListOnce = true
        val state = assertIs<AppUiState.PassengerReady>(f.app.estimateRide(PICKUP, DESTINATION))
        assertEquals("35.00", state.fareEstimate?.amount)
        assertEquals(1, f.auth.refreshes)
        assertEquals(2, f.rides.quotes)
        assertEquals(2, f.rides.lists)
        assertEquals(0, f.rides.commands)
    }

    @Test fun revoked_refresh_prevents_quotes_and_clears_credentials() = runBlocking {
        val f = QuoteFixture()
        f.auth.revoked = true
        assertIs<AppUiState.SignedOut>(f.app.estimateRide(PICKUP, DESTINATION))
        assertNull(f.store.value)
        assertEquals(1, f.auth.refreshes)
        assertEquals(0, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun unavailable_refresh_is_offline_not_logout_and_does_not_quote() = runBlocking {
        val f = QuoteFixture()
        f.auth.unavailable = true
        assertIs<AppUiState.Offline>(f.app.estimateRide(PICKUP, DESTINATION))
        assertEquals(StoredTokens("old-access", "old-refresh"), f.store.value)
        assertEquals(0, f.rides.quotes)
        assertEquals(0, f.rides.commands)
    }

    @Test fun rejected_ride_and_fixed_route_commands_are_never_replayed() = runBlocking {
        for (fixed in listOf(false, true)) {
            val f = QuoteFixture()
            val state = if (fixed) f.app.requestFixedRoute("direction", RidePaymentMethod.CASH)
                else f.app.requestRide(PICKUP, DESTINATION, RidePaymentMethod.CASH)
            assertIs<AppUiState.SignedOut>(state)
            assertEquals(1, f.rides.commands)
            assertEquals(0, f.auth.refreshes)
            assertEquals(0, f.rides.quotes)
        }
    }

    @Test fun rejected_scheduled_commands_are_never_replayed() = runBlocking {
        for (fixed in listOf(false, true)) {
            val f = QuoteFixture()
            val state = if (fixed) f.app.scheduleFixedRoute(SCHEDULED_FOR, "direction", null, scheduleEstimate("direction"))
                else f.app.schedulePointToPoint(SCHEDULED_FOR, "city", PICKUP, DESTINATION, null, scheduleEstimate(null))
            assertIs<AppUiState.SignedOut>(state)
            assertEquals(1, f.scheduling.commands)
            assertEquals(0, f.auth.refreshes)
            assertEquals(0, f.scheduling.quotes)
        }
    }

    @Test fun rejected_transfer_command_is_never_replayed() = runBlocking {
        val f = QuoteFixture()
        assertIs<AppUiState.SignedOut>(f.app.submitManualTransfer("ride", "synthetic-reference"))
        assertEquals(1, f.rides.commands)
        assertEquals(0, f.auth.refreshes)
    }
}

private class QuoteFixture(initiallyExpired: Boolean = true) {
    val store = QuoteStore()
    val auth = QuoteAuth().apply { expired = initiallyExpired }
    val rides = QuoteRides(store, auth)
    val scheduling = QuoteScheduling(store, auth)
    val app = MobileAppCoordinator(
        AppRole.PASSENGER, AuthenticationSessionCoordinator(auth, store),
        rides = rides, scheduling = scheduling,
    )
}

private class QuoteStore : SecureTokenStore {
    var value: StoredTokens? = StoredTokens("old-access", "old-refresh")
    override suspend fun tokens() = value
    override suspend fun save(accessToken: String, refreshToken: String) { value = StoredTokens(accessToken, refreshToken) }
    override suspend fun clear() { value = null }
}

private class QuoteAuth : AuthenticationGateway {
    var expired = true
    var revoked = false
    var unavailable = false
    var refreshes = 0
    override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
    override suspend fun login(identifier: String, password: String, deviceLabel: String?) = SessionTokens("new-access", "new-refresh")
    override suspend fun logout(accessToken: String) = Unit
    override suspend fun refresh(refreshToken: String): SessionTokens {
        refreshes++
        if (unavailable) throw AuthenticationNetworkException()
        if (revoked) throw AuthenticationRejectedException()
        return SessionTokens("new-access", "new-refresh")
    }
    override suspend fun currentAccount(accessToken: String): CurrentAccount {
        if (expired && accessToken == "old-access") throw AuthenticationRejectedException()
        return CurrentAccount("passenger", setOf(AccountRole.PASSENGER), "Synthetic passenger")
    }
}

private class QuoteRides(private val store: QuoteStore, private val auth: QuoteAuth) : RideGateway {
    var quotes = 0
    var lists = 0
    var commands = 0
    var rejectQuoteOnce = false
    var rejectListOnce = false
    var amount = "35.00"
    var quoteFailure: ApiRequestException? = null
    var onQuote: (suspend () -> Unit)? = null
    var history: List<RideSummary> = emptyList()
    private fun requireAccess() {
        if (auth.expired && store.value?.accessToken == "old-access") throw AuthenticationRejectedException()
    }
    private suspend fun quote(): FareEstimate {
        quotes++
        quoteFailure?.let { throw it }
        onQuote?.invoke()
        if (rejectQuoteOnce) { rejectQuoteOnce = false; auth.expired = true; throw AuthenticationRejectedException() }
        requireAccess()
        return FareEstimate(amount, "MAD", "server-rule", listOf(RidePaymentMethod.CASH))
    }
    private fun rejectedCommand(): Nothing { commands++; throw AuthenticationRejectedException() }
    override suspend fun estimateRide(pickup: Coordinates, destination: Coordinates) = quote()
    override suspend fun estimateFixedRoute(directionVersionId: String) = quote().copy(serviceType = RideServiceType.FIXED_ROUTE)
    override suspend fun listRides(): List<RideSummary> {
        lists++
        if (rejectListOnce) { rejectListOnce = false; auth.expired = true; throw AuthenticationRejectedException() }
        requireAccess()
        return history
    }
    override suspend fun requestRide(pickup: Coordinates, destination: Coordinates): RideSummary = rejectedCommand()
    override suspend fun requestFixedRoute(directionVersionId: String, paymentMethod: RidePaymentMethod): RideSummary = rejectedCommand()
    override suspend fun submitManualTransfer(id: String, payerReference: String?): RideReceipt = rejectedCommand()
    override suspend fun currentRide(id: String): RideSummary = history.single { it.id == id }
    override suspend fun finalFare(id: String): FinalRideFare = error("No completed ride")
    override suspend fun receipt(id: String) = RideReceipt(id, "2026-10-19T10:00:00Z", FinalRideFare("35.00", "MAD"), "CASH", "COMPLETED")
    override suspend fun cancelRide(id: String, reason: String): RideSummary = error("Not used")
    override suspend fun ratings(id: String): List<RideRating> = emptyList()
    override suspend fun submitRating(id: String, score: Int, comment: String?): RideRating = error("Not used")
}

private class QuoteScheduling(private val store: QuoteStore, private val auth: QuoteAuth) : ScheduledBookingGateway {
    var quotes = 0
    var commands = 0
    private fun quote(direction: String?): ScheduledBookingEstimate {
        quotes++
        if (auth.expired && store.value?.accessToken == "old-access") throw AuthenticationRejectedException()
        return scheduleEstimate(direction)
    }
    private fun rejectedCommand(): Nothing { commands++; throw AuthenticationRejectedException() }
    override suspend fun passengerBookings(page: Int) = org.example.taximobile.domain.scheduling.ScheduledBookingPage(emptyList(), page, 20, 0)
    override suspend fun passengerBooking(bookingId: String): ScheduledBooking = error("Not used")
    override suspend fun estimatePointToPoint(scheduledFor: String, cityId: String?, pickup: Coordinates, destination: Coordinates) = quote(null)
    override suspend fun estimateFixedRoute(scheduledFor: String, directionVersionId: String) = quote(directionVersionId)
    override suspend fun createPointToPoint(scheduledFor: String, cityId: String?, pickup: Coordinates, destination: Coordinates, passengerNote: String?, reviewedEconomics: ScheduledEconomics): ScheduledBooking = rejectedCommand()
    override suspend fun createFixedRoute(scheduledFor: String, directionVersionId: String, passengerNote: String?, reviewedEconomics: ScheduledEconomics): ScheduledBooking = rejectedCommand()
    override suspend fun cancelPassengerBooking(bookingId: String, reason: String): ScheduledBooking = error("Not used")
    override suspend fun driverOffers(): List<ScheduledOffer> = emptyList()
    override suspend fun driverCommitments(): List<ScheduledCommitment> = emptyList()
    override suspend fun driverPreferences(): List<ScheduledOfferPreference> = emptyList()
    override suspend fun setDriverPreference(cityId: String, enabled: Boolean): ScheduledOfferPreference = error("Not used")
    override suspend fun acceptOffer(offerId: String): ScheduledCommitment = error("Not used")
    override suspend fun declineOffer(offerId: String, reason: String?): ScheduledOffer = error("Not used")
}

private val PICKUP = Coordinates(33.5731, -7.5898)
private val DESTINATION = Coordinates(33.5899, -7.6039)
private const val SCHEDULED_FOR = "2026-10-04T17:00:00Z"
private fun scheduleEstimate(direction: String?) = ScheduledBookingEstimate(
    "city", "operator", if (direction == null) "ON_DEMAND" else "FIXED_ROUTE", direction,
    SCHEDULED_FOR, "Africa/Casablanca", PICKUP, DESTINATION,
    ScheduledEconomics("35.00", "5.00", "0.00", "40.00", "40.00", "0.00", "MAD", "server-rule", "free", "schedule-policy"),
    ScheduledCancellationTerms(30, "FULL_BEFORE_CUTOFF", "Server cancellation terms"), "CASH",
)
