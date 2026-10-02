package org.example.taximobile.feature.realtime

import kotlin.random.Random
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.coroutines.selects.select
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.domain.realtime.LiveEventGateway
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.auth.LocalSessionLifetime
import org.example.taximobile.feature.connectivity.ConnectivityStatus

/** Foreground hints are optional; retained render state is not subscription authority. */
fun canListenForLiveUpdates(
    state: AppUiState,
    foreground: Boolean,
    connectivity: ConnectivityStatus,
    pendingAction: AppAction?,
): Boolean = foreground && connectivity != ConnectivityStatus.UNAVAILABLE &&
    pendingAction?.kind !in setOf(
        AppActionKind.LOGOUT, AppActionKind.REVOKE_ACCOUNT_SESSION, AppActionKind.CHANGE_ACCOUNT_PASSWORD,
    ) &&
    (state is AppUiState.PassengerReady || state is AppUiState.DriverReady)

/**
 * One process-owned, cancellable subscription with credential-generation ownership.
 *
 * Platforms own foreground/network admission. This layer owns reconnect and
 * session replacement. Every connection catches up through REST *after* socket
 * admission, closing the lost-hint window between a pre-connect read and LISTEN.
 * A disconnect also requests REST recovery (including access-token refresh).
 * Neither callback acknowledges, queues or replays a business command.
 */
class LiveUpdateSubscription(
    private val gateway: LiveEventGateway,
    private val lifetime: StateFlow<LocalSessionLifetime>,
    private val retryPolicy: () -> LiveUpdateRetryPolicy = { LiveUpdateRetryPolicy() },
    private val connectTimeoutMillis: Long = 10_000,
    private val refreshTimeoutMillis: Long = 15_000,
    private val waitForRetry: suspend (Long) -> Unit = { delay(it) },
) {
    init { require(connectTimeoutMillis > 0 && refreshTimeoutMillis > 0) }
    private val ownership = Mutex()

    suspend fun run(onRefresh: suspend () -> Unit): Unit = ownership.withLock {
        lifetime.collectLatest { owner ->
            if (!owner.active) return@collectLatest
            val retry = retryPolicy()
            suspend fun refreshIfOwned() {
                currentCoroutineContext().ensureActive()
                if (lifetime.value != owner) return
                // A stalled REST read must not wedge all later hints. Only our
                // timeout is absorbed; cancellation of the owner still propagates.
                withTimeoutOrNull(refreshTimeoutMillis) { onRefresh() }
                currentCoroutineContext().ensureActive()
            }
            while (lifetime.value == owner) {
                currentCoroutineContext().ensureActive()
                try {
                    listenOnce(
                        onConnected = { refreshIfOwned() },
                        onRideEvent = {
                            refreshIfOwned()
                            // A delivered hint proves useful recovery; mere
                            // handshake/instant close must not reset flapping backoff.
                            retry.reset()
                        },
                    )
                } catch (error: CancellationException) {
                    throw error
                } catch (_: AuthenticationRejectedException) {
                    // REST owns credential refresh/revocation, never the socket.
                } catch (_: AuthenticationNetworkException) {
                    // Keep the last REST-confirmed UI while transport recovers.
                }
                refreshIfOwned()
                if (lifetime.value != owner) break
                waitForRetry(retry.nextDelayMillis())
            }
        }
    }

    private suspend fun listenOnce(
        onConnected: suspend () -> Unit,
        onRideEvent: suspend (org.example.taximobile.domain.realtime.LiveRideEvent) -> Unit,
    ) = coroutineScope {
        val admitted = CompletableDeferred<Unit>()
        val socket = async {
            gateway.listen(
                onConnected = { admitted.complete(Unit); onConnected() },
                onRideEvent = onRideEvent,
            )
        }
        try {
            val handshakeFinished = withTimeoutOrNull(connectTimeoutMillis) {
                select {
                    admitted.onAwait { true }
                    socket.onAwait { true } // failed or normally closed before admission
                }
            }
            if (handshakeFinished == null) throw AuthenticationNetworkException()
            socket.await() // A healthy idle socket has no artificial lifetime limit.
        } finally {
            socket.cancelAndJoin()
        }
    }
}

/** Bounded exponential jitter avoids synchronized fleet-wide retry storms. */
class LiveUpdateRetryPolicy(
    private val initialMillis: Long = 1_000,
    private val maximumMillis: Long = 30_000,
    private val chooseDelay: (Long, Long) -> Long = { minimum, maximum ->
        Random.nextLong(minimum, maximum + 1)
    },
) {
    init {
        require(initialMillis >= 2 && maximumMillis >= initialMillis && maximumMillis < Long.MAX_VALUE)
    }
    private var ceiling = initialMillis

    fun nextDelayMillis(): Long {
        val minimum = ceiling / 2
        val chosen = chooseDelay(minimum, ceiling)
        require(chosen in minimum..ceiling) { "Retry delay is outside the bounded jitter interval" }
        ceiling = if (ceiling >= maximumMillis / 2) maximumMillis else ceiling * 2
        return chosen
    }

    fun reset() { ceiling = initialMillis }
}
