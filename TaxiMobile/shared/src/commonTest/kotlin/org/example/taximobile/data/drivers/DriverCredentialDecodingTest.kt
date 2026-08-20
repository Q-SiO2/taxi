package org.example.taximobile.data.drivers

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals

class DriverCredentialDecodingTest {
    @Test
    fun `credential response retains only documented privacy minimized fields`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<DriverCredentialListResponse>(
            """{
              "credentials": [{
                "id": "credential-1",
                "type": "DRIVER_LICENSE",
                "status": "VERIFIED",
                "issued_at": "2025-08-13T00:00:00Z",
                "expires_at": "2027-08-13T00:00:00Z",
                "future_field": "ignored"
              }]
            }"""
        ).credentials.single().toDomain()

        assertEquals("credential-1", response.id)
        assertEquals("DRIVER_LICENSE", response.type)
        assertEquals("VERIFIED", response.status)
        assertEquals("2027-08-13T00:00:00Z", response.expiresAt)
    }
}
