package org.example.taximobile.feature.realtime

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertTrue
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.yield
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.domain.realtime.LiveEventGateway
import org.example.taximobile.domain.realtime.LiveRideEvent
import org.example.taximobile.feature.app.AppAction
import org.example.taximobile.feature.app.AppActionKind
import org.example.taximobile.feature.app.AppUiState
import org.example.taximobile.feature.auth.LocalSessionLifetime
import org.example.taximobile.feature.connectivity.ConnectivityStatus
import org.example.taximobile.domain.drivers.DriverAvailabilityStatus

class LiveUpdateSubscriptionTest {
    @Test
    fun `unchanged ready owner retries failures and catches up after connection and hint`() = runBlocking {
        withTimeout(5_000) {
            val lifetime = MutableStateFlow(LocalSessionLifetime(1, true))
            val completed = CompletableDeferred<Unit>()
            val delays = mutableListOf<Long>()
            var attempts = 0
            var refreshes = 0
            val gateway = TestLiveGateway { connected, hint ->
                attempts++
                when (attempts) {
                    1 -> throw AuthenticationNetworkException()
                    2 -> throw AuthenticationRejectedException()
                    else -> {
                        connected()
                        hint(LiveRideEvent("ride.accepted", "synthetic-ride"))
                        completed.complete(Unit)
                        awaitCancellation()
                    }
                }
            }
            val subscription = LiveUpdateSubscription(gateway, lifetime, ::deterministicRetry) {
                delays += it
                yield()
            }
            val job = launch { subscription.run { refreshes++ } }
            try {
                completed.await()
                assertEquals(3, attempts)
                assertEquals(listOf(1_000L, 2_000L), delays)
                assertEquals(4, refreshes) // two failures, admission, then hint
                assertEquals(LocalSessionLifetime(1, true), lifetime.value)
            } finally { job.cancelAndJoin() }
            assertEquals(0, gateway.active)
        }
    }

    @Test
    fun `normal socket close is a retry with REST catch up and positive backoff`() = runBlocking {
        withTimeout(5_000) {
            val waiting = CompletableDeferred<Long>()
            var refreshes = 0
            val gateway = TestLiveGateway { connected, _ -> connected() }
            val subscription = LiveUpdateSubscription(
                gateway, MutableStateFlow(LocalSessionLifetime(1, true)), ::deterministicRetry,
            ) { delay -> waiting.complete(delay); awaitCancellation() }
            val job = launch { subscription.run { refreshes++ } }
            try {
                assertEquals(1_000L, waiting.await())
                assertEquals(2, refreshes)
                assertEquals(0, gateway.active)
            } finally { job.cancelAndJoin() }
        }
    }

    @Test
    fun `instant close grows backoff until a useful hint resets it`() = runBlocking {
        withTimeout(5_000) {
            val waiting = CompletableDeferred<Unit>()
            val delays = mutableListOf<Long>()
            var attempts = 0
            val gateway = TestLiveGateway { connected, hint ->
                attempts++
                connected()
                if (attempts == 4) hint(LiveRideEvent("ride.accepted", "synthetic"))
            }
            val subscription = LiveUpdateSubscription(
                gateway, MutableStateFlow(LocalSessionLifetime(1, true)), ::deterministicRetry,
            ) {
                delays += it
                if (delays.size == 4) { waiting.complete(Unit); awaitCancellation() }
                yield()
            }
            val job = launch { subscription.run {} }
            try {
                waiting.await()
                assertEquals(listOf(1_000L, 2_000L, 4_000L, 1_000L), delays)
                assertEquals(4, attempts)
                assertEquals(1, gateway.maximumActive)
                assertEquals(0, gateway.active)
            } finally { job.cancelAndJoin() }
        }
    }

