package org.example.taximobile.feature.auth

import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.yield
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.SecureTokenStorageException
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.data.network.ApiRequestException
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlin.test.assertTrue

class AuthenticatedReadRecoveryTest {
    @Test fun expired_access_refreshes_before_advisory_read() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access" }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        assertEquals("new-access", auth.readWithSessionRecovery { store.tokens()!!.accessToken })
        assertEquals(1, gateway.refreshes)
        assertEquals("new-refresh", store.value?.refreshToken)
        assertTrue(auth.liveSessionLifetime.value.active)
    }

    @Test fun rejection_after_preflight_has_one_same_owner_retry() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway()
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertEquals("new-access", auth.readWithSessionRecovery {
            reads++
            if (reads == 1) {
                gateway.rejectAccess = "old-access"
                throw AuthenticationRejectedException()
            }
            store.value!!.accessToken
        })
        assertEquals(2, reads)
        assertEquals(1, gateway.refreshes)
    }

    @Test fun repeated_rejection_is_bounded_and_clears_credentials() = runBlocking {
        val store = ReadStore()
        val auth = AuthenticationSessionCoordinator(ReadAuthGateway(), store)
        var reads = 0
        assertFailsWith<AuthenticationRejectedException> {
            auth.readWithSessionRecovery { reads++; throw AuthenticationRejectedException() }
        }
        assertEquals(2, reads)
        assertNull(store.value)
        assertFalse(auth.liveSessionLifetime.value.active)
    }

    @Test fun revoked_refresh_prevents_read_and_clears_credentials() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access"; rejectRefresh = true }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertFailsWith<AuthenticationRejectedException> { auth.readWithSessionRecovery { reads++ } }
        assertEquals(0, reads)
        assertEquals(1, gateway.refreshes)
        assertNull(store.value)
    }

    @Test fun refresh_network_failure_retains_credentials_without_reading() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access"; refreshUnavailable = true }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertFailsWith<AuthenticationNetworkException> { auth.readWithSessionRecovery { reads++ } }
        assertEquals(0, reads)
        assertEquals(StoredTokens("old-access", "old-refresh"), store.value)
    }

    @Test fun concurrent_expired_reads_rotate_only_once() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access" }
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        gateway.refreshGate = { entered.complete(Unit); release.await() }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        val reads = (1..8).map { async { auth.readWithSessionRecovery { store.value!!.accessToken } } }
        withTimeout(2000) { entered.await() }
        release.complete(Unit)
        assertTrue(reads.map { it.await() }.all { it == "new-access" })
        assertEquals(1, gateway.refreshes)
    }

    @Test fun logout_fences_pending_read_before_waiting_for_credential_mutex() = runBlocking {
        val store = ReadStore()
        val auth = AuthenticationSessionCoordinator(ReadAuthGateway(), store)
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val read = async { runCatching { auth.readWithSessionRecovery { entered.complete(Unit); release.await(); "old projection" } } }
        withTimeout(2000) { entered.await() }
        val logout = async { auth.logout() }
        withTimeout(2000) { while (!auth.liveSessionLifetime.value.ending) yield() }
        assertFalse(auth.liveSessionLifetime.value.active)
        release.complete(Unit)
        assertIs<AuthenticationRejectedException>(read.await().exceptionOrNull())
        assertIs<AuthenticationState.Unauthenticated>(logout.await())
        assertNull(store.value)
        assertFalse(auth.liveSessionLifetime.value.active)
    }

    @Test fun queued_login_does_not_receive_prior_accounts_read_projection() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway()
        val auth = AuthenticationSessionCoordinator(gateway, store)
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val read = async { runCatching { auth.readWithSessionRecovery { entered.complete(Unit); release.await(); it.id } } }
        withTimeout(2000) { entered.await() }
        val login = async { auth.login("new-user", "synthetic", null) }
        withTimeout(2000) { while (auth.liveSessionLifetime.value.active) yield() }
        release.complete(Unit)
        assertIs<AuthenticationRejectedException>(read.await().exceptionOrNull())
        assertEquals("new-user", assertIs<AuthenticationState.Authenticated>(login.await()).account.id)
        assertTrue(auth.liveSessionLifetime.value.active)
    }

    @Test fun backend_principal_change_is_refused_before_read() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway()
        val auth = AuthenticationSessionCoordinator(gateway, store)
        auth.restore()
        gateway.userId = "different-user"
        var reads = 0
        assertFailsWith<AuthenticationRejectedException> { auth.readWithSessionRecovery { reads++ } }
        assertEquals(0, reads)
        assertNull(store.value)
    }

    @Test fun cancellation_is_not_retried_or_normalized_as_logout() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway()
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertFailsWith<CancellationException> {
            auth.readWithSessionRecovery { reads++; throw CancellationException("Synthetic cancellation") }
        }
        assertEquals(1, reads)
        assertEquals(0, gateway.refreshes)
        assertEquals(StoredTokens("old-access", "old-refresh"), store.value)
        assertEquals("old-access", auth.readWithSessionRecovery { store.value!!.accessToken })
    }

    @Test fun read_transport_failure_is_not_replayed() = runBlocking {
        val store = ReadStore()
        val auth = AuthenticationSessionCoordinator(ReadAuthGateway(), store)
        var reads = 0
        assertFailsWith<AuthenticationNetworkException> {
            auth.readWithSessionRecovery { reads++; throw AuthenticationNetworkException() }
        }
        assertEquals(1, reads)
        assertEquals(StoredTokens("old-access", "old-refresh"), store.value)
    }

    @Test fun queued_login_cannot_reopen_hints_during_rotated_principal_validation() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access" }
        val refreshing = CompletableDeferred<Unit>()
        val rotate = CompletableDeferred<Unit>()
        val validating = CompletableDeferred<Unit>()
        val validate = CompletableDeferred<Unit>()
        gateway.refreshGate = { refreshing.complete(Unit); rotate.await() }
        gateway.accountGate = { token ->
            if (token == "new-access") { validating.complete(Unit); validate.await() }
        }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        val read = async { runCatching { auth.readWithSessionRecovery { reads++ } } }
        withTimeout(2000) { refreshing.await() }
        // Let login stage its fence before allowing refresh to finish.
        val login = async { auth.login("new-user", "synthetic", null) }
        yield()
        rotate.complete(Unit)
        withTimeout(2000) { validating.await() }
        assertFalse(auth.liveSessionLifetime.value.active, "Old refresh must not restart hints while login is queued")
        validate.complete(Unit)
        assertIs<AuthenticationRejectedException>(read.await().exceptionOrNull())
        assertEquals(0, reads)
        assertEquals("new-user", assertIs<AuthenticationState.Authenticated>(login.await()).account.id)
        assertTrue(auth.liveSessionLifetime.value.active)
    }

    @Test fun logout_during_refresh_cannot_publish_or_reactivate_the_old_owner() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access" }
        val refreshing = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        gateway.refreshGate = { refreshing.complete(Unit); release.await() }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        val read = async { runCatching { auth.readWithSessionRecovery { reads++ } } }
        withTimeout(2000) { refreshing.await() }
        val logout = async { auth.logout() }
        withTimeout(2000) { while (!auth.liveSessionLifetime.value.ending) yield() }
        release.complete(Unit)
        assertIs<AuthenticationRejectedException>(read.await().exceptionOrNull())
        assertEquals(0, reads)
        assertIs<AuthenticationState.Unauthenticated>(logout.await())
        assertNull(store.value)
        assertFalse(auth.liveSessionLifetime.value.active)
    }

    @Test fun cancelled_refresh_propagates_and_releases_the_mutex_without_erasing_credentials() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply {
            rejectAccess = "old-access"
            refreshGate = { throw CancellationException("Synthetic refresh cancellation") }
        }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertFailsWith<CancellationException> { auth.readWithSessionRecovery { reads++ } }
        assertEquals(0, reads)
        assertEquals(1, gateway.refreshes)
        assertEquals(StoredTokens("old-access", "old-refresh"), store.value)
        gateway.refreshGate = {}
        assertEquals("new-access", auth.readWithSessionRecovery { store.value!!.accessToken })
    }

    @Test fun protected_storage_failure_does_not_read_or_retry_the_business_operation() = runBlocking {
        val store = ReadStore().apply { failSave = true }
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access" }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertFailsWith<ApiRequestException> { auth.readWithSessionRecovery { reads++ } }
        assertEquals(0, reads)
        assertEquals(1, gateway.refreshes)
        assertEquals(1, gateway.logouts, "Best-effort revoke of issued but unpersisted credentials")
        assertFalse(auth.liveSessionLifetime.value.active)
    }

    @Test fun missing_credentials_do_not_call_backend_or_advisory_read() = runBlocking {
        val store = ReadStore().apply { value = null }
        val gateway = ReadAuthGateway()
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertFailsWith<AuthenticationRejectedException> { auth.readWithSessionRecovery { reads++ } }
        assertEquals(0, reads)
        assertEquals(0, gateway.refreshes)
        assertFalse(auth.liveSessionLifetime.value.active)
    }

    @Test fun queued_read_cannot_adopt_a_login_staged_after_it_was_requested() = runBlocking {
        val store = ReadStore()
        val auth = AuthenticationSessionCoordinator(ReadAuthGateway(), store)
        val entered = CompletableDeferred<Unit>()
        val release = CompletableDeferred<Unit>()
        val first = async { runCatching { auth.readWithSessionRecovery { entered.complete(Unit); release.await() } } }
        withTimeout(2000) { entered.await() }
        var queuedReads = 0
        val queued = async { runCatching { auth.readWithSessionRecovery { queuedReads++ } } }
        yield() // Queue the old owner's read behind the active read.
        val login = async { auth.login("new-user", "synthetic", null) }
        withTimeout(2000) { while (auth.liveSessionLifetime.value.active) yield() }
        release.complete(Unit)
        assertIs<AuthenticationRejectedException>(first.await().exceptionOrNull())
        assertIs<AuthenticationRejectedException>(queued.await().exceptionOrNull())
        assertEquals(0, queuedReads)
        assertEquals("new-user", assertIs<AuthenticationState.Authenticated>(login.await()).account.id)
    }

    @Test fun a_quote_has_only_one_refresh_budget_including_preflight() = runBlocking {
        val store = ReadStore()
        val gateway = ReadAuthGateway().apply { rejectAccess = "old-access" }
        val auth = AuthenticationSessionCoordinator(gateway, store)
        var reads = 0
        assertFailsWith<AuthenticationRejectedException> {
            auth.readWithSessionRecovery {
                reads++
                gateway.rejectAccess = "new-access"
                throw AuthenticationRejectedException()
            }
        }
        assertEquals(1, reads)
        assertEquals(1, gateway.refreshes)
        assertNull(store.value)
        assertFalse(auth.liveSessionLifetime.value.active)
    }

    @Test fun failed_credential_clear_is_not_presented_as_successful_sign_out() = runBlocking {
        val store = ReadStore().apply { failClear = true }
        val auth = AuthenticationSessionCoordinator(ReadAuthGateway(), store)
        var reads = 0
        assertFailsWith<ApiRequestException> {
            auth.readWithSessionRecovery { reads++; throw AuthenticationRejectedException() }
        }
        assertEquals(2, reads)
        assertEquals(StoredTokens("old-access", "old-refresh"), store.value)
        assertFalse(auth.liveSessionLifetime.value.active)
    }
}

