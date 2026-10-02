package org.example.taximobile.feature.auth

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlin.test.assertNull
import kotlinx.coroutines.runBlocking
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationRejectedException
import org.example.taximobile.data.auth.SecureTokenStorageException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import taximobile.shared.generated.resources.Res
import taximobile.shared.generated.resources.message_session_restore_failed
import taximobile.shared.generated.resources.message_sign_in_failed

class AuthenticationSessionStorageTest {
    @Test
    fun `restore converts protected storage failure into an actionable state`() = runBlocking {
        val coordinator = AuthenticationSessionCoordinator(
            gateway = RecordingAuthenticationGateway(),
            tokenStore = FailingTokenStore(failRead = true),
        )

        val failure = assertIs<AuthenticationState.Failure>(coordinator.restore())

        assertEquals(Res.string.message_session_restore_failed, failure.message.resource)
    }

    @Test
    fun `login revokes newly issued backend session when protected save fails`() = runBlocking {
        val gateway = RecordingAuthenticationGateway()
        val coordinator = AuthenticationSessionCoordinator(
            gateway = gateway,
            tokenStore = FailingTokenStore(failSave = true),
        )

        val failure = assertIs<AuthenticationState.Failure>(
            coordinator.login("person@example.test", "password", "test device"),
        )

        assertEquals(Res.string.message_sign_in_failed, failure.message.resource)
        assertEquals("issued-access", gateway.loggedOutAccessToken)
    }

    @Test
    fun `logout does not claim local success when protected deletion fails`() = runBlocking {
        val gateway = RecordingAuthenticationGateway()
        val coordinator = AuthenticationSessionCoordinator(
            gateway = gateway,
            tokenStore = FailingTokenStore(
                storedTokens = StoredTokens("stored-access", "stored-refresh"),
                failClear = true,
            ),
        )

        val failure = assertIs<AuthenticationState.Failure>(coordinator.logout())

        assertEquals(Res.string.message_session_restore_failed, failure.message.resource)
        assertNull(gateway.loggedOutAccessToken)
    }

    @Test
    fun `refresh revokes newly issued backend session when protected save fails`() = runBlocking {
        val gateway = RecordingAuthenticationGateway(rejectInitialAccessToken = "stored-access")
        val coordinator = AuthenticationSessionCoordinator(
            gateway = gateway,
            tokenStore = FailingTokenStore(
                storedTokens = StoredTokens("stored-access", "stored-refresh"),
                failSave = true,
            ),
        )

        val failure = assertIs<AuthenticationState.Failure>(coordinator.restore())

        assertEquals(Res.string.message_session_restore_failed, failure.message.resource)
        assertEquals("refreshed-access", gateway.loggedOutAccessToken)
    }
}

private class FailingTokenStore(
    private val storedTokens: StoredTokens? = null,
    private val failRead: Boolean = false,
    private val failSave: Boolean = false,
    private val failClear: Boolean = false,
) : SecureTokenStore {
    override suspend fun tokens(): StoredTokens? {
        if (failRead) throw SecureTokenStorageException("test read failure")
        return storedTokens
    }

    override suspend fun save(accessToken: String, refreshToken: String) {
        if (failSave) throw SecureTokenStorageException("test save failure")
    }

    override suspend fun clear() {
        if (failClear) throw SecureTokenStorageException("test clear failure")
    }
}

private class RecordingAuthenticationGateway(
    private val rejectInitialAccessToken: String? = null,
) : AuthenticationGateway {
    var loggedOutAccessToken: String? = null

    override suspend fun register(
        displayName: String,
        email: String?,
        phoneNumber: String?,
        password: String,
    ) = Unit

    override suspend fun login(identifier: String, password: String, deviceLabel: String?) =
        SessionTokens(accessToken = "issued-access", refreshToken = "issued-refresh")

    override suspend fun refresh(refreshToken: String) =
        SessionTokens(accessToken = "refreshed-access", refreshToken = "refreshed-refresh")

    override suspend fun logout(accessToken: String) {
        loggedOutAccessToken = accessToken
    }

    override suspend fun currentAccount(accessToken: String): CurrentAccount {
        if (accessToken == rejectInitialAccessToken) throw AuthenticationRejectedException()
        error("Current account must not be requested after a protected-storage failure")
    }
}