    @Test
    fun `network and foreground return restart unchanged ready state without overlapping sockets`() = runBlocking {
        withTimeout(5_000) {
            // Model the same admission Boolean used by both native effects.
            // This is shared ownership evidence, not execution of native Compose.
            data class Admission(val foreground: Boolean, val network: ConnectivityStatus)
            val admission = MutableStateFlow(Admission(true, ConnectivityStatus.AVAILABLE))
            val connections = Channel<Unit>(Channel.UNLIMITED)
            val closed = Channel<Unit>(Channel.UNLIMITED)
            var refreshes = 0
            val gateway = TestLiveGateway { connected, _ ->
                try { connected(); connections.send(Unit); awaitCancellation() }
                finally { closed.send(Unit) }
            }
            val subscription = LiveUpdateSubscription(gateway, MutableStateFlow(LocalSessionLifetime(1, true)))
            val ready = AppUiState.PassengerReady()
            val job = launch {
                admission.collectLatest {
                    if (canListenForLiveUpdates(ready, it.foreground, it.network, null)) {
                        subscription.run { refreshes++ }
                    }
                }
            }
            try {
                connections.receive()
                admission.value = Admission(true, ConnectivityStatus.UNAVAILABLE)
                closed.receive()
                assertEquals(0, gateway.active)
                admission.value = Admission(true, ConnectivityStatus.AVAILABLE)
                connections.receive()
                admission.value = Admission(false, ConnectivityStatus.AVAILABLE)
                closed.receive()
                assertEquals(0, gateway.active)
                admission.value = Admission(true, ConnectivityStatus.AVAILABLE)
                connections.receive()
                assertEquals(3, refreshes)
                assertEquals(1, gateway.maximumActive)
            } finally { job.cancelAndJoin(); connections.close(); closed.close() }
            assertEquals(0, gateway.active)
        }
    }

    @Test
    fun `token generation replacement closes old socket and rejects its late hints`() = runBlocking {
        withTimeout(5_000) {
            val lifetime = MutableStateFlow(LocalSessionLifetime(1, true))
            val connections = Channel<Int>(Channel.UNLIMITED)
            val callbacks = mutableListOf<suspend (LiveRideEvent) -> Unit>()
            var refreshes = 0
            val gateway = TestLiveGateway { connected, hint ->
                callbacks += hint
                connected()
                connections.send(callbacks.size)
                awaitCancellation()
            }
            val job = launch { LiveUpdateSubscription(gateway, lifetime).run { refreshes++ } }
            try {
                assertEquals(1, connections.receive())
                lifetime.value = LocalSessionLifetime(2, true)
                assertEquals(2, connections.receive())
                assertEquals(1, gateway.maximumActive)
                assertEquals(2, refreshes)
                callbacks[0](LiveRideEvent("ride.accepted", "old"))
                assertEquals(2, refreshes)
                callbacks[1](LiveRideEvent("ride.accepted", "current"))
                assertEquals(3, refreshes)
                lifetime.value = LocalSessionLifetime(3, false)
                // CollectLatest must finish cancellation before observing a new owner.
                lifetime.value = LocalSessionLifetime(4, true)
                assertEquals(3, connections.receive())
                callbacks[1](LiveRideEvent("ride.accepted", "logged-out"))
                assertEquals(4, refreshes)
                assertEquals(1, gateway.maximumActive)
            } finally { job.cancelAndJoin(); connections.close() }
            assertEquals(0, gateway.active)
        }
    }

    @Test
    fun `inactive session opens nothing and logout cancels retry wait`() = runBlocking {
        withTimeout(5_000) {
            val lifetime = MutableStateFlow(LocalSessionLifetime())
            val retryEntered = CompletableDeferred<Unit>()
            val retryCancelled = CompletableDeferred<Unit>()
            val recovered = CompletableDeferred<Unit>()
            var attempts = 0
            val gateway = TestLiveGateway { _, _ ->
                attempts++
                if (attempts == 1) throw AuthenticationNetworkException()
                recovered.complete(Unit)
                awaitCancellation()
            }
            val subscription = LiveUpdateSubscription(gateway, lifetime, ::deterministicRetry) {
                retryEntered.complete(Unit)
                try { awaitCancellation() } finally { retryCancelled.complete(Unit) }
            }
            val job = launch { subscription.run {} }
            try {
                yield(); yield()
                assertEquals(0, attempts)
                lifetime.value = LocalSessionLifetime(1, true)
                retryEntered.await()
                lifetime.value = LocalSessionLifetime(2, false)
                retryCancelled.await()
                assertEquals(1, attempts)
                lifetime.value = LocalSessionLifetime(3, true)
                recovered.await()
                assertEquals(2, attempts)
            } finally { job.cancelAndJoin() }
        }
    }

    @Test
    fun `foreground owner cancellation closes connection without retry or refresh`() = runBlocking {
        withTimeout(5_000) {
            val connected = CompletableDeferred<Unit>()
            var refreshes = 0
            var retries = 0
            val gateway = TestLiveGateway { onConnected, _ ->
                onConnected(); connected.complete(Unit); awaitCancellation()
            }
            val subscription = LiveUpdateSubscription(
                gateway, MutableStateFlow(LocalSessionLifetime(1, true)),
                waitForRetry = { retries++ },
            )
            val job = launch { subscription.run { refreshes++ } }
            connected.await()
            job.cancelAndJoin()
            assertEquals(1, refreshes)
            assertEquals(0, retries)
            assertEquals(0, gateway.active)
        }
    }

