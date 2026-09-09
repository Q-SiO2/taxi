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
              "transport_fare": 35.00,
              "scheduling_surcharge": 5.00,
              "operator_service_fee": 1.76,
              "operator_allocation": 1.76,
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
                "transport_fare": 35.00,
                "scheduling_surcharge": 5.00,
                "operator_service_fee": 1.76,
                "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION",
                "operator_allocation": 1.76,
                "currency": "MAD",
                "settled_at": "2026-08-13T12:00:00Z"
              }]
            }"""
        )

        assertEquals(1, response.count)
        assertEquals("2026-08-13T12:00:00Z", response.settledThrough)
        assertEquals("ride-1", response.items.single().toDomain().rideId)
        assertEquals("35.00", response.items.single().toDomain().net)
        assertEquals("35.00", response.transportFare?.content)
        assertEquals("5.00", response.schedulingSurcharge?.content)
        assertEquals("1.76", response.items.single().toDomain().operatorServiceFee)
        assertEquals("DRIVER_SETTLEMENT_DEDUCTION", response.items.single().toDomain().operatorFeeFundingMode)
    }
}