private class ReadStore : SecureTokenStore {
    var value: StoredTokens? = StoredTokens("old-access", "old-refresh")
    var failSave = false
    var failClear = false
    override suspend fun tokens() = value
    override suspend fun save(accessToken: String, refreshToken: String) {
        if (failSave) throw SecureTokenStorageException("Synthetic persistence failure")
        value = StoredTokens(accessToken, refreshToken)
    }
    override suspend fun clear() {
        if (failClear) throw SecureTokenStorageException("Synthetic clear failure")
        value = null
    }
}

private class ReadAuthGateway : AuthenticationGateway {
    var userId = "original-user"
    var rejectAccess: String? = null
    var rejectRefresh = false
    var refreshUnavailable = false
    var refreshes = 0
    var logouts = 0
    var refreshGate: suspend () -> Unit = {}
    var accountGate: suspend (String) -> Unit = {}
    override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
    override suspend fun login(identifier: String, password: String, deviceLabel: String?): SessionTokens {
        userId = identifier
        return SessionTokens("login-access", "login-refresh")
    }
    override suspend fun refresh(refreshToken: String): SessionTokens {
        refreshes++
        refreshGate()
        if (refreshUnavailable) throw AuthenticationNetworkException()
        if (rejectRefresh) throw AuthenticationRejectedException()
        return SessionTokens("new-access", "new-refresh")
    }
    override suspend fun logout(accessToken: String) { logouts++ }
    override suspend fun currentAccount(accessToken: String): CurrentAccount {
        accountGate(accessToken)
        if (rejectAccess == accessToken) throw AuthenticationRejectedException()
        return CurrentAccount(userId, emptySet(), "Synthetic")
    }
}
