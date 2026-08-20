package org.example.taximobile.data.rides

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals

class RideHistoryDecodingTest {
    @Test
    fun `history decoding retains pickup destination and optional address`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<RideListResponse>(
            """{
              "items": [{
                "id": "ride-1",
                "status": "COMPLETED",
                "completed_at": "2026-08-13T12:00:00Z",
                "pickup": {"latitude": 33.5731, "longitude": -7.5898, "address": "Pickup"},
                "destination": {"latitude": 33.5890, "longitude": -7.5910, "address": " Casa Voyageurs "},
                "driver": null
              }]
            }"""
        )

        val ride = response.items.single().toSummary()
        assertEquals("Pickup", ride.pickup?.address)
        assertEquals("Casa Voyageurs", ride.destination?.address)
        assertEquals(33.5890, ride.destination?.latitude)
    }
}
