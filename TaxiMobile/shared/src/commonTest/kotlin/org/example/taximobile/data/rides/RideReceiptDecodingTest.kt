package org.example.taximobile.data.rides

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals

class RideReceiptDecodingTest {
    @Test
    fun `receipt decoding preserves append-only refund totals and safe rows`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<RideReceiptResponse>(
            """{
              "ride_id": "ride-1",
              "completed_at": "2026-08-24T12:00:00Z",
              "fare": {
                "amount": "35.00",
                "currency": "MAD",
                "pricing_rule_version": "casablanca-v1",
                "components": [{"code":"TRANSPORT_FARE","label":"Transport fare","amount":"35.00"}],
                "economics": {
                  "transport_fare": "35.00",
                  "scheduling_surcharge": "0.00",
                  "operator_service_fee": "1.76",
                  "passenger_total": "35.00",
                  "expected_driver_net": "33.24",
                  "operator_allocation": "1.76",
                  "operator_fee_policy_version": "fee-v1",
                  "operator_fee_calculation_mode": "PERCENTAGE_OF_TRANSPORT_FARE",
                  "operator_fee_funding_mode": "DRIVER_SETTLEMENT_DEDUCTION"
                }
              },
              "payment": {
                "method": "CASH",
                "status": "COMPLETED",
                "refunds": {
                  "refunded_amount": "5.00",
                  "net_paid_amount": "30.00",
                  "currency": "MAD",
                  "items": [{
                    "id": "refund-1",
                    "amount": "5.00",
                    "currency": "MAD",
                    "reason": "FARE_CORRECTION",
                    "refunded_at": "2026-08-24T13:00:00Z"
                  }]
                }
              }
            }"""
        )

        val receipt = response.toDomain()
        assertEquals("35.00", receipt.fare.amount)
        assertEquals("33.24", receipt.fare.economics?.expectedDriverNet)
        assertEquals("DRIVER_SETTLEMENT_DEDUCTION", receipt.fare.economics?.operatorFeeFundingMode)
        assertEquals("TRANSPORT_FARE", receipt.fare.components.single().code)
        assertEquals("5.00", receipt.refunds?.refundedAmount)
        assertEquals("30.00", receipt.refunds?.netPaidAmount)
        assertEquals("FARE_CORRECTION", receipt.refunds?.items?.single()?.reason)
        assertEquals("2026-08-24T13:00:00Z", receipt.refunds?.items?.single()?.refundedAt)
    }

    @Test
    fun `older receipt without refund field remains decodable`() {
        val response = Json { ignoreUnknownKeys = true }.decodeFromString<RideReceiptResponse>(
            """{
              "ride_id": "ride-legacy",
              "completed_at": "2026-08-24T12:00:00Z",
              "fare": {"amount": "35.00", "currency": "MAD", "components": []},
              "payment": {"method": "CASH", "status": "COMPLETED"}
            }"""
        )

        assertEquals(null, response.toDomain().refunds)
    }
}
