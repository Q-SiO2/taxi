package org.example.taximobile.feature.auth

import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.feature.ui.text.UiMessage
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_network_unavailable

sealed interface AuthenticationState {
    data object Restoring : AuthenticationState
    data object Unauthenticated : AuthenticationState
    data object Authenticating : AuthenticationState
    data class Authenticated(val account: CurrentAccount) : AuthenticationState
    data class Refreshing(val account: CurrentAccount) : AuthenticationState
    data class Failure(val message: UiMessage) : AuthenticationState
}

sealed interface AuthenticationEvent {
    data object RestoreSucceededWithoutSession : AuthenticationEvent
    data class LoginSucceeded(val account: CurrentAccount) : AuthenticationEvent
    data class LoginFailed(val message: UiMessage) : AuthenticationEvent
    data object RefreshStarted : AuthenticationEvent
    data object RefreshSucceeded : AuthenticationEvent
    data object RefreshRejected : AuthenticationEvent
    data object NetworkUnavailable : AuthenticationEvent
    data object LoggedOut : AuthenticationEvent
}

/** Pure reducer so UI state never becomes a substitute for backend authority. */
fun reduceAuthenticationState(
    state: AuthenticationState,
    event: AuthenticationEvent,
): AuthenticationState = when (event) {
    AuthenticationEvent.RestoreSucceededWithoutSession,
    AuthenticationEvent.LoggedOut,
    AuthenticationEvent.RefreshRejected -> AuthenticationState.Unauthenticated

    is AuthenticationEvent.LoginSucceeded -> AuthenticationState.Authenticated(event.account)
    is AuthenticationEvent.LoginFailed -> AuthenticationState.Failure(event.message)
    AuthenticationEvent.RefreshStarted -> when (state) {
        is AuthenticationState.Authenticated -> AuthenticationState.Refreshing(state.account)
        else -> state
    }
    AuthenticationEvent.RefreshSucceeded -> when (state) {
        is AuthenticationState.Refreshing -> AuthenticationState.Authenticated(state.account)
        else -> state
    }
    AuthenticationEvent.NetworkUnavailable -> when (state) {
        is AuthenticationState.Authenticated,
        is AuthenticationState.Refreshing -> state
        else -> AuthenticationState.Failure(UiMessage(Res.string.message_network_unavailable))
    }
}
