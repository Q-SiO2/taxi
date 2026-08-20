package org.example.taximobile.domain.auth

enum class AccountRole {
    PASSENGER,
    DRIVER,
    COOPERATIVE_MEMBER,
    ADMIN,
}

data class CurrentAccount(
    val id: String,
    val roles: Set<AccountRole>,
    val displayName: String,
)

data class SessionTokens(
    val accessToken: String,
    val refreshToken: String,
)
