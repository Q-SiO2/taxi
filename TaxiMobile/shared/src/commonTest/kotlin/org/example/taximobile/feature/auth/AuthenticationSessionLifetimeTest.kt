package org.example.taximobile.feature.auth

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.SecureTokenStorageException
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens

class AuthenticationSessionLifetimeTest {
    @Test
    fun `ordinary restore retains generation and exposes no account or credential`() = runBlocking {
        val coordinator = coordinator()
        assertEquals(LocalSessionLifetime(), coordinator.liveSessionLifetime.value)
        assertIs<AuthenticationState.Authenticated>(coordinator.restore())
        val initial = coordinator.liveSessionLifetime.value
        assertEquals(LocalSessionLifetime(1, true), initial)
        coordinator.restore()
        assertEquals(initial, coordinator.liveSessionLifetime.value)
        assertFalse(initial.toString().contains("access"))
        assertFalse(initial.toString().contains("synthetic-user"))
    }

    @Test
    fun `login and rotated refresh replace ownership while transport failure retains it`() = runBlocking {
        val gateway = LifetimeGateway()
        val coordinator = coordinator(gateway)
        coordinator.restore()
        coordinator.login("synthetic", "synthetic", null)
        assertEquals(LocalSessionLifetime(3, true), coordinator.liveSessionLifetime.value)
        gateway.rejectAccess = "login-access"
        assertIs<AuthenticationState.Authenticated>(coordinator.restore())
        assertEquals(LocalSessionLifetime(4, true), coordinator.liveSessionLifetime.value)
        gateway.networkUnavailable = true
        assertIs<AuthenticationState.Failure>(coordinator.restore())
        assertEquals(LocalSessionLifetime(4, true), coordinator.liveSessionLifetime.value)
    }

    @Test
    fun `two concurrent restores rotate a rejected refresh credential only once`() = runBlocking {
        withTimeout(5_000) {
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            val gateway = LifetimeGateway().apply {
                rejectAccess = "stored-access"
                refreshGate = { entered.complete(Unit); release.await() }
            }
            val coordinator = coordinator(gateway)
            val first = async { coordinator.restore() }
            entered.await()
            val second = async { coordinator.restore() }
            release.complete(Unit)
            assertIs<AuthenticationState.Authenticated>(first.await())
            assertIs<AuthenticationState.Authenticated>(second.await())
            assertEquals(1, gateway.refreshes)
            assertEquals(LocalSessionLifetime(1, true), coordinator.liveSessionLifetime.value)
        }
    }

    @Test
    fun `logout stops subscriptions before waiting for remote revoke`() = runBlocking {
        withTimeout(5_000) {
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            val gateway = LifetimeGateway().apply { logoutGate = { entered.complete(Unit); release.await() } }
            val store = LifetimeStore()
            val coordinator = coordinator(gateway, store)
            coordinator.restore()
            val logout = async { coordinator.logout() }
            entered.await()
            assertFalse(coordinator.liveSessionLifetime.value.active)
            assertEquals(null, store.value)
            release.complete(Unit)
            assertIs<AuthenticationState.Unauthenticated>(logout.await())
            assertIs<AuthenticationState.Unauthenticated>(coordinator.restore())
            assertFalse(coordinator.liveSessionLifetime.value.active)
        }
    }

    @Test
    fun `rejected refresh and missing credentials end ownership`() = runBlocking {
        val gateway = LifetimeGateway()
        val store = LifetimeStore()
        val coordinator = coordinator(gateway, store)
        coordinator.restore()
        gateway.rejectAccess = "stored-access"
        gateway.rejectRefresh = true
        assertIs<AuthenticationState.Unauthenticated>(coordinator.restore())
        assertFalse(coordinator.liveSessionLifetime.value.active)
        assertEquals(null, store.value)
        coordinator.restore()
        assertEquals(LocalSessionLifetime(2, false), coordinator.liveSessionLifetime.value)
    }

