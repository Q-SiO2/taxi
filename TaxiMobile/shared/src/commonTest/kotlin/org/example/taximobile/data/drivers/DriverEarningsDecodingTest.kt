package org.example.taximobile.data.drivers

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals

class DriverEarningsDecodingTest {
    @Test
    fun `earnings response preserves summary pagination and exact row amounts`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<DriverEarningsResponse>(
            """{
              "currency": "MAD",
              "gross": 35.00,
              "fees": 0.00,
              "adjustments": 0.00,
              "net": 35.00,
              "settled_through": "2026-08-13T12:00:00Z",
              "count": 1,
              "page": 1,
              "limit": 20,
              "items": [{
                "id": "earning-1",
                "ride_id": "ride-1",
                "gross": 35.00,
                "fees": 0.00,
                "adjustments": 0.00,
                "net": 35.00,
                "currency": "MAD",
                "settled_at": "2026-08-13T12:00:00Z"
              }]
            }"""
        )

        assertEquals(1, response.count)
        assertEquals("2026-08-13T12:00:00Z", response.settledThrough)
        assertEquals("ride-1", response.items.single().toDomain().rideId)
        assertEquals("35.00", response.items.single().toDomain().net)
    }
}
