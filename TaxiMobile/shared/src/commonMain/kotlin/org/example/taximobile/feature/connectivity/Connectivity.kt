package org.example.taximobile.feature.connectivity

import kotlinx.coroutines.flow.StateFlow
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.app.hasAuthenticatedSession
import org.example.taximobile.feature.ui.text.UiMessage

/**
 * Coarse platform connectivity signal. This is deliberately not an API-health
 * signal and must never be used as evidence that a command reached the backend.
 */
enum class ConnectivityStatus {
    UNKNOWN,
    AVAILABLE,
    UNAVAILABLE,
}

/** A lifecycle-owned stream implemented with each platform's native monitor. */
interface ConnectivityObserver {
    val status: StateFlow<ConnectivityStatus>

    fun close()
}

/**
 * Emits one recovery request only for a real unavailable-to-available edge.
 * Initial availability and repeated native callbacks do not duplicate the
 * application's normal startup restore.
 */
class ConnectivityRecoveryPolicy {
    private var previous = ConnectivityStatus.UNKNOWN

    fun shouldRefresh(current: ConnectivityStatus): Boolean {
        if (current == ConnectivityStatus.UNKNOWN) return false
        val shouldRefresh = previous == ConnectivityStatus.UNAVAILABLE &&
            current == ConnectivityStatus.AVAILABLE
        previous = current
        return shouldRefresh
    }
}

/**
 * Arms one authoritative refresh only after the application has actually been
 * backgrounded. The initial foreground event and duplicate lifecycle events do
 * not duplicate normal startup restoration.
 */
class ForegroundRecoveryPolicy {
    private var backgroundObserved = false

    fun onBackground() {
        backgroundObserved = true
    }

    fun shouldRefreshOnForeground(): Boolean {
        if (!backgroundObserved) return false
        backgroundObserved = false
        return true
    }
}

/**
 * Separates renderable backend-confirmed state from a subsequent connection
 * failure. Irreversible commands are never queued or represented as successful.
 */
data class AppStatePresentation(
    val state: AppUiState,
    val connectionIssue: UiMessage? = null,
) {
    fun accept(candidate: AppUiState): AppStatePresentation {
        return if (candidate is AppUiState.Offline && state.hasAuthenticatedSession()) {
            copy(connectionIssue = candidate.message)
        } else {
            AppStatePresentation(candidate)
        }
    }

    /**
     * Executes an authenticated UI action exactly once. When its result cannot
     * prove the command's outcome, one read-only restore reconciles the UI with
     * backend truth. The original operation error remains visible after a
     * successful restore, while an expired session always wins and signs out.
     *
     * [restore] must only read current state. It must never replay [action].
     */
    suspend fun performAuthenticatedAction(
        action: suspend () -> AppUiState,
        restore: suspend () -> AppUiState,
        onBackendConfirmed: (AppUiState) -> Unit = {},
    ): AppStatePresentation {
        val result = action()
        if (result !is AppUiState.Offline || !state.hasAuthenticatedSession()) {
            if (result !is AppUiState.Offline && result !is AppUiState.SignedOut) {
                onBackendConfirmed(result)
            }
            return accept(result)
        }

        val reconciled = accept(restore())
        return if (reconciled.state.hasAuthenticatedSession()) {
            reconciled.copy(connectionIssue = result.message)
        } else {
            reconciled
        }
    }
}
