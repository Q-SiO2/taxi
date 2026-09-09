package org.example.taximobile.domain.system

enum class ClientCompatibilityStatus {
    SUPPORTED,
    UPDATE_AVAILABLE,
    UPGRADE_REQUIRED,
}

data class ClientCompatibility(
    val status: ClientCompatibilityStatus,
    val minimumVersion: String,
    val recommendedVersion: String,
    val policyRevision: String,
    val apiVersion: String,
)

interface ClientCompatibilityGateway {
    suspend fun check(): ClientCompatibility
}
