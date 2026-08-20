package org.example.taximobile.feature.auth

import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.domain.auth.CurrentAccount
import taximobile.shared.generated.resources.*

class AuthenticationStateTest {
    private val account = CurrentAccount(id = "user", roles = emptySet(), displayName = "Passenger")

    @Test
    fun network_failure_does_not_log_out_an_authenticated_account() {
        val state = AuthenticationState.Authenticated(account)

        assertEquals(state, reduceAuthenticationState(state, AuthenticationEvent.NetworkUnavailable))
    }

    @Test
    fun refresh_rejection_removes_the_authenticated_session() {
        assertEquals(
            AuthenticationState.Unauthenticated,
            reduceAuthenticationState(AuthenticationState.Refreshing(account), AuthenticationEvent.RefreshRejected),
        )
    }

    @Test
    fun registration_failures_have_actionable_safe_messages() {
        assertEquals(
            Res.string.message_registration_conflict,
            registrationFailureMessage(409).resource,
        )
        assertEquals(
            Res.string.message_registration_invalid,
            registrationFailureMessage(422).resource,
        )
        assertEquals(
            Res.string.message_registration_rate_limited,
            registrationFailureMessage(429).resource,
        )
        assertEquals(
            Res.string.message_registration_failed,
            registrationFailureMessage(500).resource,
        )
    }
}
