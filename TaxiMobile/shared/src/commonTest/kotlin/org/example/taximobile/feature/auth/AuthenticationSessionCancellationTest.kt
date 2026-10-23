package org.example.taximobile.feature.auth

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertIs
import kotlin.test.assertTrue
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineStart
import kotlinx.coroutines.async
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.SecureTokenStorageException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_network_unavailable

class AuthenticationSessionCancellationTest {
    @Test
    fun refresh_commit_deadline_reports_network_failure_without_publishing_a_principal() = runBlocking {
        withTimeout(2_000) {
            val gateway = RotationGateway().apply {
                afterServerRotation = { CompletableDeferred<Unit>().await() }
            }
            val store = RotationStore()
            val auth = AuthenticationSessionCoordinator(gateway, store, refreshCommitTimeoutMillis = 25)
            val result = assertIs<AuthenticationState.Failure>(auth.restore())
            assertEquals(Res.string.message_network_unavailable, result.message.resource)
            assertEquals(StoredTokens("old-access", "old-refresh"), store.value)
            assertEquals(1, gateway.refreshes)
            assertFalse(auth.liveSessionLifetime.value.active)
        }
    }

    @Test
    fun failed_protected_save_after_cancellation_revokes_issued_session_and_does_not_resume_ui() = runBlocking {
        withTimeout(5_000) {
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            val gateway = RotationGateway().apply {
                afterServerRotation = { entered.complete(Unit); release.await() }
            }
            val store = RotationStore().apply {
                beforeSave = { throw SecureTokenStorageException("Synthetic protected save failure") }
            }
            val auth = AuthenticationSessionCoordinator(gateway, store)
            var uiResumed = false
            val restore = async { auth.restore(); uiResumed = true }
            entered.await()
            restore.cancel()
            release.complete(Unit)
            restore.join()
            assertEquals(listOf("new-access"), gateway.loggedOut)
            assertEquals(StoredTokens("old-access", "old-refresh"), store.value)
            assertFalse(auth.liveSessionLifetime.value.active)
            assertTrue(restore.isCancelled)
            assertFalse(uiResumed, "A cancelled observer must not receive even a typed failure state")
        }
    }

    @Test
    fun cancelled_ui_after_server_rotation_still_commits_the_issued_pair() = runBlocking {
        withTimeout(5_000) {
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            val gateway = RotationGateway().apply {
                afterServerRotation = { entered.complete(Unit); release.await() }
            }
            val store = RotationStore()
            val auth = AuthenticationSessionCoordinator(gateway, store)
            val restore = async { auth.restore() }
            entered.await()
            restore.cancel()
            release.complete(Unit)
            restore.join()
            assertEquals(StoredTokens("new-access", "new-refresh"), store.value)
            assertIs<AuthenticationState.Authenticated>(auth.restore())
            assertEquals(1, gateway.refreshes)
        }
    }

    @Test
    fun cancelled_ui_during_protected_save_does_not_drop_the_rotated_pair() = runBlocking {
        withTimeout(5_000) {
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            val gateway = RotationGateway()
            val store = RotationStore().apply {
                beforeSave = { entered.complete(Unit); release.await() }
            }
            val auth = AuthenticationSessionCoordinator(gateway, store)
            val restore = async { auth.restore() }
            entered.await()
            restore.cancel()
            release.complete(Unit)
            restore.join()
            assertEquals(StoredTokens("new-access", "new-refresh"), store.value)
            assertIs<AuthenticationState.Authenticated>(auth.restore())
            assertEquals(1, gateway.refreshes)
        }
    }

    @Test
    fun staged_logout_after_cancelled_rotation_revokes_the_new_pair_and_never_reopens_hints() = runBlocking {
        withTimeout(5_000) {
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            val gateway = RotationGateway().apply {
                afterServerRotation = { entered.complete(Unit); release.await() }
            }
            val store = RotationStore()
            val auth = AuthenticationSessionCoordinator(gateway, store)
            val restore = async { auth.restore() }
            entered.await()
            restore.cancel()
            val logout = async(start = CoroutineStart.UNDISPATCHED) { auth.logout() }
            assertFalse(auth.liveSessionLifetime.value.active)
            release.complete(Unit)
            restore.join()
            assertIs<AuthenticationState.Unauthenticated>(logout.await())
            assertEquals(null, store.value)
            assertEquals(listOf("new-access"), gateway.loggedOut)
            assertFalse(auth.liveSessionLifetime.value.active)
        }
    }

    @Test
    fun cancelling_principal_validation_keeps_the_already_committed_pair_for_fresh_restore() = runBlocking {
        withTimeout(5_000) {
            val entered = CompletableDeferred<Unit>()
            val release = CompletableDeferred<Unit>()
            val gateway = RotationGateway().apply {
                validateNewAccount = { entered.complete(Unit); release.await() }
            }
            val store = RotationStore()
            val auth = AuthenticationSessionCoordinator(gateway, store)
            val restore = async { auth.restore() }
            entered.await()
            restore.cancel()
            release.complete(Unit)
            restore.join()
            assertEquals(StoredTokens("new-access", "new-refresh"), store.value)
            assertIs<AuthenticationState.Authenticated>(auth.restore())
            assertEquals(1, gateway.refreshes)
        }
    }
}

private class RotationStore : SecureTokenStore {
    var value: StoredTokens? = StoredTokens("old-access", "old-refresh")
    var beforeSave: suspend () -> Unit = {}
    override suspend fun tokens() = value
    override suspend fun save(accessToken: String, refreshToken: String) {
        beforeSave()
        value = StoredTokens(accessToken, refreshToken)
    }
    override suspend fun clear() { value = null }
}

private class RotationGateway : AuthenticationGateway {
    var refreshes = 0
    val loggedOut = mutableListOf<String>()
    var afterServerRotation: suspend () -> Unit = {}
    var validateNewAccount: suspend () -> Unit = {}
    override suspend fun register(displayName: String, email: String?, phoneNumber: String?, password: String) = Unit
    override suspend fun login(identifier: String, password: String, deviceLabel: String?) = SessionTokens("new-access", "new-refresh")
    override suspend fun refresh(refreshToken: String): SessionTokens {
        refreshes++
        // One-use rotation represents the server committing before its response
        // or the subsequent protected store work reaches the cancelled caller.
        if (refreshToken != "old-refresh" || refreshes != 1) throw AuthenticationRejectedException()
        afterServerRotation()
        return SessionTokens("new-access", "new-refresh")
    }
    override suspend fun logout(accessToken: String) { loggedOut += accessToken }
    override suspend fun currentAccount(accessToken: String): CurrentAccount {
        if (accessToken == "old-access") throw AuthenticationRejectedException()
        validateNewAccount()
        return CurrentAccount("synthetic-owner", emptySet(), "Synthetic")
    }
}
