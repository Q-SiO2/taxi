package org.example.taximobile.feature.app

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs
import kotlinx.coroutines.runBlocking
import org.example.taximobile.app.AppRole
import org.example.taximobile.data.auth.AuthenticationGateway
import org.example.taximobile.data.auth.AuthenticationNetworkException
import org.example.taximobile.data.auth.SecureTokenStore
import org.example.taximobile.data.auth.StoredTokens
import org.example.taximobile.domain.auth.CurrentAccount
import org.example.taximobile.domain.auth.SessionTokens
import org.example.taximobile.domain.system.ClientCompatibility
import org.example.taximobile.domain.system.ClientCompatibilityGateway
import org.example.taximobile.domain.system.ClientCompatibilityStatus
import org.example.taximobile.feature.auth.AuthenticationSessionCoordinator

class ClientCompatibilityCoordinatorTest {
    @Test
    fun obsoleteClientStopsBeforeAuthenticationRestore() = runBlocking {
        val coordinator = coordinator(
            compatibility = ClientCompatibility(
                status = ClientCompatibilityStatus.UPGRADE_REQUIRED,
                minimumVersion = "2.0.0",
                recommendedVersion = "2.1.0",
                policyRevision = "pilot-2",
                apiVersion = "v1",
            )
        )

        val state = assertIs<AppUiState.UpgradeRequired>(coordinator.restore())

        assertEquals("2.0.0", state.minimumVersion)
        assertEquals("pilot-2", state.policyRevision)
    }

    @Test
    fun supportedAndOptionalUpdateClientsContinueToAuthenticationRestore() = runBlocking {
        for (status in listOf(ClientCompatibilityStatus.SUPPORTED, ClientCompatibilityStatus.UPDATE_AVAILABLE)) {
            val state = coordinator(
                compatibility = ClientCompatibility(
                    status = status,
                    minimumVersion = "1.0.0",
                    recommendedVersion = "1.1.0",
                    policyRevision = "pilot-1",
                    apiVersion = "v1",
                )
            ).restore()

            assertIs<AppUiState.SignedOut>(state)
        }
    }

    @Test
    fun compatibilityTransportFailureUsesTheRetryableOfflineState() = runBlocking<Unit> {
        val coordinator = MobileAppCoordinator(
            appRole = AppRole.PASSENGER,
            authentication = emptyAuthentication(),
            clientCompatibility = object : ClientCompatibilityGateway {
                override suspend fun check(): ClientCompatibility {
                    throw AuthenticationNetworkException()
                }
            },
        )

        assertIs<AppUiState.Offline>(coordinator.restore())
    }

    private fun coordinator(compatibility: ClientCompatibility) = MobileAppCoordinator(
        appRole = AppRole.PASSENGER,
        authentication = emptyAuthentication(),
        clientCompatibility = object : ClientCompatibilityGateway {
            override suspend fun check() = compatibility
        },
    )

    private fun emptyAuthentication() = AuthenticationSessionCoordinator(
        gateway = UnexpectedAuthenticationGateway,
        tokenStore = EmptyTokenStore,
    )
}

private object EmptyTokenStore : SecureTokenStore {
    override suspend fun tokens(): StoredTokens? = null
    override suspend fun save(accessToken: String, refreshToken: String) = error("unexpected save")
    override suspend fun clear() = Unit
}

private object UnexpectedAuthenticationGateway : AuthenticationGateway {
    override suspend fun register(
        displayName: String,
        email: String?,
        phoneNumber: String?,
        password: String,
    ) = error("unexpected register")

    override suspend fun login(
        identifier: String,
        password: String,
        deviceLabel: String?,
    ): SessionTokens = error("unexpected login")

    override suspend fun refresh(refreshToken: String): SessionTokens = error("unexpected refresh")
    override suspend fun logout(accessToken: String) = error("unexpected logout")
    override suspend fun currentAccount(accessToken: String): CurrentAccount = error("unexpected account")
}