    @Test
    fun `failed save clear or facility read never retains live ownership`() = runBlocking {
        val store = LifetimeStore()
        val coordinator = coordinator(store = store)
        coordinator.restore()
        store.failRead = true
        assertIs<AuthenticationState.Failure>(coordinator.restore())
        assertFalse(coordinator.liveSessionLifetime.value.active)
        store.failRead = false
        coordinator.restore()
        assertTrue(coordinator.liveSessionLifetime.value.active)
        store.failClear = true
        assertIs<AuthenticationState.Failure>(coordinator.clearLocalSession())
        assertFalse(coordinator.liveSessionLifetime.value.active)
        store.failClear = false
        store.failSave = true
        assertIs<AuthenticationState.Failure>(coordinator.login("synthetic", "synthetic", null))
        assertFalse(coordinator.liveSessionLifetime.value.active)
    }

    @Test
    fun `late and queued restores cannot reopen hints during logout cleanup`() = runBlocking {
        withTimeout(5_000) {
            val gateway = LifetimeGateway()
            val coordinator = coordinator(gateway)
            coordinator.restore()
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            gateway.accountGate = { entered.complete(Unit); release.await() }
            val late = async { coordinator.restore() }
            entered.await()
            coordinator.beginSessionEnd()
            assertTrue(coordinator.liveSessionLifetime.value.ending)
            release.complete(Unit)
            late.await()
            assertFalse(coordinator.liveSessionLifetime.value.active)
            coordinator.restore()
            assertFalse(coordinator.liveSessionLifetime.value.active)
            coordinator.logout()
            assertFalse(coordinator.liveSessionLifetime.value.active)
            assertFalse(coordinator.liveSessionLifetime.value.ending)
            coordinator.login("synthetic", "synthetic", null)
            assertTrue(coordinator.liveSessionLifetime.value.active)
        }
    }

    @Test
    fun `ending an inactive session still prevents first restore from opening hints`() = runBlocking {
        val coordinator = coordinator()
        coordinator.beginSessionEnd()
        assertEquals(LocalSessionLifetime(0, false, true), coordinator.liveSessionLifetime.value)
        coordinator.restore()
        assertEquals(LocalSessionLifetime(0, false, true), coordinator.liveSessionLifetime.value)
        coordinator.clearLocalSession()
        assertEquals(LocalSessionLifetime(), coordinator.liveSessionLifetime.value)
        coordinator.login("synthetic", "synthetic", null)
        assertEquals(LocalSessionLifetime(1, true), coordinator.liveSessionLifetime.value)
    }
}

private fun coordinator(gateway: LifetimeGateway = LifetimeGateway(), store: LifetimeStore = LifetimeStore()) =
    AuthenticationSessionCoordinator(gateway, store)

private class LifetimeStore : SecureTokenStore {
    var value: StoredTokens? = StoredTokens("stored-access", "stored-refresh")
    var failSave = false
    var failClear = false
    var failRead = false
    override suspend fun tokens(): StoredTokens? {
        if (failRead) throw SecureTokenStorageException("synthetic read failure")
        return value
    }
    override suspend fun save(accessToken: String, refreshToken: String) {
        if (failSave) throw SecureTokenStorageException("synthetic save failure")
        value = StoredTokens(accessToken, refreshToken)
    }
    override suspend fun clear() {
        if (failClear) throw SecureTokenStorageException("synthetic clear failure")
        value = null
    }
}

private class LifetimeGateway : AuthenticationGateway {
    var rejectAccess: String? = null
    var rejectRefresh = false
    var networkUnavailable = false
    var refreshes = 0
    var refreshGate: suspend () -> Unit = {}
    var logoutGate: suspend () -> Unit = {}
    var accountGate: suspend () -> Unit = {}
    override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
    override suspend fun login(identifier: String, password: String, deviceLabel: String?) = SessionTokens("login-access", "login-refresh")
    override suspend fun refresh(refreshToken: String): SessionTokens {
        refreshes++
        refreshGate()
        if (rejectRefresh) throw AuthenticationRejectedException()
        return SessionTokens("refreshed-access", "refreshed-refresh")
    }
    override suspend fun logout(accessToken: String) = logoutGate()
    override suspend fun currentAccount(accessToken: String): CurrentAccount {
        accountGate()
        if (networkUnavailable) throw AuthenticationNetworkException()
        if (rejectAccess == accessToken) throw AuthenticationRejectedException()
        return CurrentAccount("synthetic-user", emptySet(), "Synthetic")
    }
}
