package org.example.taximobile.domain.support

/** Controlled categories keep user input from defining operational ticket types. */
enum class SupportCategory {
    RIDE_PROBLEM,
    FARE_DISPUTE,
    ACCOUNT_ACCESS,
    OTHER,
}

data class SupportTicket(
    val id: String,
    val category: SupportCategory,
    val subject: String,
    val status: String,
    val createdAt: String,
    val latestPublicMessage: String? = null,
    val updatedAt: String? = null,
)

interface SupportGateway {
    suspend fun createTicket(category: SupportCategory, subject: String, description: String, rideId: String? = null)
    suspend fun tickets(): List<SupportTicket>
}
