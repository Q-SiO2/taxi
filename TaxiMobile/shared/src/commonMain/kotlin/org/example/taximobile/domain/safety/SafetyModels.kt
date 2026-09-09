package org.example.taximobile.domain.safety

enum class SafetyCategory {
    IMMEDIATE_DANGER,
    HARASSMENT,
    ASSAULT,
    UNSAFE_DRIVING,
    DISCRIMINATION,
    VEHICLE_SAFETY,
    OTHER_SAFETY,
    UNKNOWN,
}

data class SafetyReport(
    val id: String,
    val rideId: String,
    val category: SafetyCategory,
    val status: String,
    val createdAt: String,
    val latestPublicMessage: String? = null,
    val updatedAt: String? = null,
)

interface SafetyGateway {
    suspend fun createReport(rideId: String, category: SafetyCategory, description: String)
    suspend fun reports(): List<SafetyReport>
}
