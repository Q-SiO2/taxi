package org.example.taximobile.domain.cooperatives

data class CooperativeMembership(
    val cooperativeId: String,
    val cooperativeName: String,
    val status: String,
    val joinedAt: String?,
    val membershipNumber: String?,
)

interface CooperativeGateway {
    /** Returns null only when the backend confirms that no current membership exists. */
    suspend fun currentMembership(): CooperativeMembership?
}
