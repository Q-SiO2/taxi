package org.example.taximobile.operations.model

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class PricingEconomicsModelsTest {
    @Test
    fun `fixed route tariff preserves its immutable direction scope`() {
        val tariff = Json { ignoreUnknownKeys = true }.decodeFromString<PricingRuleRecord>(
            """{
              "id":"fare-1","city_id":"city-1","operator_id":"operator-1",
              "service_type":"FIXED_ROUTE","booking_type":"IMMEDIATE",
              "fixed_route_direction_id":"direction-1","name":"Complete direction fare",
              "version":"route-v1","model":"FIXED","fixed_amount":"8.00","currency":"MAD",
              "effective_from":"2026-08-27T12:00:00Z","effective_until":null,"status":"ACTIVE",
              "optimistic_version":3,"created_at":"2026-08-27T10:00:00Z",
              "updated_at":"2026-08-27T11:00:00Z"
            }"""
        )

        assertEquals("direction-1", tariff.fixedRouteDirectionId)
        assertEquals("8.00", tariff.fixedAmount)
    }

    @Test
    fun `policy responses preserve exact decimal strings and optimistic revision`() {
        val policy = Json { ignoreUnknownKeys = true }.decodeFromString<OperatorFeePolicyRecord>(
            """{
              "id":"fee-1",
              "city_id":"city-1",
              "operator_id":"operator-1",
              "service_type":"ON_DEMAND",
              "version":"fee-v1",
              "status":"IN_REVIEW",
              "calculation_mode":"PERCENTAGE_OF_TRANSPORT_FARE",
              "funding_mode":"DRIVER_SETTLEMENT_DEDUCTION",
              "eligible_base_code":"TRANSPORT_FARE",
              "percentage_rate":"5.1250",
              "flat_amount":null,
              "currency":"MAD",
              "rounding_rule":"HALF_UP_0_01",
              "minimum_driver_net":"20.00",
              "effective_from":"2026-08-27T12:00:00Z",
              "effective_until":null,
              "optimistic_version":3,
              "created_at":"2026-08-27T10:00:00Z",
              "updated_at":"2026-08-27T11:00:00Z"
            }"""
        )

        assertEquals("5.1250", policy.percentageRate)
        assertEquals("20.00", policy.minimumDriverNet)
        assertEquals(3, policy.optimisticVersion)
        assertNull(policy.flatAmount)
    }

    @Test
    fun `fee request selects exactly one calculation amount`() {
        val percentage = org.example.taximobile.operations.ui.FeePolicyDraft(
            version = "fee-percentage-v1",
            percentageRate = "5.1250",
            currency = "MAD",
            effectiveFrom = "2026-08-27T12:00:00Z",
        ).toCreateOrNull("operator-1")
        val flat = org.example.taximobile.operations.ui.FeePolicyDraft(
            version = "fee-zero-v1",
            calculationMode = "FLAT_PER_COMPLETED_BOOKING",
            flatAmount = "0.00",
            currency = "MAD",
            effectiveFrom = "2026-08-27T12:00:00+01:00",
        ).toCreateOrNull("operator-1")

        assertEquals("5.1250", percentage?.percentageRate)
        assertNull(percentage?.flatAmount)
        assertEquals("0.00", flat?.flatAmount)
        assertNull(flat?.percentageRate)
        val routeTariff = org.example.taximobile.operations.ui.TariffDraft(
            serviceType = "FIXED_ROUTE",
            fixedRouteDirectionId = "direction-1",
            version = "route-v1",
            name = "Complete direction fare",
            fixedAmount = "8.00",
            currency = "MAD",
            effectiveFrom = "2026-08-27T12:00:00Z",
        ).toCreateOrNull("operator-1")
        assertEquals("FIXED_ROUTE", routeTariff?.serviceType)
        assertEquals("direction-1", routeTariff?.fixedRouteDirectionId)
    }

    @Test
    fun `form validators reject ambiguous money timestamps and policy transitions`() {
        assertTrue(validMoney("0.00", allowZero = true))
        assertFalse(validMoney("0.00", allowZero = false))
        assertFalse(validMoney("5.999", allowZero = true))
        assertTrue(validPercentage("99.9999"))
        assertFalse(validPercentage("100.0000"))
        assertTrue(validZonedTimestamp("2026-08-27T12:30:00Z"))
        assertFalse(validZonedTimestamp("2026-08-27T12:30:00"))
        assertEquals("IN_REVIEW", pricingPolicyTargetFor("DRAFT"))
        assertEquals("ACTIVE", pricingPolicyTargetFor("IN_REVIEW"))
        assertNull(pricingPolicyTargetFor("ACTIVE"))
    }

    @Test
    fun `scheduling draft sends complete ordered lifecycle policy`() {
        val request = org.example.taximobile.operations.ui.SchedulingPolicyDraft(
            serviceType = "FIXED_ROUTE",
            version = "fixed-schedule-v1",
            surchargeAmount = "3.00",
            currency = "MAD",
            beneficiary = "OPERATOR",
            minimumLeadMinutes = "60",
            maximumHorizonDays = "30",
            offerOpenMinutesBefore = "1440",
            offerResponseSeconds = "120",
            commitmentDeadlineMinutesBefore = "180",
            handoffMinutesBefore = "30",
            protectedDurationMinutes = "90",
            conflictBufferBeforeMinutes = "30",
            conflictBufferAfterMinutes = "30",
            passengerCancelCutoffMinutes = "60",
            driverCancelCutoffMinutes = "120",
            surchargeRefundMode = "FULL_BEFORE_CUTOFF",
            fallbackMatchingEnabled = true,
            effectiveFrom = "2026-08-29T12:00:00Z",
        ).toCreateOrNull("operator-1")

        assertEquals("FIXED_ROUTE", request?.serviceType)
        assertEquals(1440, request?.offerOpenMinutesBefore)
        assertEquals(180, request?.commitmentDeadlineMinutesBefore)
        assertEquals(30, request?.handoffMinutesBefore)
        assertEquals("FULL_BEFORE_CUTOFF", request?.surchargeRefundMode)
        assertTrue(request?.fallbackMatchingEnabled == true)
    }
}