    @Test
    fun `cancellation during authoritative catch up is never transport failure`() = runBlocking {
        withTimeout(5_000) {
            val refreshing = CompletableDeferred<Unit>()
            var retries = 0
            val gateway = TestLiveGateway { connected, _ -> connected(); awaitCancellation() }
            val subscription = LiveUpdateSubscription(
                gateway, MutableStateFlow(LocalSessionLifetime(1, true)),
                waitForRetry = { retries++ },
            )
            val job = launch {
                subscription.run { refreshing.complete(Unit); awaitCancellation() }
            }
            refreshing.await()
            job.cancelAndJoin()
            assertEquals(0, retries)
            assertEquals(0, gateway.active)
        }
    }

    @Test
    fun `credential rotation caused by catch up cancels old owner and catches up again`() = runBlocking {
        withTimeout(5_000) {
            val lifetime = MutableStateFlow(LocalSessionLifetime(1, true))
            val caughtUp = CompletableDeferred<Unit>()
            var refreshes = 0
            val gateway = TestLiveGateway { connected, _ -> connected(); awaitCancellation() }
            val job = launch {
                LiveUpdateSubscription(gateway, lifetime).run {
                    refreshes++
                    if (refreshes == 1) {
                        lifetime.value = LocalSessionLifetime(2, true)
                        yield()
                    } else caughtUp.complete(Unit)
                }
            }
            try {
                caughtUp.await()
                assertEquals(2, refreshes)
                assertEquals(1, gateway.maximumActive)
            } finally { job.cancelAndJoin() }
        }
    }

    @Test
    fun `unexpected programming failure is not swallowed as retry`() = runBlocking<Unit> {
        val gateway = TestLiveGateway { _, _ -> error("synthetic programming error") }
        assertFailsWith<IllegalStateException> {
            LiveUpdateSubscription(gateway, MutableStateFlow(LocalSessionLifetime(1, true))).run {}
        }
    }

    @Test
    fun `explicit cancellation exception propagates without a failure catch up`() = runBlocking {
        var refreshes = 0
        val gateway = TestLiveGateway { _, _ -> throw CancellationException("synthetic cancellation") }
        // A child CancellationException finishes collectLatest's child while
        // leaving the outer owner suspended; external cancellation must release it.
        val attempted = CompletableDeferred<Unit>()
        val guardedGateway = TestLiveGateway { connected, hint ->
            attempted.complete(Unit); gateway.listen(connected, hint)
        }
        val job = launch {
            LiveUpdateSubscription(guardedGateway, MutableStateFlow(LocalSessionLifetime(1, true)))
                .run { refreshes++ }
        }
        attempted.await()
        job.cancelAndJoin()
        assertEquals(0, refreshes)
    }

    @Test
    fun `only one run owns a socket until the previous foreground owner is cancelled`() = runBlocking {
        withTimeout(5_000) {
            val started = Channel<Unit>(Channel.UNLIMITED)
            val gateway = TestLiveGateway { connected, _ ->
                connected(); started.send(Unit); awaitCancellation()
            }
            val subscription = LiveUpdateSubscription(gateway, MutableStateFlow(LocalSessionLifetime(1, true)))
            val first = launch { subscription.run {} }
            started.receive()
            val second = launch { subscription.run {} }
            try {
                yield()
                assertEquals(1, gateway.active)
                first.cancelAndJoin()
                started.receive()
                assertEquals(1, gateway.maximumActive)
            } finally { first.cancelAndJoin(); second.cancelAndJoin(); started.close() }
        }
    }

    @Test
    fun `foreground connectivity and security commands gate both product roles`() {
        val states = listOf(
            AppUiState.PassengerReady(), AppUiState.DriverReady(DriverAvailabilityStatus.AVAILABLE),
        )
        for (state in states) {
            for (network in listOf(ConnectivityStatus.UNKNOWN, ConnectivityStatus.AVAILABLE)) {
                assertTrue(canListenForLiveUpdates(state, true, network, null))
                assertFalse(canListenForLiveUpdates(state, false, network, null))
            }
            assertFalse(canListenForLiveUpdates(state, true, ConnectivityStatus.UNAVAILABLE, null))
            for (kind in listOf(AppActionKind.LOGOUT, AppActionKind.CHANGE_ACCOUNT_PASSWORD, AppActionKind.REVOKE_ACCOUNT_SESSION)) {
                assertFalse(canListenForLiveUpdates(state, true, ConnectivityStatus.AVAILABLE, AppAction(kind)))
            }
            assertTrue(canListenForLiveUpdates(state, true, ConnectivityStatus.AVAILABLE, AppAction(AppActionKind.REFRESH)))
        }
        assertFalse(canListenForLiveUpdates(AppUiState.SignedOut(), true, ConnectivityStatus.AVAILABLE, null))
        assertFalse(canListenForLiveUpdates(AppUiState.DriverOnboarding("test", emptyList(), emptyList()), true, ConnectivityStatus.AVAILABLE, null))
    }

