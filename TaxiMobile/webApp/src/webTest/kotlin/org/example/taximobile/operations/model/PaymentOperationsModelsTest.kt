package org.example.taximobile.operations.model

import kotlinx.serialization.json.Json
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class PaymentOperationsModelsTest {
    private val json = Json { ignoreUnknownKeys = true }

    @Test
    fun `configuration and reconciliation permissions independently expose payments`() {
        assertEquals(
            listOf(OperationsDestination.PAYMENTS),
            availableDestinations(setOf(MANAGE_PAYMENT_CAPABILITIES)),
        )
        assertEquals(
            listOf(OperationsDestination.PAYMENTS),
            availableDestinations(setOf(RECONCILE_PAYMENTS)),
        )
    }

    @Test
    fun `capability response preserves exact scope lifecycle and cash fallback`() {
        val capability = json.decodeFromString<PaymentCapabilityRecord>(
            """{
              "id":"capability-1","city_id":"city-1","operator_id":"operator-1",
              "service_type":"ON_DEMAND","version":"cash-v1","status":"ACTIVE",
              "cash_enabled":true,"manual_transfer_enabled":false,
              "recipient_account_id":null,"effective_from":"2026-08-31T10:00:00Z",
              "effective_until":null,"optimistic_version":4,
              "submitted_at":"2026-08-31T10:01:00Z",
              "approved_at":"2026-08-31T10:02:00Z",
              "activated_at":"2026-08-31T10:03:00Z",
              "created_at":"2026-08-31T10:00:00Z",
              "updated_at":"2026-08-31T10:03:00Z"
            }""",
        )

        assertEquals("city-1", capability.cityId)
        assertEquals("operator-1", capability.operatorId)
        assertEquals("ON_DEMAND", capability.serviceType)
        assertEquals("ACTIVE", capability.status)
        assertEquals(4, capability.optimisticVersion)
        assertEquals(true, capability.cashEnabled)
        assertNull(capability.recipientAccountId)
    }

    @Test
    fun `reconciliation records preserve exact decimal strings and provenance`() {
        val transfer = json.decodeFromString<ManualTransferReconciliationRecord>(
            """{
              "claim_id":"claim-1","payment_id":"payment-1","ride_id":"ride-1",
              "city_id":"city-1","operator_id":"operator-1",
              "recipient_account_id":"recipient-1","recipient_label":"primary-wallet",
              "payment_reference":"TM-REFERENCE-1","payer_reference":"WALLET-42",
              "amount":"40.00","currency":"MAD","status":"SUBMITTED",
              "submitted_at":"2026-08-31T11:00:00Z","reviewed_at":null
            }""",
        )
        val refund = json.decodeFromString<PaymentRefundRecord>(
            """{
              "id":"refund-1","payment_id":"payment-1","ride_id":"ride-1",
              "city_id":"city-1","operator_id":"operator-1","amount":"5.00",
              "currency":"MAD","reason":"SERVICE_RECOVERY",
              "settlement_method":"EXTERNAL_TRANSFER",
              "settlement_reference":"RETURN-1","operator_note":"Case approved.",
              "driver_recovery_amount":"0.00","operator_funded_amount":"5.00",
              "authorized_by_user_id":"reviewer-1","refunded_at":"2026-08-31T12:00:00Z",
              "payment_status":"COMPLETED","remaining_refundable_amount":"35.00"
            }""",
        )

        assertEquals("40.00", transfer.amount)
        assertEquals("recipient-1", transfer.recipientAccountId)
        assertEquals("city-1", refund.cityId)
        assertEquals("operator-1", refund.operatorId)
        assertEquals("0.00", refund.driverRecoveryAmount)
        assertEquals("35.00", refund.remainingRefundableAmount)
    }
}
