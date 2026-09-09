package org.example.taximobile.data.drivers

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import org.example.taximobile.domain.rides.RideServiceType

class DriverOfferEconomicsDecodingTest {
    @Test
    fun `offer preserves backend fee funding and expected driver net`() {
        val payload = Json { ignoreUnknownKeys = true }.decodeFromString<OfferListResponse>(
            """{
              "server_time": "2026-08-27T10:00:00Z",
              "offers": [{
                "id": "offer-1",
                "ride_id": "ride-1",
                "service_type": "FIXED_ROUTE",
                "fixed_route": {
                  "direction_version_id": "direction-1",
                  "route_version_id": "route-version-1",
                  "route_code": "RABAT_01",
                  "localized_route_name": {"en":"Route","fr":"Ligne","ar":"الخط"},
                  "direction_code": "OUTBOUND",
                  "start_location_name": {"en":"Station","fr":"Gare","ar":"المحطة"},
                  "finish_location_name": {"en":"University","fr":"Université","ar":"الجامعة"}
                },
                "pickup": {"latitude": 33.5731, "longitude": -7.5898},
                "estimated_fare": {"amount": "35.13", "currency": "MAD"},
                "economics": {
                  "transport_fare": "35.13",
                  "scheduling_surcharge": "0.00",
                  "operator_service_fee": "1.76",
                  "passenger_total": "35.13",
                  "expected_driver_net": "33.37",
                  "operator_allocation": "1.76",
                  "operator_fee_policy_version": "fee-v1",
                  "operator_fee_calculation_mode": "PERCENTAGE_OF_TRANSPORT_FARE",
                  "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION"
                },
                "issued_at": "2026-08-27T10:00:00Z",
                "expires_at": "2026-08-27T10:00:45Z"
              }]
            }"""
        )

        val offer = payload.offers.single().toDomain(payload.serverTime)

        assertEquals("35.13", offer.estimatedFareAmount)
        assertEquals("33.37", offer.economics?.expectedDriverNet)
        assertEquals("DRIVER_SETTLEMENT_DEDUCTION", offer.economics?.operatorFeeFundingMode)
        assertEquals("2026-08-27T10:00:00Z", offer.serverTimeAtFetch)
        assertEquals(RideServiceType.FIXED_ROUTE, offer.serviceType)
        assertEquals("Station", offer.fixedRoute?.startName?.en)
    }
}