    @Test
    fun `backoff grows caps and resets with bounded jitter`() {
        val retry = deterministicRetry()
        assertEquals(listOf(1_000L, 2_000L, 4_000L, 8_000L, 16_000L, 30_000L, 30_000L), List(7) { retry.nextDelayMillis() })
        retry.reset()
        assertEquals(1_000L, retry.nextDelayMillis())
        val lower = LiveUpdateRetryPolicy(chooseDelay = { minimum, _ -> minimum })
        assertEquals(listOf(500L, 1_000L, 2_000L), List(3) { lower.nextDelayMillis() })
        val random = LiveUpdateRetryPolicy()
        repeat(100) { assertTrue(random.nextDelayMillis() in 500L..30_000L) }
    }

    @Test
    fun `invalid retry timing or injected delay cannot make a busy loop`() {
        assertFailsWith<IllegalArgumentException> { LiveUpdateRetryPolicy(initialMillis = 0) }
        assertFailsWith<IllegalArgumentException> { LiveUpdateRetryPolicy(maximumMillis = 999) }
        assertFailsWith<IllegalArgumentException> { LiveUpdateRetryPolicy(maximumMillis = Long.MAX_VALUE) }
        assertFailsWith<IllegalArgumentException> { LiveUpdateRetryPolicy(chooseDelay = { _, _ -> 0 }).nextDelayMillis() }
    }

    @Test
    fun `stalled handshake is cancelled before the next bounded retry`() = runBlocking {
        withTimeout(5_000) {
            val retry = CompletableDeferred<Long>()
            val gateway = TestLiveGateway { _, _ -> awaitCancellation() }
            val subscription = LiveUpdateSubscription(
                gateway, MutableStateFlow(LocalSessionLifetime(1, true)), ::deterministicRetry,
                waitForRetry = { retry.complete(it); awaitCancellation() },
                connectTimeoutMillis = 20,
            )
            var refreshes = 0
            val job = launch { subscription.run { refreshes++ } }
            try {
                assertEquals(1_000L, retry.await())
                assertEquals(0, gateway.active)
                assertEquals(1, refreshes)
            } finally { job.cancelAndJoin() }
        }
    }

    @Test
    fun `stalled catch up times out without losing a healthy subscription`() = runBlocking {
        withTimeout(5_000) {
            val hintCompleted = CompletableDeferred<Unit>()
            val gateway = TestLiveGateway { connected, hint ->
                connected()
                hint(LiveRideEvent("ride.accepted", "synthetic"))
                hintCompleted.complete(Unit)
                awaitCancellation()
            }
            var refreshes = 0
            val subscription = LiveUpdateSubscription(
                gateway, MutableStateFlow(LocalSessionLifetime(1, true)), refreshTimeoutMillis = 20,
            )
            val job = launch {
                subscription.run {
                    refreshes++
                    if (refreshes == 1) awaitCancellation()
                }
            }
            try {
                hintCompleted.await()
                assertEquals(2, refreshes)
                assertEquals(1, gateway.active)
            } finally { job.cancelAndJoin() }
        }
    }

    @Test
    fun `zero handshake or refresh budget is rejected`() {
        val gateway = TestLiveGateway { _, _ -> awaitCancellation() }
        val lifetime = MutableStateFlow(LocalSessionLifetime())
        assertFailsWith<IllegalArgumentException> { LiveUpdateSubscription(gateway, lifetime, connectTimeoutMillis = 0) }
        assertFailsWith<IllegalArgumentException> { LiveUpdateSubscription(gateway, lifetime, refreshTimeoutMillis = 0) }
    }
}

private fun deterministicRetry() = LiveUpdateRetryPolicy(chooseDelay = { _, maximum -> maximum })

private class TestLiveGateway(
    private val behavior: suspend (suspend () -> Unit, suspend (LiveRideEvent) -> Unit) -> Unit,
) : LiveEventGateway {
    var active = 0
    var maximumActive = 0
    override suspend fun listen(onConnected: suspend () -> Unit, onRideEvent: suspend (LiveRideEvent) -> Unit) {
        active++
        maximumActive = maxOf(maximumActive, active)
        try { behavior(onConnected, onRideEvent) } finally { active-- }
    }
}
