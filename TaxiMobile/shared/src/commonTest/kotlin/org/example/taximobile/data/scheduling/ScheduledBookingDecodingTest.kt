package org.example.taximobile.data.scheduling

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ScheduledBookingDecodingTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `passenger booking preserves backend economics policy and honest commitment state`() {
        val response = json.decodeFromString<ScheduledBookingListResponse>(
            """{"items":[${bookingPayload(status = "OFFERING", committed = false)}],"page":1,"limit":20,"total":1}""",
        )

        val booking = response.items.single().toDomain()

        assertEquals("11.00", booking.economics.passengerTotal)
        assertEquals("3.00", booking.economics.schedulingSurcharge)
        assertEquals("schedule-fixed-v1", booking.economics.schedulingPolicyVersion)
        assertEquals("FULL_BEFORE_CUTOFF", booking.cancellationTerms.surchargeRefundMode)
        assertFalse(booking.driverCommitted)
        assertEquals("Africa/Casablanca", booking.cityTimezone)
    }

    @Test
    fun `driver offer and commitment retain server timing and protected window`() {
        val offer = json.decodeFromString<ScheduledOfferListResponse>(
            """{"items":[{
              "id":"offer-1","booking_id":"booking-1","status":"PENDING","city_id":"city-1",
              "service_type":"FIXED_ROUTE","scheduled_for":"2026-09-03T08:30:00Z",
              "city_timezone":"Africa/Casablanca","expires_at":"2026-08-29T12:02:00Z",
              "pickup":{"latitude":34.02,"longitude":-6.84,"address":"Station"},
              "destination":{"latitude":34.00,"longitude":-6.80,"address":"University"},
              ${economicsAndTerms()},"server_time":"2026-08-29T12:00:00Z"
            }]}""",
        ).items.single().toDomain()
        val commitment = json.decodeFromString<ScheduledCommitmentListResponse>(
            """{"items":[{
              "id":"commitment-1","booking_id":"booking-1","city_id":"city-1",
              "service_type":"FIXED_ROUTE","scheduled_for":"2026-09-03T08:30:00Z",
              "city_timezone":"Africa/Casablanca","status":"ACTIVE",
              "protected_from":"2026-09-03T07:30:00Z","protected_until":"2026-09-03T10:30:00Z",
              "pickup":{"latitude":34.02,"longitude":-6.84,"address":"Station"},
              "destination":{"latitude":34.00,"longitude":-6.80,"address":"University"},
              "economics":${economics()}
            }]}""",
        ).items.single().toDomain()

        assertEquals("2026-08-29T12:00:00Z", offer.serverTime)
        assertEquals("2026-08-29T12:02:00Z", offer.expiresAt)
        assertEquals("8.00", offer.economics.expectedDriverNet)
        assertEquals("2026-09-03T07:30:00Z", commitment.protectedFrom)
        assertEquals("2026-09-03T10:30:00Z", commitment.protectedUntil)
        assertTrue(commitment.status == "ACTIVE")
    }

    @Test
    fun `scheduled estimate and driver preferences preserve backend authority`() {
        val estimate = json.decodeFromString<ScheduledBookingEstimateResponse>(
            """{
              "city_id":"city-1","operator_id":"operator-1","service_type":"FIXED_ROUTE",
              "fixed_route_direction_version_id":"direction-1","scheduled_for":"2026-09-03T08:30:00Z",
              "city_timezone":"Africa/Casablanca","pickup":{"latitude":34.02,"longitude":-6.84},
              "destination":{"latitude":34.00,"longitude":-6.80},${economicsAndTerms()},
              "payment_method":"CASH"
            }""",
        ).toDomain()
        val preferences = json.decodeFromString<ScheduledPreferenceListResponse>(
            """{"items":[{"city_id":"city-1","enabled":true,"updated_at":"2026-08-29T12:00:00Z"}]}""",
        ).items.map(ScheduledPreferenceResponse::toDomain)

        assertEquals("11.00", estimate.economics.passengerTotal)
        assertEquals("schedule-fixed-v1", estimate.economics.schedulingPolicyVersion)
        assertEquals("CASH", estimate.paymentMethod)
        assertTrue(preferences.single().enabled)
    }

    private fun bookingPayload(status: String, committed: Boolean) = """{
      "id":"booking-1","city_id":"city-1","operator_id":"operator-1","service_type":"FIXED_ROUTE",
      "fixed_route_direction_version_id":"direction-1","scheduled_for":"2026-09-03T08:30:00Z",
      "city_timezone":"Africa/Casablanca","status":"$status",
      "pickup":{"latitude":34.02,"longitude":-6.84,"address":"Station"},
      "destination":{"latitude":34.00,"longitude":-6.80,"address":"University"},
      ${economicsAndTerms()},"driver_committed":$committed,"live_ride_id":null,
      "cancellation_financial_outcome":null,"created_at":"2026-08-29T12:00:00Z"
    }"""

    private fun economicsAndTerms() = """
      "economics":${economics()},
      "cancellation_terms":{"passenger_cancel_cutoff_minutes":60,
        "surcharge_refund_mode":"FULL_BEFORE_CUTOFF",
        "summary":"The scheduling surcharge is refundable until 60 minutes before pickup."}
    """.trimIndent()

    private fun economics() = """{
      "transport_fare":"8.00","scheduling_surcharge":"3.00","operator_service_fee":"0.00",
      "passenger_total":"11.00","expected_driver_net":"8.00","operator_allocation":"3.00",
      "currency":"MAD","pricing_rule_version":"route-v1","operator_fee_policy_version":"fee-v1",
      "scheduling_policy_version":"schedule-fixed-v1"
    }"""
}
