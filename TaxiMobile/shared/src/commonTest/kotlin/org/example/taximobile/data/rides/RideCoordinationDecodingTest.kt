package org.example.taximobile.data.rides

import kotlinx.serialization.json.Json
import org.example.taximobile.domain.rides.RideCoordinationCode
import org.example.taximobile.domain.rides.RideCoordinationSenderRole
import kotlin.test.Test
import kotlin.test.assertEquals

class RideCoordinationDecodingTest {
    @Test
    fun `known coordination response retains server role code and timestamp`() {
        val response = Json.decodeFromString<RideCoordinationResponse>(
            """{
              "id": "message-1",
              "ride_id": "ride-1",
              "sender_role": "DRIVER",
              "code": "DRIVER_ON_MY_WAY",
              "created_at": "2026-09-03T10:15:00Z"
            }"""
        ).toDomain()

        assertEquals("ride-1", response.rideId)
        assertEquals(RideCoordinationSenderRole.DRIVER, response.senderRole)
        assertEquals(RideCoordinationCode.DRIVER_ON_MY_WAY, response.code)
        assertEquals("2026-09-03T10:15:00Z", response.createdAt)
    }

    @Test
    fun `future coordination values remain visible as unknown instead of crashing`() {
        val response = Json.decodeFromString<RideCoordinationResponse>(
            """{
              "id": "message-2",
              "ride_id": "ride-1",
              "sender_role": "DISPATCHER",
              "code": "FUTURE_CODE",
              "created_at": "2026-09-03T10:16:00Z"
            }"""
        ).toDomain()

        assertEquals(RideCoordinationSenderRole.UNKNOWN, response.senderRole)
        assertEquals(RideCoordinationCode.UNKNOWN, response.code)
    }
}
