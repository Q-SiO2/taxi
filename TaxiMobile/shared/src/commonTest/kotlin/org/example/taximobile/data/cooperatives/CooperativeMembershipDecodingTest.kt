package org.example.taximobile.data.cooperatives

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals

class CooperativeMembershipDecodingTest {
    @Test
    fun `membership response retains only documented self fields`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<CooperativeMembershipResponse>(
            """{
              "cooperative_id": "cooperative-1",
              "cooperative_name": "Casablanca Taxi Cooperative",
              "status": "ACTIVE",
              "joined_at": "2026-01-01T00:00:00Z",
              "membership_number": "MEMBER-123",
              "future_field": "ignored"
            }"""
        ).toDomain()

        assertEquals("Casablanca Taxi Cooperative", response.cooperativeName)
        assertEquals("ACTIVE", response.status)
        assertEquals("MEMBER-123", response.membershipNumber)
    }
}
